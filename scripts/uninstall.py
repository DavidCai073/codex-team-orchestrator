from __future__ import annotations

import argparse
import sys
from pathlib import Path

from kitlib import atomic_write, is_within, load_json, sha256_file, state_paths, validate_managed_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Safely uninstall Codex Team Orchestrator.")
    parser.add_argument("--codex-home", type=Path, help="Codex home directory (default: CODEX_HOME or ~/.codex).")
    parser.add_argument("--user-home", type=Path, help="User home used for ~/.agents (default: current home).")
    parser.add_argument("--dry-run", action="store_true", help="Show restoration actions without changing files.")
    return parser.parse_args()


def resolve_homes(args: argparse.Namespace) -> tuple[Path, Path]:
    user_home = (args.user_home or Path.home()).expanduser().resolve()
    env_home = __import__("os").environ.get("CODEX_HOME")
    codex_home = (args.codex_home or (Path(env_home) if env_home else user_home / ".codex")).expanduser().resolve()
    return codex_home, user_home


def remove_empty_managed_dirs(paths: list[Path], codex_home: Path, user_home: Path) -> None:
    skill_roots = (
        (codex_home / "skills" / "orchestrator").resolve(),
        (user_home / ".agents" / "skills" / "orchestrator").resolve(),
    )
    for parent in sorted({path.parent.resolve() for path in paths}, key=lambda item: len(item.parts), reverse=True):
        current = parent
        root = next((candidate for candidate in skill_roots if is_within(current, candidate)), None)
        while root is not None and is_within(current, root):
            try:
                current.rmdir()
            except OSError:
                break
            if current == root:
                break
            current = current.parent
    try:
        (codex_home / "agents").rmdir()
    except OSError:
        pass


def main() -> int:
    args = parse_args()
    codex_home, user_home = resolve_homes(args)
    state_dir, manifest_path = state_paths(codex_home)
    if not manifest_path.is_file():
        print(f"No installation state found at {manifest_path}.", file=sys.stderr)
        return 2

    manifest = load_json(manifest_path)
    files = manifest.get("files")
    if not isinstance(files, list):
        raise ValueError("Installation manifest has no valid files list")

    conflicts: list[str] = []
    records: list[dict[str, object]] = []
    for value in files:
        if not isinstance(value, dict):
            raise ValueError("Installation manifest contains an invalid file record")
        target = Path(str(value.get("path", ""))).resolve()
        validate_managed_path(target, codex_home, user_home)
        expected = value.get("installed_sha256")
        if not target.is_file():
            conflicts.append(f"missing: {target}")
        elif sha256_file(target) != expected:
            conflicts.append(f"modified: {target}")
        backup_value = value.get("backup_path")
        if backup_value:
            backup = Path(str(backup_value)).resolve()
            expected_original = value.get("original_sha256")
            if not is_within(backup, state_dir / "backups") or not backup.is_file():
                conflicts.append(f"backup unavailable: {target}")
            elif not isinstance(expected_original, str) or sha256_file(backup) != expected_original:
                conflicts.append(f"backup checksum mismatch: {target}")
        records.append(value)

    if conflicts:
        print("Uninstall stopped to protect files changed after installation:", file=sys.stderr)
        for conflict in conflicts:
            print(f"  {conflict}", file=sys.stderr)
        print(f"Resolve the conflicts manually; installation state remains at {manifest_path}.", file=sys.stderr)
        return 2

    for record in reversed(records):
        target = Path(str(record["path"])).resolve()
        backup_value = record.get("backup_path")
        action = "restore" if backup_value else "remove"
        print(f"{action:>7}  {target}")
    if args.dry_run:
        print("Dry run complete; no files were changed.")
        return 0

    rollback: list[tuple[Path, bytes]] = []
    try:
        for record in reversed(records):
            target = Path(str(record["path"])).resolve()
            rollback.append((target, target.read_bytes()))
            backup_value = record.get("backup_path")
            if backup_value:
                atomic_write(target, Path(str(backup_value)).read_bytes())
            else:
                target.unlink()
        manifest_path.unlink()
    except Exception:
        for target, data in rollback:
            atomic_write(target, data)
        raise

    backup_paths = [Path(str(record["backup_path"])) for record in records if record.get("backup_path")]
    for path in backup_paths:
        path.unlink(missing_ok=True)
    for directory in sorted({path.parent for path in backup_paths}, key=lambda item: len(item.parts), reverse=True):
        try:
            directory.rmdir()
        except OSError:
            pass
    try:
        (state_dir / "backups").rmdir()
    except OSError:
        pass
    try:
        state_dir.rmdir()
    except OSError:
        pass
    remove_empty_managed_dirs([Path(str(record["path"])) for record in records], codex_home, user_home)
    print("Codex Team Orchestrator was uninstalled and original files were restored.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
