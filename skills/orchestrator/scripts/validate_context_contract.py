"""Schema 2 is the single source of truth for Full handoff fields."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from workspace_state import changed_paths, digest, relative_path, snapshot, snapshot_errors, under

SCHEMA_VERSION = 2
CAPSULE_FIELDS = (
    "schema_version", "stage_id", "node_id", "capsule_version", "objective", "acceptance_criteria",
    "confirmed_decisions", "non_goals", "dependencies_and_interfaces", "owned_paths", "input_paths",
    "permission", "safety_boundaries", "known_failures", "evidence_index", "open_questions", "workspace_base",
)
DELTA_FIELDS = (
    "schema_version", "stage_id", "node_id", "execution_status", "received_capsule_version",
    "context_status", "context_issues", "capsule_digest", "conclusion", "evidence", "changed_files",
    "checks", "new_facts", "invalidated_assumptions", "open_questions", "risks", "recommended_next", "workspace_after",
)
CONTEXT_STATUSES = ("sufficient", "missing_context", "stale_context", "contradictory_context")
DELTA_STATUSES = ("completed", "blocked", "needs_decision")
PERMISSIONS = ("read-only", "scoped-write", "execute-checks")
CHECK_STATUSES = ("passed", "failed", "not_run")
EVIDENCE_KINDS = ("path", "url", "command")


def capsule_digest(payload: dict) -> str:
    return digest(payload)


def nonblank(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def string_list(value: Any) -> bool:
    return isinstance(value, list) and all(nonblank(item) for item in value)


def shape(payload: Any, fields: tuple[str, ...], label: str) -> list[str]:
    if not isinstance(payload, dict):
        return [f"{label} must be a JSON object"]
    errors = [f"missing required field: {field}" for field in fields if field not in payload]
    if type(payload.get("schema_version")) is not int or payload["schema_version"] != SCHEMA_VERSION:
        errors.append("schema_version must be integer 2; regenerate schema 1 handoffs")
    for field in ("stage_id", "node_id"):
        if not nonblank(payload.get(field)):
            errors.append(f"{field} must be a non-empty string")
    return errors


def validate_evidence(value: Any, label: str) -> list[str]:
    if not isinstance(value, list):
        return [f"{label} must be a list"]
    errors, ids = [], []
    for index, item in enumerate(value):
        name = f"{label}[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{name} must be an object")
            continue
        for field in ("id", "ref", "result"):
            if not nonblank(item.get(field)):
                errors.append(f"{name}.{field} must be a non-empty string")
        ids.append(item.get("id"))
        if item.get("kind") not in EVIDENCE_KINDS or type(item.get("verified")) is not bool:
            errors.append(f"{name} has invalid kind or verified value")
    if all(isinstance(item, str) for item in ids) and len(set(ids)) != len(ids):
        errors.append(f"{label} IDs must be unique")
    return errors


def validate_capsule(payload: Any, expected_version: int | None = None) -> list[str]:
    errors = shape(payload, CAPSULE_FIELDS, "capsule")
    if not isinstance(payload, dict):
        return errors
    if not nonblank(payload.get("objective")):
        errors.append("objective must be a non-empty string")
    version = payload.get("capsule_version")
    if type(version) is not int or version < 1:
        errors.append("capsule_version must be a positive integer")
    elif expected_version is not None and version != expected_version:
        errors.append("capsule_version mismatch")
    for field in ("non_goals", "dependencies_and_interfaces", "owned_paths", "input_paths", "safety_boundaries", "known_failures", "open_questions"):
        if not string_list(payload.get(field)):
            errors.append(f"{field} must be a list of non-blank strings")
    for field in ("owned_paths", "input_paths"):
        paths = payload.get(field)
        if isinstance(paths, list) and any(not relative_path(item) for item in paths):
            errors.append(f"{field} must contain normalized portable relative paths")
    if payload.get("permission") not in PERMISSIONS:
        errors.append("permission must be read-only, scoped-write, or execute-checks")
    if not payload.get("safety_boundaries"):
        errors.append("safety_boundaries must not be empty")
    if payload.get("permission") == "scoped-write" and not payload.get("owned_paths"):
        errors.append("scoped-write requires non-empty owned_paths")
    criteria = payload.get("acceptance_criteria")
    if not isinstance(criteria, list) or not criteria:
        errors.append("acceptance_criteria must contain at least one observable criterion")
    else:
        ids = []
        for index, item in enumerate(criteria):
            if not isinstance(item, dict) or not nonblank(item.get("id")) or not nonblank(item.get("description")):
                errors.append(f"acceptance_criteria[{index}] requires id and description")
                continue
            ids.append(item["id"])
            if item.get("verification") not in ("command", "manual"):
                errors.append(f"acceptance_criteria[{index}].verification must be command or manual")
            if item.get("verification") == "command" and type(item.get("expected_exit_code")) is not int:
                errors.append(f"acceptance_criteria[{index}] requires integer expected_exit_code")
            if "command" in item and (not string_list(item["command"]) or not item["command"]):
                errors.append(f"acceptance_criteria[{index}].command must be non-empty argv")
            if item.get("cwd", ".") != "." and not relative_path(item.get("cwd")):
                errors.append(f"acceptance_criteria[{index}].cwd must be relative or '.'")
        if len(set(ids)) != len(ids):
            errors.append("acceptance criterion IDs must be unique")
    decisions = payload.get("confirmed_decisions")
    if not isinstance(decisions, list):
        errors.append("confirmed_decisions must be a list")
    else:
        for index, item in enumerate(decisions):
            if (not isinstance(item, dict) or not nonblank(item.get("id")) or not nonblank(item.get("statement"))
                    or not string_list(item.get("evidence")) or not item.get("evidence")):
                errors.append(f"confirmed_decisions[{index}] requires id, statement, and non-empty evidence list")
    errors.extend(validate_evidence(payload.get("evidence_index"), "evidence_index"))
    errors.extend(snapshot_errors(payload.get("workspace_base"), "workspace_base"))
    if not errors:
        excluded = payload["workspace_base"]["excluded_paths"]
        watched = payload["owned_paths"] + payload["input_paths"]
        if any(under(path, excluded) or under(exclude, [path]) for path in watched for exclude in excluded):
            errors.append("exclusions overlap input_paths or owned_paths")
        links = [path for path, item in payload["workspace_base"]["files"].items() if item["kind"] == "symlink"]
        if any(under(path, links) or under(link, [path]) for path in watched for link in links):
            errors.append("watched paths overlap symlinks; use an isolated checkout with regular files")
    return errors


def validate_checks(value: Any) -> list[str]:
    if not isinstance(value, list):
        return ["checks must be a list"]
    errors, ids = [], []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            errors.append(f"checks[{index}] must be an object")
            continue
        if not nonblank(item.get("id")):
            errors.append(f"checks[{index}].id must be non-empty")
        ids.append(item.get("id"))
        if not string_list(item.get("command")) or not item.get("command"):
            errors.append(f"checks[{index}].command must be non-empty argv")
        if item.get("cwd") != "." and not relative_path(item.get("cwd")):
            errors.append(f"checks[{index}].cwd must be relative or '.'")
        status, code = item.get("status"), item.get("exit_code")
        if status not in CHECK_STATUSES or not nonblank(item.get("summary")):
            errors.append(f"checks[{index}] has invalid status or summary")
        if status == "not_run":
            if code is not None:
                errors.append(f"checks[{index}]: not_run requires null exit_code")
        elif type(code) is not int or (status == "passed") != (code == 0):
            errors.append(f"checks[{index}]: status and exit_code disagree")
        if status != "not_run":
            for field in ("workspace_digest", "stdout_digest", "stderr_digest"):
                if not isinstance(item.get(field), str) or not re.fullmatch(r"sha256:[0-9a-f]{64}", item[field]):
                    errors.append(f"checks[{index}].{field} must be a digest")
            if not relative_path(item.get("record")):
                errors.append(f"checks[{index}].record must be a relative path")
    if all(isinstance(item, str) for item in ids) and len(set(ids)) != len(ids):
        errors.append("check IDs must be unique")
    return errors


def validate_delta(payload: Any, expected_version: int | None = None, capsule: dict | None = None,
                   workspace_root: Path | None = None) -> list[str]:
    errors = shape(payload, DELTA_FIELDS, "delta")
    if not isinstance(payload, dict):
        return errors
    if capsule is None:
        errors.append("capsule is required to bind a delta; provide --capsule-file")
    else:
        errors.extend(f"capsule: {error}" for error in validate_capsule(capsule))
    if not nonblank(payload.get("conclusion")):
        errors.append("conclusion must be a non-empty string")
    for field in ("context_issues", "changed_files", "new_facts", "invalidated_assumptions", "open_questions", "risks"):
        if not string_list(payload.get(field)):
            errors.append(f"{field} must be a list of non-blank strings")
    if payload.get("recommended_next") is not None and not nonblank(payload["recommended_next"]):
        errors.append("recommended_next must be a non-empty string or null")
    status, context = payload.get("execution_status"), payload.get("context_status")
    if status not in DELTA_STATUSES:
        errors.append("execution_status must be completed, blocked, or needs_decision")
    if context not in CONTEXT_STATUSES:
        errors.append("invalid context_status")
    if context == "sufficient" and payload.get("context_issues") != []:
        errors.append("sufficient context requires context_issues to be []")
    if context in CONTEXT_STATUSES and context != "sufficient":
        if status not in ("blocked", "needs_decision") or not payload.get("context_issues"):
            errors.append("non-sufficient context requires a blocked decision and context_issues")
        if payload.get("changed_files") or payload.get("checks"):
            errors.append("non-sufficient context must not report changed_files or execution checks")
    version = payload.get("received_capsule_version")
    if type(version) is not int or version < 1:
        errors.append("received_capsule_version must be a positive integer")
    elif expected_version is not None and version != expected_version:
        errors.append("received_capsule_version mismatch")
    errors.extend(validate_evidence(payload.get("evidence"), "evidence"))
    errors.extend(validate_checks(payload.get("checks")))
    errors.extend(snapshot_errors(payload.get("workspace_after"), "workspace_after"))
    paths = payload.get("changed_files")
    if isinstance(paths, list) and any(not relative_path(path) for path in paths):
        errors.append("changed_files must contain normalized relative paths")
    if status == "completed" and context != "sufficient":
        errors.append("completed execution requires sufficient context")
    if errors:
        return errors
    assert capsule is not None
    for field in ("stage_id", "node_id"):
        if payload[field] != capsule[field]:
            errors.append(f"{field} does not match capsule")
    if version != capsule["capsule_version"]:
        errors.append("received_capsule_version does not match capsule")
    if payload.get("capsule_digest") != capsule_digest(capsule):
        errors.append("capsule_digest does not match canonical capsule")
    base, after = capsule["workspace_base"], payload["workspace_after"]
    if base["excluded_paths"] != after["excluded_paths"]:
        errors.append("workspace exclusions changed")
    actual = changed_paths(base["files"], after["files"])
    if sorted(set(paths)) != actual or len(set(paths)) != len(paths):
        errors.append("changed_files does not match actual workspace changes from baseline")
    if capsule["permission"] != "scoped-write" and actual:
        errors.append(f"{capsule['permission']} capsule must not change monitored files")
    if capsule["permission"] == "read-only" and any(check["status"] != "not_run" for check in payload["checks"]):
        errors.append("read-only capsule must not execute checks")
    check_ids = {check["id"] for check in payload["checks"]}
    for evidence in payload["evidence"]:
        if evidence["kind"] == "command" and evidence["ref"] not in check_ids:
            errors.append("command evidence references an unreported check")
    watched = capsule["owned_paths"] + capsule["input_paths"]
    links = [path for path, item in after["files"].items() if item["kind"] == "symlink"]
    if any(under(path, links) or under(link, [path]) for path in watched for link in links):
        errors.append("result introduces a watched symlink; reconcile before acceptance")
    for path in actual:
        if not under(path, capsule["owned_paths"]):
            errors.append(f"actual change outside owned_paths: {path}")
        if under(path, capsule["input_paths"]) and not under(path, capsule["owned_paths"]):
            errors.append(f"read dependency changed: {path}")
    if workspace_root is not None:
        current = snapshot(workspace_root, base["excluded_paths"])
        if current["files"] != after["files"]:
            errors.append("workspace changed after the worker result; reconcile before acceptance")
        for index, item in enumerate(payload["evidence"]):
            if item["kind"] != "path":
                continue
            ref = item["ref"]
            if not relative_path(ref):
                errors.append(f"evidence[{index}].ref must be workspace-relative")
                continue
            candidate = (workspace_root / ref).resolve()
            if not candidate.is_relative_to(workspace_root.resolve()) or not candidate.exists():
                errors.append(f"evidence[{index}].ref does not exist inside workspace")
    return errors


def validate_acceptance(review: Any, capsule: dict, delta: dict) -> list[str]:
    """A root decision, separate from a worker's execution report."""
    prerequisite = validate_delta(delta, capsule=capsule)
    if prerequisite:
        return prerequisite
    if not isinstance(review, dict) or review.get("acceptance_status") not in ("accepted", "rejected", "pending"):
        return ["acceptance_status must be accepted, rejected, or pending"]
    rows = review.get("criteria")
    if not isinstance(rows, list):
        return ["criteria must be a list"]
    criteria = {item["id"]: item for item in capsule["acceptance_criteria"]}
    evidence = {item["id"]: item for item in delta["evidence"]}
    checks = {item["id"]: item for item in delta["checks"]}
    errors, seen = [], []
    accepted = review["acceptance_status"] == "accepted"
    if accepted and delta["execution_status"] != "completed":
        errors.append("accepted requires completed execution")
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("criterion_id"), str) or row["criterion_id"] not in criteria:
            errors.append("unknown acceptance criterion")
            continue
        criterion = criteria[row["criterion_id"]]
        seen.append(row["criterion_id"])
        if row.get("decision") not in ("met", "unmet", "unverified") or not nonblank(row.get("reason")):
            errors.append("criterion requires decision and reason")
        ids = row.get("evidence_ids")
        if not string_list(ids) or any(key not in evidence for key in ids):
            errors.append("criterion references missing evidence")
            continue
        if row.get("decision") == "met":
            if not ids or any(not evidence[key]["verified"] for key in ids):
                errors.append("met criterion requires verified evidence")
            if criterion["verification"] == "command":
                linked = [checks.get(evidence[key]["ref"]) for key in ids if evidence[key]["kind"] == "command"]
                if not criterion.get("command"):
                    errors.append("command criterion must pin command argv before acceptance; update the node contract")
                elif not any(check and check["status"] != "not_run"
                             and check["exit_code"] == criterion["expected_exit_code"]
                             and check["command"] == criterion["command"]
                             and check["cwd"] == criterion.get("cwd", ".") for check in linked):
                    errors.append("required check has no matching planned command, cwd and expected exit code")
        if accepted and row.get("decision") != "met":
            errors.append("accepted requires every criterion to be met")
    if sorted(seen) != sorted(criteria):
        errors.append("acceptance must cover each criterion exactly once")
    return errors


def read_payload(path: str | None) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8")) if path else json.load(sys.stdin)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kind", choices=("capsule", "delta"), required=True)
    parser.add_argument("--file")
    parser.add_argument("--capsule-file")
    parser.add_argument("--workspace-root", type=Path)
    parser.add_argument("--expected-version", type=int, help="Expected node version, never a global stage revision.")
    args = parser.parse_args()
    if args.kind == "delta" and not args.capsule_file:
        print("INVALID delta: --capsule-file is required", file=sys.stderr)
        return 2
    try:
        payload = read_payload(args.file)
        capsule = read_payload(args.capsule_file) if args.capsule_file else None
        errors = (validate_capsule(payload, args.expected_version) if args.kind == "capsule" else
                  validate_delta(payload, args.expected_version, capsule, args.workspace_root))
    except (OSError, ValueError, RecursionError):
        print(f"INVALID {args.kind}: unreadable input or unstable workspace", file=sys.stderr)
        return 2
    if errors:
        print("\n".join(f"INVALID {args.kind}: {error}" for error in errors), file=sys.stderr)
        return 2
    version = payload["capsule_version" if args.kind == "capsule" else "received_capsule_version"]
    print(f"VALID {args.kind} version={version} digest={capsule_digest(payload) if args.kind == 'capsule' else payload['capsule_digest']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
