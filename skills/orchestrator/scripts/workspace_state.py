"""Portable file inventories. Retrospective observations, never a sandbox."""
from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import subprocess
from pathlib import Path, PureWindowsPath
from typing import Any


def digest(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    return "sha256:" + hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def relative_path(value: Any) -> bool:
    if not isinstance(value, str) or not value or value != value.strip():
        return False
    if "\\" in value or ":" in value or any(ord(char) < 32 for char in value):
        return False
    if any(char in value for char in '*?<>|"') or PureWindowsPath(value).drive:
        return False
    parts = value.split("/")
    return all(part not in {"", ".", "..", ".git"} and not part.endswith((" ", ".")) for part in parts)


def under(path: str, prefixes: list[str]) -> bool:
    return any(path == prefix or path.startswith(prefix + "/") for prefix in prefixes)


def changed_paths(before: dict, after: dict) -> list[str]:
    return sorted(key for key in before.keys() | after.keys() if before.get(key) != after.get(key))


def file_state(path: Path) -> dict:
    before = path.lstat()
    if getattr(before, "st_file_attributes", 0) & 0x400 and not stat.S_ISLNK(before.st_mode):
        raise ValueError("Unsupported Windows reparse point; use regular local files.")
    if stat.S_ISLNK(before.st_mode):
        content_hash = hashlib.sha256(os.readlink(path).encode("utf-8")).hexdigest()
        kind = "symlink"
    elif stat.S_ISREG(before.st_mode):
        hasher = hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                hasher.update(chunk)
        content_hash, kind = hasher.hexdigest(), "file"
    else:
        raise ValueError("Unsupported special file in monitored workspace.")
    after = path.lstat()
    if (before.st_mtime_ns, before.st_size, before.st_mode) != (after.st_mtime_ns, after.st_size, after.st_mode):
        raise ValueError("Workspace changed while hashing; retry after the writer has stopped.")
    return {"digest": "sha256:" + content_hash, "kind": kind, "executable": bool(before.st_mode & stat.S_IXUSR)}


def snapshot(root: Path, excluded_paths: list[str] | None = None) -> dict:
    root = root.resolve(strict=True)
    excluded_paths = sorted(set(excluded_paths or []))
    if not root.is_dir() or any(not relative_path(path) for path in excluded_paths):
        raise ValueError("Snapshot requires a directory and normalized relative exclusions.")
    files: dict[str, dict] = {}
    observed_stats: dict[Path, tuple] = {}
    def onerror(error: OSError) -> None:
        raise error
    for directory, subdirs, names in os.walk(root, followlinks=False, onerror=onerror):
        folder = Path(directory)
        for name in list(subdirs):
            candidate = folder / name
            relative = candidate.relative_to(root).as_posix()
            if name == ".git" or under(relative, excluded_paths):
                subdirs.remove(name)
            elif candidate.is_symlink() or getattr(candidate.lstat(), "st_file_attributes", 0) & 0x400:
                subdirs.remove(name)
                names.append(name)
        for name in sorted(names):
            path = folder / name
            relative = path.relative_to(root).as_posix()
            if name == ".git" or under(relative, excluded_paths):
                continue
            if not relative_path(relative):
                raise ValueError("Workspace contains a nonportable path; use an isolated, portable checkout.")
            # Directory junctions are intentionally rejected, never traversed.
            files[relative] = file_state(path)
            observed = path.lstat()
            observed_stats[path] = (observed.st_mtime_ns, observed.st_size, observed.st_mode)
    for path, signature in observed_stats.items():
        current = path.lstat()
        if signature != (current.st_mtime_ns, current.st_size, current.st_mode):
            raise ValueError("Workspace changed during inventory; stop concurrent writers.")
    head: str | None = None
    dirty_paths: list[str] = []
    try:
        base = subprocess.run(["git", "-C", str(root), "rev-parse", "--show-toplevel"], capture_output=True)
        if base.returncode == 0 and Path(os.fsdecode(base.stdout).strip()).resolve() == root:
            commit = subprocess.run(["git", "-C", str(root), "rev-parse", "--verify", "HEAD"], capture_output=True)
            if commit.returncode == 0:
                head = commit.stdout.decode("ascii").strip()
            status = subprocess.run(["git", "-C", str(root), "status", "--porcelain=v1", "-z", "--untracked-files=all"], capture_output=True, check=True)
            entries = status.stdout.split(b"\0")
            index = 0
            while index < len(entries):
                entry = entries[index]
                index += 1
                if not entry:
                    continue
                dirty_paths.append(os.fsdecode(entry[3:]).replace("\\", "/"))
                if b"R" in entry[:2] or b"C" in entry[:2]:
                    dirty_paths.append(os.fsdecode(entries[index]).replace("\\", "/"))
                    index += 1
    except FileNotFoundError:
        pass  # A non-Git workspace still has content hashes.
    result = {"files": files, "excluded_paths": excluded_paths, "git_head": head,
              "dirty_paths": sorted(set(dirty_paths))}
    result["digest"] = digest(result)
    return result


def snapshot_errors(value: Any, label: str) -> list[str]:
    if not isinstance(value, dict):
        return [f"{label} must be a snapshot object"]
    errors: list[str] = []
    files = value.get("files")
    if not isinstance(files, dict):
        errors.append(f"{label}.files must be an object")
    else:
        for path, item in files.items():
            if not relative_path(path) or not isinstance(item, dict):
                errors.append(f"{label}.files has an invalid entry")
                continue
            if not isinstance(item.get("digest"), str) or not re.fullmatch(r"sha256:[0-9a-f]{64}", item["digest"]):
                errors.append(f"{label}.files has an invalid digest")
            if item.get("kind") not in ("file", "symlink") or type(item.get("executable")) is not bool:
                errors.append(f"{label}.files has invalid metadata")
    exclusions = value.get("excluded_paths")
    if not isinstance(exclusions, list) or any(not relative_path(path) for path in exclusions):
        errors.append(f"{label}.excluded_paths must be relative paths")
    elif isinstance(files, dict) and any(under(path, exclusions) for path in files):
        errors.append(f"{label}.files includes an excluded path")
    if not isinstance(value.get("dirty_paths"), list) or any(not isinstance(p, str) for p in value.get("dirty_paths", [])):
        errors.append(f"{label}.dirty_paths must be strings")
    head = value.get("git_head")
    if head is not None and (not isinstance(head, str) or not re.fullmatch(r"[0-9a-f]{40,64}", head)):
        errors.append(f"{label}.git_head must be a commit hash or null")
    if value.get("digest") != digest({key: item for key, item in value.items() if key != "digest"}):
        errors.append(f"{label}.digest mismatch")
    return errors


def check_input_freshness(capsule: dict, current: dict) -> list[str]:
    watched = capsule["input_paths"] + capsule["owned_paths"]
    changes = changed_paths(capsule["workspace_base"]["files"], current["files"])
    return [f"input changed since assignment: {path}" for path in changes if under(path, watched)]
