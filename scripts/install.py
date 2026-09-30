from __future__ import annotations

import argparse
import re
import sys
import tomllib
from datetime import datetime, timezone
from pathlib import Path

from kitlib import atomic_write, is_within, load_json, sha256_bytes, sha256_file, state_paths, write_json
from config_merge import ConfigMergeError, merge_values


VERSION = "0.3.0"
AGENTS_START = "<!-- codex-team-orchestrator:start -->"
AGENTS_END = "<!-- codex-team-orchestrator:end -->"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Install Codex Team Orchestrator safely.")
    parser.add_argument("--codex-home", type=Path, help="Codex home directory (default: CODEX_HOME or ~/.codex).")
    parser.add_argument("--user-home", type=Path, help="User home used for ~/.agents (default: current home).")
    parser.add_argument("--apply-preset", action="store_true", help="Apply routing, safety and concurrency settings; preserve existing model choices.")
    parser.add_argument("--model-preset", choices=("astra", "sol"), help="Explicitly select Astra or GPT-6.1 Sol, with Luna defaults; clear managed role model overrides. Requires --apply-preset.")
    parser.add_argument("--skill-location", choices=("codex", "agents"), default="codex", help="Select the client-supported Skill discovery root; default: codex.")
    parser.add_argument("--dry-run", action="store_true", help="Show planned changes without writing files.")
    parser.add_argument("--force", action="store_true", help="Replace conflicting managed Skill or agent files after backing them up.")
    args = parser.parse_args()
    if args.model_preset and not args.apply_preset:
        parser.error("--model-preset requires --apply-preset")
    return args


def resolve_homes(args: argparse.Namespace) -> tuple[Path, Path]:
    user_home = (args.user_home or Path.home()).expanduser().resolve()
    env_home = __import__("os").environ.get("CODEX_HOME")
    codex_home = (args.codex_home or (Path(env_home) if env_home else user_home / ".codex")).expanduser().resolve()
    return codex_home, user_home


def merge_config(existing: str, preset_path: Path, model_preset: str | None = None) -> str:
    selected = tomllib.loads(preset_path.read_text(encoding="utf-8"))
    if model_preset:
        if model_preset not in ("astra", "sol"):
            raise ConfigMergeError("Unsupported model preset")
        models = tomllib.loads((preset_path.parent / f"models.{model_preset}.toml").read_text(encoding="utf-8"))
        selected.update({key: value for key, value in models.items() if key != "agents"})
        selected.setdefault("agents", {}).update(models.get("agents", {}))
    return merge_values(existing, selected)


def merge_agents(existing: str, preset_path: Path) -> str:
    pattern = re.compile(
        rf"\n?{re.escape(AGENTS_START)}.*?{re.escape(AGENTS_END)}\n?",
        re.DOTALL,
    )
    base = pattern.sub("\n", existing.replace("\r\n", "\n")).rstrip()
    preset = preset_path.read_text(encoding="utf-8").strip()
    block = f"{AGENTS_START}\n{preset}\n{AGENTS_END}"
    return f"{base}\n\n{block}\n" if base else f"{block}\n"


def source_operations(repo_root: Path, codex_home: Path, user_home: Path, skill_location: str = "codex", model_preset: str | None = None) -> list[dict[str, object]]:
    operations: list[dict[str, object]] = []
    skill_source = repo_root / "skills" / "orchestrator"
    skill_target = (codex_home / "skills" if skill_location == "codex" else user_home / ".agents" / "skills") / "orchestrator"
    for source in sorted(path for path in skill_source.rglob("*") if path.is_file()
                         and "__pycache__" not in path.parts and path.suffix != ".pyc"):
        operations.append({"source": source, "target": skill_target / source.relative_to(skill_source), "kind": "skill"})
    for name in ("luna_worker.toml", "terra_scout.toml"):
        source, target = repo_root / "agents" / name, codex_home / "agents" / name
        operation: dict[str, object] = {"source": source, "target": target, "kind": "agent"}
        if target.is_file() and model_preset is None:
            existing = tomllib.loads(target.read_text(encoding="utf-8"))
            preserved = {key: existing[key] for key in ("model", "model_reasoning_effort") if key in existing}
            if any(not isinstance(value, str) or not value.strip() for value in preserved.values()):
                raise ConfigMergeError("Existing role model settings must be non-empty strings")
            if preserved:
                operation["data"] = merge_values(source.read_text(encoding="utf-8"), preserved).encode("utf-8")
        operations.append(operation)
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


def manifest_manages_root(manifest: dict[str, object], root: Path) -> bool:
    records = manifest.get("files")
    if not isinstance(records, list):
        return False
    for record in records:
        if not isinstance(record, dict):
            continue
        value = record.get("path")
        if isinstance(value, str) and value and is_within(Path(value), root):
            return True
    return False


def main() -> int:
    args = parse_args()
    codex_home, user_home = resolve_homes(args)
    repo_root = Path(__file__).resolve().parent.parent
    state_dir, manifest_path = state_paths(codex_home)

    operations = source_operations(repo_root, codex_home, user_home, args.skill_location, args.model_preset)
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
                    "data": merge_config(existing_config, repo_root / "presets" / "config.example.toml", args.model_preset).encode("utf-8"),
                    "kind": "preset-config",
                },
                {
                    "target": agents_path,
                    "data": merge_agents(existing_agents, repo_root / "presets" / "AGENTS.example.md").encode("utf-8"),
                    "kind": "preset-agents",
                },
            ]
        )

    manifest = load_json(manifest_path) if manifest_path.exists() else None
    legacy_skill_root = (user_home / ".agents" / "skills" if args.skill_location == "codex" else codex_home / "skills") / "orchestrator"
    if legacy_skill_root.is_dir() and not (
        manifest is not None and manifest_manages_root(manifest, legacy_skill_root)
    ):
        print(
            "Unmanaged duplicate Skill directory exists; review it before installing: "
            f"{legacy_skill_root}.",
            file=sys.stderr,
        )
        return 2

    if manifest is not None:
        if (manifest.get("model_preset") == args.model_preset
                and manifest.get("skill_location", "codex") == args.skill_location
                and is_idempotent(manifest, operations, args.apply_preset)):
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
    if args.apply_preset:
        print("Preset: routing, workspace-write/on-request safety, concurrency")
        print(f"Models: explicit {args.model_preset} preset; managed roles inherit its defaults" if args.model_preset else "Models: existing root/default/role choices preserved")
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
            "model_preset": args.model_preset,
            "skill_location": args.skill_location,
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
    try:
        raise SystemExit(main())
    except (ConfigMergeError, OSError, ValueError) as error:
        print(f"Install stopped before completion: {error}", file=sys.stderr)
        raise SystemExit(2)
