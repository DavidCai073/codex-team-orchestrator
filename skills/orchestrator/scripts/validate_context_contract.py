from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any


CAPSULE_FIELDS = (
    "schema_version",
    "stage_id",
    "capsule_version",
    "node_id",
    "objective",
    "acceptance_criteria",
    "confirmed_decisions",
    "non_goals",
    "dependencies_and_interfaces",
    "owned_paths",
    "permission",
    "safety_boundaries",
    "known_failures",
    "evidence_index",
    "open_questions",
)

DELTA_FIELDS = (
    "stage_id",
    "node_id",
    "status",
    "received_capsule_version",
    "context_status",
    "context_issues",
    "capsule_digest",
    "conclusion",
    "evidence",
    "changed_files",
    "checks",
    "new_facts",
    "invalidated_assumptions",
    "open_questions",
    "risks",
    "recommended_next",
)

STRING_CAPSULE_FIELDS = (
    "acceptance_criteria",
    "non_goals",
    "dependencies_and_interfaces",
    "owned_paths",
    "safety_boundaries",
    "known_failures",
    "open_questions",
)
STRING_DELTA_FIELDS = (
    "context_issues",
    "changed_files",
    "new_facts",
    "invalidated_assumptions",
    "open_questions",
    "risks",
)

CONTEXT_STATUSES = {
    "sufficient",
    "missing_context",
    "stale_context",
    "contradictory_context",
}
DELTA_STATUSES = {"completed", "blocked", "needs_decision"}
PERMISSIONS = {"read-only", "scoped-write", "execute-checks"}
CHECK_STATUSES = {"passed", "failed", "not_run"}
EVIDENCE_KINDS = {"path", "url", "command"}
_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_DRIVE_RE = re.compile(r"^[A-Za-z]:[\\/]")


def is_positive_integer(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def capsule_digest(payload: dict[str, Any]) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def missing_fields(payload: dict[str, Any], required: tuple[str, ...]) -> list[str]:
    return [field for field in required if field not in payload]


def validate_non_empty_string(value: Any, label: str, errors: list[str]) -> None:
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{label} must be a non-empty string")


def validate_string_fields(payload: dict[str, Any], fields: tuple[str, ...], errors: list[str]) -> None:
    for field in fields:
        if field not in payload:
            continue
        value = payload[field]
        if not isinstance(value, list):
            errors.append(f"{field} must be a list; use [] when empty")
            continue
        for index, item in enumerate(value):
            if not isinstance(item, str) or not item.strip():
                errors.append(f"{field}[{index}] must be a non-empty string")


def normalize_relative_path(value: Any, label: str, errors: list[str]) -> str | None:
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{label} must be a non-empty relative path")
        return None
    raw = value.strip().replace("\\", "/")
    if raw.startswith("/") or _DRIVE_RE.match(value) or "*" in raw or "?" in raw:
        errors.append(f"{label} must be a normalized relative path without wildcards")
        return None
    parts = raw.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        errors.append(f"{label} must not contain empty, '.', or '..' path components")
        return None
    return "/".join(parts)


def validate_owned_paths(payload: dict[str, Any], errors: list[str]) -> None:
    value = payload.get("owned_paths")
    if not isinstance(value, list):
        errors.append("owned_paths must be a list; use [] when empty")
        return
    for index, item in enumerate(value):
        normalize_relative_path(item, f"owned_paths[{index}]", errors)


def validate_evidence_item(value: Any, label: str, errors: list[str]) -> None:
    if not isinstance(value, dict):
        errors.append(f"{label} must be an object")
        return
    for field in ("kind", "ref", "result"):
        validate_non_empty_string(value.get(field), f"{label}.{field}", errors)
    if value.get("kind") not in EVIDENCE_KINDS:
        errors.append(f"{label}.kind must be one of: {', '.join(sorted(EVIDENCE_KINDS))}")
    if not isinstance(value.get("verified"), bool):
        errors.append(f"{label}.verified must be a boolean")


def validate_evidence_list(value: Any, field: str, errors: list[str]) -> None:
    if not isinstance(value, list):
        errors.append(f"{field} must be a list; use [] when empty")
        return
    for index, item in enumerate(value):
        validate_evidence_item(item, f"{field}[{index}]", errors)


def validate_decisions(value: Any, errors: list[str]) -> None:
    if not isinstance(value, list):
        errors.append("confirmed_decisions must be a list; use [] when empty")
        return
    for index, item in enumerate(value):
        label = f"confirmed_decisions[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{label} must be an object")
            continue
        validate_non_empty_string(item.get("id"), f"{label}.id", errors)
        validate_non_empty_string(item.get("statement"), f"{label}.statement", errors)
        evidence = item.get("evidence")
        if isinstance(evidence, list):
            if not evidence:
                errors.append(f"{label}.evidence must not be empty")
            for evidence_index, entry in enumerate(evidence):
                validate_non_empty_string(entry, f"{label}.evidence[{evidence_index}]", errors)
        else:
            validate_non_empty_string(evidence, f"{label}.evidence", errors)


def validate_checks(value: Any, errors: list[str]) -> None:
    if not isinstance(value, list):
        errors.append("checks must be a list; use [] when empty")
        return
    for index, item in enumerate(value):
        label = f"checks[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{label} must be an object")
            continue
        validate_non_empty_string(item.get("command"), f"{label}.command", errors)
        validate_non_empty_string(item.get("summary"), f"{label}.summary", errors)
        if item.get("status") not in CHECK_STATUSES:
            errors.append(f"{label}.status must be one of: {', '.join(sorted(CHECK_STATUSES))}")


def validate_capsule(payload: Any, expected_version: int | None = None) -> list[str]:
    if not isinstance(payload, dict):
        return ["capsule must be a JSON object"]
    errors = [f"missing required field: {field}" for field in missing_fields(payload, CAPSULE_FIELDS)]
    validate_non_empty_string(payload.get("stage_id"), "stage_id", errors)
    validate_non_empty_string(payload.get("node_id"), "node_id", errors)
    validate_non_empty_string(payload.get("objective"), "objective", errors)
    if payload.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    version = payload.get("capsule_version")
    if not is_positive_integer(version):
        errors.append("capsule_version must be a positive integer")
    elif expected_version is not None and version != expected_version:
        errors.append(f"capsule_version mismatch: expected {expected_version}, received {version}")
    validate_string_fields(payload, STRING_CAPSULE_FIELDS, errors)
    acceptance = payload.get("acceptance_criteria")
    if isinstance(acceptance, list) and not acceptance:
        errors.append("acceptance_criteria must contain at least one observable criterion")
    validate_decisions(payload.get("confirmed_decisions"), errors)
    validate_evidence_list(payload.get("evidence_index"), "evidence_index", errors)
    validate_owned_paths(payload, errors)
    if payload.get("permission") not in PERMISSIONS:
        errors.append(f"permission must be one of: {', '.join(sorted(PERMISSIONS))}")
    boundaries = payload.get("safety_boundaries")
    if isinstance(boundaries, list) and not boundaries:
        errors.append("safety_boundaries must not be empty")
    return errors


def path_is_within_owned(path: str, owned_paths: list[str]) -> bool:
    normalized = path.replace("\\", "/").strip("/")
    return any(normalized == owned or normalized.startswith(owned + "/") for owned in owned_paths)


def validate_workspace_evidence(
    evidence: list[Any], workspace_root: Path | None, errors: list[str]
) -> None:
    if workspace_root is None:
        return
    root = workspace_root.expanduser().resolve()
    for index, item in enumerate(evidence):
        if not isinstance(item, dict) or item.get("kind") != "path":
            continue
        ref = item.get("ref")
        if not isinstance(ref, str) or not ref.strip():
            continue
        candidate = Path(ref)
        if not candidate.is_absolute():
            candidate = root / candidate
        try:
            resolved = candidate.resolve()
            resolved.relative_to(root)
        except (OSError, ValueError):
            errors.append(f"evidence[{index}].ref escapes workspace_root")
            continue
        if not resolved.exists():
            errors.append(f"evidence[{index}].ref does not exist under workspace_root: {ref}")


def validate_delta(
    payload: Any,
    expected_version: int | None = None,
    capsule: dict[str, Any] | None = None,
    workspace_root: Path | None = None,
) -> list[str]:
    if not isinstance(payload, dict):
        return ["delta must be a JSON object"]
    errors = [f"missing required field: {field}" for field in missing_fields(payload, DELTA_FIELDS)]
    if capsule is None:
        errors.append("capsule is required to bind a delta; provide --capsule-file")
    validate_non_empty_string(payload.get("stage_id"), "stage_id", errors)
    validate_non_empty_string(payload.get("node_id"), "node_id", errors)
    validate_non_empty_string(payload.get("conclusion"), "conclusion", errors)
    validate_string_fields(payload, STRING_DELTA_FIELDS, errors)
    validate_evidence_list(payload.get("evidence"), "evidence", errors)
    validate_checks(payload.get("checks"), errors)
    recommended_next = payload.get("recommended_next")
    if recommended_next is not None:
        validate_non_empty_string(recommended_next, "recommended_next", errors)
    status = payload.get("status")
    if status not in DELTA_STATUSES:
        errors.append(f"status must be one of: {', '.join(sorted(DELTA_STATUSES))}")
    context_status = payload.get("context_status")
    if context_status not in CONTEXT_STATUSES:
        errors.append(f"context_status must be one of: {', '.join(sorted(CONTEXT_STATUSES))}")
    version = payload.get("received_capsule_version")
    if not is_positive_integer(version):
        errors.append("received_capsule_version must be a positive integer")
    elif expected_version is not None and version != expected_version:
        errors.append(f"received_capsule_version mismatch: expected {expected_version}, received {version}")
    digest = payload.get("capsule_digest")
    if not isinstance(digest, str) or not _DIGEST_RE.fullmatch(digest):
        errors.append("capsule_digest must match sha256:<64 lowercase hex characters>")

    if context_status in CONTEXT_STATUSES:
        issues = payload.get("context_issues")
        if context_status == "sufficient" and issues != []:
            errors.append("sufficient context requires context_issues to be []")
        if context_status != "sufficient":
            if status not in {"blocked", "needs_decision"}:
                errors.append("non-sufficient context requires blocked or needs_decision status")
            if payload.get("changed_files"):
                errors.append("non-sufficient context must not report changed_files")
            if payload.get("checks"):
                errors.append("non-sufficient context must not run execution checks")
            if not isinstance(issues, list) or not issues:
                errors.append("non-sufficient context must identify context_issues")

    if status == "completed":
        if context_status != "sufficient":
            errors.append("completed delta requires sufficient context")
        evidence = payload.get("evidence")
        if not isinstance(evidence, list) or not any(
            isinstance(item, dict) and item.get("verified") is True for item in evidence
        ):
            errors.append("completed delta requires at least one verified evidence item")

    if capsule is not None:
        capsule_errors = validate_capsule(capsule)
        if capsule_errors:
            errors.extend(f"capsule: {error}" for error in capsule_errors)
        else:
            if payload.get("stage_id") != capsule.get("stage_id"):
                errors.append("stage_id does not match capsule")
            if payload.get("node_id") != capsule.get("node_id"):
                errors.append("node_id does not match capsule")
            if payload.get("received_capsule_version") != capsule.get("capsule_version"):
                errors.append("received_capsule_version does not match capsule")
            expected_digest = capsule_digest(capsule)
            if payload.get("capsule_digest") != expected_digest:
                errors.append("capsule_digest does not match canonical capsule")
            changed_files = payload.get("changed_files")
            permission = capsule.get("permission")
            owned_paths = [
                item.replace("\\", "/").strip("/")
                for item in capsule.get("owned_paths", [])
                if isinstance(item, str)
            ]
            if permission in {"read-only", "execute-checks"} and changed_files:
                errors.append(f"{permission} capsule delta must not report changed_files")
            if permission == "scoped-write" and isinstance(changed_files, list):
                for index, item in enumerate(changed_files):
                    normalized = normalize_relative_path(item, f"changed_files[{index}]", errors)
                    if normalized and not path_is_within_owned(normalized, owned_paths):
                        errors.append(f"changed_files[{index}] is outside owned_paths")

    validate_workspace_evidence(payload.get("evidence", []), workspace_root, errors)
    return errors


def read_payload(path: str | None) -> Any:
    if path:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    return json.load(sys.stdin)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate an orchestrator Context Capsule or State Delta JSON payload."
    )
    parser.add_argument("--kind", choices=("capsule", "delta"), required=True)
    parser.add_argument("--file", help="Read JSON from this file; defaults to stdin.")
    parser.add_argument("--capsule-file", help="Capsule JSON required when validating a delta.")
    parser.add_argument("--workspace-root", type=Path, help="Check path evidence exists below this root.")
    parser.add_argument("--expected-version", type=int)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.kind == "delta" and not args.capsule_file:
        print("INVALID delta: --capsule-file is required for capsule binding", file=sys.stderr)
        return 2
    try:
        payload = read_payload(args.file)
        capsule = read_payload(args.capsule_file) if args.capsule_file else None
    except (OSError, json.JSONDecodeError) as error:
        print(f"INVALID {args.kind}: {error}", file=sys.stderr)
        return 2
    if args.kind == "capsule":
        errors = validate_capsule(payload, args.expected_version)
        digest = capsule_digest(payload) if isinstance(payload, dict) and not errors else None
        version_field = "capsule_version"
    else:
        errors = validate_delta(payload, args.expected_version, capsule, args.workspace_root)
        digest = payload.get("capsule_digest") if isinstance(payload, dict) else None
        version_field = "received_capsule_version"
    if errors:
        for error in errors:
            print(f"INVALID {args.kind}: {error}", file=sys.stderr)
        return 2
    print(f"VALID {args.kind} version={payload[version_field]} digest={digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
