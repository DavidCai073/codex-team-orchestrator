"""Read-only installation checks; native discovery and model access remain unverified."""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tomllib
from pathlib import Path


def diagnose(codex_home: Path, user_home: Path) -> dict:
    issues = []
    config = codex_home / "config.toml"
    config_result = {"exists": config.is_file(), "toml_valid": None}
    if config.is_file():
        try:
            tomllib.loads(config.read_text(encoding="utf-8"))
            config_result["toml_valid"] = True
        except (OSError, ValueError):
            config_result["toml_valid"] = False
            issues.append("config.toml cannot be parsed; contents were not included in this report")
    candidates = []
    for location, root in (("codex", codex_home / "skills"), ("agents", user_home / ".agents" / "skills")):
        skill = root / "orchestrator" / "SKILL.md"
        valid = None
        if skill.is_file():
            try:
                source = skill.read_text(encoding="utf-8")
                valid = bool(re.match(r"\A---\nname: orchestrator\ndescription: .+\n---\n", source))
            except (OSError, ValueError):
                valid = False
        candidates.append({"location": location, "present": skill.is_file(), "metadata_valid": valid})
    found = [item for item in candidates if item["present"]]
    if len(found) != 1:
        issues.append("Expected exactly one Skill location; missing or duplicate installations need review")
    if any(item["metadata_valid"] is False for item in found):
        issues.append("Skill frontmatter is invalid")
    roles = []
    for name in ("terra_scout", "luna_worker"):
        file = codex_home / "agents" / (name + ".toml")
        valid = False
        if file.is_file():
            try:
                value = tomllib.loads(file.read_text(encoding="utf-8"))
                valid = value.get("name") == name and isinstance(value.get("developer_instructions"), str)
            except (OSError, ValueError):
                pass
        roles.append({"name": name, "present": file.is_file(), "toml_and_required_fields_valid": valid})
        if not valid:
            issues.append(f"Role missing or invalid: {name}")
    return {"python_supported": sys.version_info >= (3, 11), "config": config_result,
            "skill_candidates": candidates, "roles": roles, "issues": issues,
            "runtime": {"skill_discovered": "not_verified", "roles_discovered": "not_verified",
                        "model_access": "not_verified", "permissions_and_concurrency": "not_verified"},
            "next_step": "Restart the target client and inspect its actual loaded Skills, roles and available tools. File presence is not runtime discovery."}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--codex-home", type=Path)
    parser.add_argument("--user-home", type=Path)
    args = parser.parse_args()
    user_home = (args.user_home or Path.home()).expanduser().resolve()
    codex_home = (args.codex_home or Path(os.environ.get("CODEX_HOME", str(user_home / ".codex")))).expanduser().resolve()
    report = diagnose(codex_home, user_home)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 2 if report["issues"] or not report["python_supported"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
