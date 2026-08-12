from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any


STATE_DIR_NAME = ".codex-team-orchestrator"
STATE_FILE_NAME = "install-state.json"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temp_path = Path(temp_name)
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_path, path)
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise


def write_json(path: Path, value: dict[str, Any]) -> None:
    payload = json.dumps(value, ensure_ascii=False, indent=2).encode("utf-8") + b"\n"
    atomic_write(path, payload)


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected an object in {path}")
    return value


def is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def validate_managed_path(path: Path, codex_home: Path, user_home: Path) -> None:
    skill_root = user_home / ".agents" / "skills" / "orchestrator"
    allowed_files = {
        codex_home / "config.toml",
        codex_home / "AGENTS.md",
        codex_home / "agents" / "luna_worker.toml",
        codex_home / "agents" / "terra_scout.toml",
    }
    resolved = path.resolve()
    if resolved in {item.resolve() for item in allowed_files}:
        return
    if is_within(resolved, skill_root):
        return
    raise ValueError(f"Manifest path is outside managed locations: {path}")


def state_paths(codex_home: Path) -> tuple[Path, Path]:
    state_dir = codex_home / STATE_DIR_NAME
    return state_dir, state_dir / STATE_FILE_NAME
