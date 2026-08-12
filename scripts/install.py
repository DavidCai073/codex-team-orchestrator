from __future__ import annotations

import argparse
import re
import shutil
import sys
import tomllib
from datetime import datetime, timezone
from pathlib import Path

from kitlib import atomic_write, load_json, sha256_bytes, sha256_file, state_paths, write_json


VERSION = "0.1.0"
AGENTS_START = "<!-- codex-team-orchestrator:start -->"
AGENTS_END = "<!-- codex-team-orchestrator:end -->"
TABLE_RE = re.compile(r"^\s*\[([^\]]+)\]\s*(?:#.*)?$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Install Codex Team Orchestrator safely.")
    parser.add_argument("--codex-home", type=Path, help="Codex home directory (default: CODEX_HOME or ~/.codex).")
    parser.add_argument("--user-home", type=Path, help="User home used for ~/.agents (default: current home).")
    parser.add_argument("--apply-preset", action="store_true", help="Merge the sanitized config and AGENTS presets after backing up existing files.")
    parser.add_argument("--dry-run", action="store_true", help="Show planned changes without writing files.")
    parser.add_argument("--force", action="store_true", help="Replace conflicting managed Skill or agent files after backing them up.")
    return parser.parse_args()


def resolve_homes(args: argparse.Namespace) -> tuple[Path, Path]:
    user_home = (args.user_home or Path.home()).expanduser().resolve()
    env_home = __import__("os").environ.get("CODEX_HOME")
    codex_home = (args.codex_home or (Path(env_home) if env_home else user_home / ".codex")).expanduser().resolve()
    return codex_home, user_home


def toml_literal(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, str):
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    raise TypeError(f"Unsupported preset value: {value!r}")


def assignment_index(lines: list[str], start: int, end: int, key: str) -> int | None:
    pattern = re.compile(rf"^\s*{re.escape(key)}\s*=")
    for index in range(start, end):
        if pattern.match(lines[index]) and not lines[index].lstrip().startswith("#"):
            return index
    return None


def first_table_index(lines: list[str], start: int = 0) -> int:
    for index in range(start, len(lines)):
        if TABLE_RE.match(lines[index]):
            return index
    return len(lines)


def merge_config(existing: str, preset_path: Path) -> str:
    preset = tomllib.loads(preset_path.read_text(encoding="utf-8"))
    lines = existing.replace("\r\n", "\n").split("\n") if existing else []
    if lines and lines[-1] == "":
        lines.pop()

    top_values = {key: value for key, value in preset.items() if key != "agents"}
    top_end = first_table_index(lines)
    missing_top: list[str] = []
    for key, value in top_values.items():
        index = assignment_index(lines, 0, top_end, key)
        replacement = f"{key} = {toml_literal(value)}"
        if index is None:
            missing_top.append(replacement)
        else:
            lines[index] = replacement
    if missing_top:
        insertion = missing_top + ([""] if top_end < len(lines) else [])
        lines[top_end:top_end] = insertion

    agents_values = preset.get("agents", {})
    if not isinstance(agents_values, dict):
        raise ValueError("Preset [agents] must be a table")
    agents_header = None
    for index, line in enumerate(lines):
        match = TABLE_RE.match(line)
        if match and match.group(1).strip() == "agents":
            agents_header = index
            break
    if agents_header is None:
        if lines and lines[-1] != "":
            lines.append("")
        lines.append("[agents]")
        for key, value in agents_values.items():
            lines.append(f"{key} = {toml_literal(value)}")
    else:
        agents_end = first_table_index(lines, agents_header + 1)
        missing_agents: list[str] = []
        for key, value in agents_values.items():
            index = assignment_index(lines, agents_header + 1, agents_end, key)
            replacement = f"{key} = {toml_literal(value)}"
            if index is None:
                missing_agents.append(replacement)
            else:
                lines[index] = replacement
        if missing_agents:
            lines[agents_end:agents_end] = missing_agents

    result = "\n".join(lines).rstrip() + "\n"
    tomllib.loads(result)
    return result


def merge_agents(existing: str, preset_path: Path) -> str:
    pattern = re.compile(
        rf"\n?{re.escape(AGENTS_START)}.*?{re.escape(AGENTS_END)}\n?",
        re.DOTALL,
    )
    base = pattern.sub("\n", existing.replace("\r\n", "\n")).rstrip()
    preset = preset_path.read_text(encoding="utf-8").strip()
    block = f"{AGENTS_START}\n{preset}\n{AGENTS_END}"
    return f"{base}\n\n{block}\n" if base else f"{block}\n"


def source_operations(repo_root: Path, codex_home: Path, user_home: Path) -> list[dict[str, object]]:
    operations: list[dict[str, object]] = []
    skill_source = repo_root / "skills" / "orchestrator"
    skill_target = user_home / ".agents" / "skills" / "orchestrator"
    for source in sorted(path for path in skill_source.rglob("*") if path.is_file()):
        operations.append({"source": source, "target": skill_target / source.relative_to(skill_source), "kind": "skill"})
    for name in ("luna_worker.toml", "terra_scout.toml"):
        operations.append({"source": repo_root / "agents" / name, "target": codex_home / "agents" / name, "kind": "agent"})
    return operations


def operation_bytes(operation: dict[str, object]) -> bytes:
    if "data" in operation:
        return operation["data"]  # type: ignore[return-value]
    return Path(operation["source"]).read_bytes()


def is_idempotent(manifest: dict[str, object], operations: list[dict[str, object]], preset_applied: bool) -> bool:
    if manifest.get("version") != VERSION or manifest.get("preset_applied") is not preset_applied:
        return False
    records = manifest.get("files")
    if not isinstance(records, list) or len(records) != len(operations):
        return False
    expected = {str(Path(op["target"]).resolve()): sha256_bytes(operation_bytes(op)) for op in operations}
    for record in records:
        if not isinstance(record, dict):
            return False
        target = str(Path(str(record.get("path", ""))).resolve())
        path = Path(target)
        if target not in expected or not path.is_file():
            return False
        if sha256_file(path) != expected[target] or record.get("installed_sha256") != expected[target]:
            return False
    return True


def main() -> int:
    args = parse_args()
    codex_home, user_home = resolve_homes(args)
    repo_root = Path(__file__).resolve().parent.parent
    state_dir, manifest_path = state_paths(codex_home)

    operations = source_operations(repo_root, codex_home, user_home)
    for operation in operations:
        source = Path(operation["source"])
        if not source.is_file():
            raise FileNotFoundError(f"Missing package file: {source}")

    if args.apply_preset:
        config_path = codex_home / "config.toml"
        agents_path = codex_home / "AGENTS.md"
        existing_config = config_path.read_text(encoding="utf-8") if config_path.exists() else ""
        existing_agents = agents_path.read_text(encoding="utf-8") if agents_path.exists() else ""
        operations.extend(
            [
                {
                    "target": config_path,
                    "data": merge_config(existing_config, repo_root / "presets" / "config.example.toml").encode("utf-8"),
                    "kind": "preset-config",
                },
                {
                    "target": agents_path,
                    "data": merge_agents(existing_agents, repo_root / "presets" / "AGENTS.example.md").encode("utf-8"),
                    "kind": "preset-agents",
                },
            ]
        )

    if manifest_path.exists():
        manifest = load_json(manifest_path)
        if is_idempotent(manifest, operations, args.apply_preset):
            print(f"Already installed: {VERSION}")
            return 0
        print(
            f"Existing installation state differs from this request: {manifest_path}. "
            "Uninstall it first so the original backups are not lost.",
            file=sys.stderr,
        )
        return 2

    conflicts: list[Path] = []
    for operation in operations:
        target = Path(operation["target"])
        if target.exists() and target.read_bytes() != operation_bytes(operation):
            if str(operation["kind"]).startswith("preset-"):
                continue
            conflicts.append(target)
    if conflicts and not args.force:
        print("Conflicting managed files already exist:", file=sys.stderr)
        for path in conflicts:
            print(f"  {path}", file=sys.stderr)
        print("Review them, then re-run with --force if replacement is intended.", file=sys.stderr)
        return 2

    print(f"Codex home: {codex_home}")
    print(f"User home:  {user_home}")
    for operation in operations:
        target = Path(operation["target"])
        action = "update" if target.exists() else "create"
        print(f"{action:>6}  {target}")
    if args.dry_run:
        print("Dry run complete; no files were changed.")
        return 0

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    backup_dir = state_dir / "backups" / timestamp
    records: list[dict[str, object]] = []
    written: list[dict[str, object]] = []
    try:
        for index, operation in enumerate(operations):
            target = Path(operation["target"])
            data = operation_bytes(operation)
            record: dict[str, object] = {
                "path": str(target.resolve()),
                "kind": operation["kind"],
                "created": not target.exists(),
                "installed_sha256": sha256_bytes(data),
                "backup_path": None,
                "original_sha256": None,
            }
            if target.exists():
                original = target.read_bytes()
                backup_path = backup_dir / f"{index:03d}-{target.name}.bak"
                atomic_write(backup_path, original)
                record["backup_path"] = str(backup_path.resolve())
                record["original_sha256"] = sha256_bytes(original)
            records.append(record)
            atomic_write(target, data)
            written.append(record)

        manifest = {
            "schema_version": 1,
            "version": VERSION,
            "installed_at": datetime.now(timezone.utc).isoformat(),
            "codex_home": str(codex_home),
            "user_home": str(user_home),
            "preset_applied": args.apply_preset,
            "files": records,
        }
        write_json(manifest_path, manifest)
    except Exception:
        for record in reversed(written):
            target = Path(str(record["path"]))
            backup_value = record.get("backup_path")
            if backup_value:
                atomic_write(target, Path(str(backup_value)).read_bytes())
            else:
                target.unlink(missing_ok=True)
        raise

    print(f"Installed Codex Team Orchestrator {VERSION}.")
    print("Restart Codex before testing the custom agents.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
