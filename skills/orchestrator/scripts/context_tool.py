"""Generate handoffs and collect local evidence; never spawn agents or grant authority."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
import uuid
from pathlib import Path

from validate_context_contract import (
    CAPSULE_FIELDS, DELTA_FIELDS, SCHEMA_VERSION, capsule_digest, read_payload,
    validate_acceptance, validate_capsule, validate_checks, validate_delta,
)
from workspace_state import check_input_freshness, changed_paths, digest, relative_path, snapshot, under


class ContractError(ValueError):
    pass


def require(errors: list[str]) -> None:
    if errors:
        raise ContractError("; ".join(errors))


def outside_workspace(path: Path, root: Path, exclusions: list[str] | None = None) -> Path:
    """Permit sidecars, or the explicitly excluded reserved in-workspace directory."""
    resolved = path.resolve()
    if resolved.is_relative_to(root.resolve()):
        relative = resolved.relative_to(root.resolve()).as_posix()
        if ".orchestrator" not in (exclusions or []) or not relative.startswith(".orchestrator/"):
            raise ValueError("Store artifacts outside the workspace or under explicitly excluded .orchestrator/.")
    return resolved


def write_new(path: Path, payload: dict, root: Path, exclusions: list[str] | None = None) -> None:
    path = outside_workspace(path, root, exclusions)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Never silently replace a capsule, receipt, or root acceptance decision.
    with path.open("x", encoding="utf-8") as stream:
        json.dump(payload, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")


def make_capsule(spec: dict, root: Path, exclusions: list[str] | None = None) -> dict:
    if not isinstance(spec, dict):
        raise ValueError("spec must be an object")
    capsule = {field: [] for field in ("confirmed_decisions", "non_goals", "dependencies_and_interfaces",
               "owned_paths", "input_paths", "known_failures", "evidence_index", "open_questions")}
    # The model supplies judgment fields; machine fields cannot be supplied by the spec.
    for field in CAPSULE_FIELDS:
        if field in spec and field not in ("schema_version", "workspace_base"):
            capsule[field] = spec[field]
    capsule.update(schema_version=SCHEMA_VERSION, node_id=spec.get("node_id", uuid.uuid4().hex),
                   capsule_version=spec.get("capsule_version", 1), workspace_base=snapshot(root, exclusions))
    require(validate_capsule(capsule))
    require([f"acceptance criterion {item['id']} must pin a non-empty command argv"
             for item in capsule["acceptance_criteria"]
             if item["verification"] == "command" and not item.get("command")])
    return capsule


def record_path(records: Path, name: str) -> Path:
    if not relative_path(name):
        raise ValueError("Invalid evidence record path")
    path = (records / name).resolve()
    if not path.is_relative_to(records.resolve()):
        raise ValueError("Evidence record escapes records directory")
    return path


def runtime_signature() -> dict:
    return {"python": platform.python_version(), "platform": sys.platform}


def run_check(capsule: dict, root: Path, records: Path, command: list[str], cwd: str = ".") -> dict:
    require(validate_capsule(capsule))
    if capsule["permission"] == "read-only":
        raise ValueError("read-only capsules do not authorize execution checks")
    if not command or (cwd != "." and not relative_path(cwd)):
        raise ValueError("Provide a non-empty argv and relative cwd")
    folder = (root / cwd).resolve()
    if not folder.is_relative_to(root.resolve()):
        raise ValueError("Check cwd escapes workspace")
    records = outside_workspace(records, root, capsule["workspace_base"]["excluded_paths"])
    before = snapshot(root, capsule["workspace_base"]["excluded_paths"])
    changes = changed_paths(capsule["workspace_base"]["files"], before["files"])
    if (capsule["permission"] != "scoped-write" and changes) or any(not under(path, capsule["owned_paths"]) for path in changes):
        raise ValueError("Inputs or files outside ownership changed before the check")
    identifier = "check-" + uuid.uuid4().hex
    records.mkdir(parents=True, exist_ok=True)
    stdout_file, stderr_file = records / (identifier + ".stdout"), records / (identifier + ".stderr")
    with stdout_file.open("xb") as stdout, stderr_file.open("xb") as stderr:
        env = os.environ.copy()
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        completed = subprocess.run(command, cwd=folder, env=env, stdout=stdout, stderr=stderr, check=False)
    after = snapshot(root, capsule["workspace_base"]["excluded_paths"])
    check = {"id": identifier, "command": command, "cwd": cwd,
             "exit_code": completed.returncode, "status": "passed" if completed.returncode == 0 else "failed",
             "summary": f"Process exited with code {completed.returncode}.",
             "workspace_digest": digest(before["files"]),
             "stdout_digest": "sha256:" + hashlib.sha256(stdout_file.read_bytes()).hexdigest(),
             "stderr_digest": "sha256:" + hashlib.sha256(stderr_file.read_bytes()).hexdigest(),
             "record": identifier + ".json"}
    receipt = {"schema_version": SCHEMA_VERSION, "capsule_digest": capsule_digest(capsule), "check": check,
               "workspace_after_digest": digest(after["files"]), "runtime": runtime_signature()}
    write_new(records / check["record"], receipt, root, capsule["workspace_base"]["excluded_paths"])
    return check


def verify_receipts(delta: dict, capsule: dict, records: Path, current_ids: list[str] | None = None) -> list[str]:
    errors = []
    for check in delta["checks"]:
        if check["status"] == "not_run":
            continue
        receipt = read_payload(str(record_path(records, check["record"])))
        if not isinstance(receipt, dict) or receipt.get("check") != check or receipt.get("capsule_digest") != capsule_digest(capsule):
            errors.append("check receipt does not match the reported check and capsule")
            continue
        if check["id"] in (current_ids or []) and receipt.get("runtime") != runtime_signature():
            errors.append("check runtime changed; review environment before reusing evidence")
        current_digest = digest(delta["workspace_after"]["files"])
        if check["id"] in (current_ids or []) and (check["workspace_digest"] != current_digest or receipt.get("workspace_after_digest") != current_digest):
            errors.append("check evidence does not match final code state")
        for suffix in ("stdout", "stderr"):
            content = record_path(records, check["id"] + "." + suffix).read_bytes()
            if "sha256:" + hashlib.sha256(content).hexdigest() != check[suffix + "_digest"]:
                errors.append("check output digest mismatch")
    return errors


def make_delta(report: dict, capsule: dict, root: Path, records: Path) -> dict:
    if not isinstance(report, dict):
        raise ValueError("report must be an object")
    result = {field: [] for field in ("context_issues", "evidence", "changed_files", "checks", "new_facts",
              "invalidated_assumptions", "open_questions", "risks")}
    for field in ("execution_status", "context_status", "context_issues", "conclusion", "evidence",
                  "changed_files", "new_facts", "invalidated_assumptions", "open_questions", "risks", "recommended_next"):
        if field in report:
            result[field] = report[field]
    result.setdefault("recommended_next", None)
    result.setdefault("context_status", "sufficient")
    names = report.get("check_records", [])
    if not isinstance(names, list):
        raise ValueError("check_records must be a list")
    result["checks"] = [read_payload(str(record_path(records, name)))["check"] for name in names]
    result.update(schema_version=SCHEMA_VERSION, stage_id=capsule["stage_id"], node_id=capsule["node_id"],
                  received_capsule_version=capsule["capsule_version"], capsule_digest=capsule_digest(capsule),
                  workspace_after=snapshot(root, capsule["workspace_base"]["excluded_paths"]))
    require(validate_delta(result, capsule=capsule, workspace_root=root))
    require(verify_receipts(result, capsule, records))
    return result


def accept(review: dict, capsule: dict, delta: dict, root: Path, records: Path) -> dict:
    require(validate_delta(delta, capsule=capsule, workspace_root=root))
    require(validate_acceptance(review, capsule, delta))
    evidence = {item["id"]: item for item in delta["evidence"]}
    used = [evidence[key]["ref"] for row in review["criteria"] if row["decision"] == "met"
            for key in row["evidence_ids"] if evidence[key]["kind"] == "command"]
    require(verify_receipts(delta, capsule, records, used))
    return {"schema_version": SCHEMA_VERSION, "stage_id": capsule["stage_id"], "node_id": capsule["node_id"],
            "capsule_digest": capsule_digest(capsule), "delta_digest": digest(delta),
            "reviewed_workspace_digest": digest(delta["workspace_after"]["files"]),
            "acceptance_status": review["acceptance_status"], "criteria": review["criteria"]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    schema = sub.add_parser("schema", help="Print authoritative required fields without reading a workspace")
    for action in ("prepare", "ready", "run-check", "result", "accept"):
        command = sub.add_parser(action)
        command.add_argument("--workspace-root", type=Path, required=True)
        if action == "prepare":
            command.add_argument("--spec", required=True)
            command.add_argument("--exclude", action="append", default=[])
        else:
            command.add_argument("--capsule", required=True)
        if action in ("prepare", "result", "accept"):
            command.add_argument("--out", type=Path, required=True)
        if action in ("run-check", "result", "accept"):
            command.add_argument("--records-dir", type=Path, required=True)
        if action == "run-check":
            command.add_argument("--cwd", default=".")
            command.add_argument("command", nargs=argparse.REMAINDER)
        if action == "result":
            command.add_argument("--report", required=True)
        if action == "accept":
            command.add_argument("--delta", required=True)
            command.add_argument("--review", required=True)
    args = parser.parse_args()
    try:
        if args.action == "schema":
            print(json.dumps({"schema_version": SCHEMA_VERSION, "capsule": CAPSULE_FIELDS, "delta": DELTA_FIELDS}, indent=2))
            return 0
        root = args.workspace_root.resolve(strict=True)
        if args.action == "prepare":
            exclusions = args.exclude
            outside_workspace(args.out, root, exclusions)
            value = make_capsule(read_payload(args.spec), root, args.exclude)
        else:
            cap = read_payload(args.capsule)
            require(validate_capsule(cap))
            exclusions = cap["workspace_base"]["excluded_paths"]
            if hasattr(args, "out"):
                outside_workspace(args.out, root, exclusions)
            if hasattr(args, "records_dir"):
                outside_workspace(args.records_dir, root, exclusions)
            if args.action == "ready":
                issues = check_input_freshness(cap, snapshot(root, cap["workspace_base"]["excluded_paths"]))
                print(json.dumps({"received_capsule_version": cap["capsule_version"],
                                  "context_status": "stale_context" if issues else "sufficient", "context_issues": issues}))
                return 2 if issues else 0
            if args.action == "run-check":
                argv = args.command[1:] if args.command[:1] == ["--"] else args.command
                value = run_check(cap, root, args.records_dir, argv, args.cwd)
                print(json.dumps(value, indent=2))
                return 0  # Receipt creation succeeded; actual test exit code is in the receipt.
            if args.action == "result":
                value = make_delta(read_payload(args.report), cap, root, args.records_dir)
            else:
                value = accept(read_payload(args.review), cap, read_payload(args.delta), root, args.records_dir)
        write_new(args.out, value, root, exclusions)
        print(f"Created {args.action} record: {args.out}")
        return 0
    except ContractError as error:
        print(f"INVALID operation: {error}", file=sys.stderr)
        return 2
    except (OSError, ValueError, KeyError, TypeError, RecursionError):
        # Payloads may contain private data. Errors from validated fields are raised
        # separately below by callers/tests; do not dump arbitrary JSON or commands.
        print("INVALID operation: check inputs, contract validation, workspace freshness and record paths.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
