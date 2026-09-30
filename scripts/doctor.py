"""Read-only installation checks; native discovery and model access remain unverified."""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tomllib
from pathlib import Path


def configured_role_settings(config: dict, role: dict) -> dict:
    """Resolve file defaults only; live spawn/runtime overrides remain unobserved."""
    defaults = config.get("agents", {})
    if not isinstance(defaults, dict):
        defaults = {}
    model = defaults.get("default_subagent_model", config.get("model"))
    model_source = "agents_default" if "default_subagent_model" in defaults else "parent_config"
    if "default_subagent_reasoning_effort" in defaults:
        effort, effort_source = defaults["default_subagent_reasoning_effort"], "agents_default"
    elif "default_subagent_model" in defaults:
        effort, effort_source = None, "model_default_not_resolved"
    else:
        effort, effort_source = config.get("model_reasoning_effort"), "parent_config"
    if "model" in role:
        model, model_source = role["model"], "role_file"
    if "model_reasoning_effort" in role:
        effort, effort_source = role["model_reasoning_effort"], "role_file"
    return {"model": model, "model_source": model_source, "reasoning_effort": effort,
            "effort_source": effort_source, "live_effective_settings": "not_verified"}


def diagnose(codex_home: Path, user_home: Path) -> dict:
    issues = []
    parsed_config = {}
    config = codex_home / "config.toml"
    config_result = {"exists": config.is_file(), "toml_valid": None}
    if config.is_file():
        try:
            parsed_config = tomllib.loads(config.read_text(encoding="utf-8"))
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
        value = {}
        if file.is_file():
            try:
                value = tomllib.loads(file.read_text(encoding="utf-8"))
                valid = (value.get("name") == name and all(isinstance(value.get(field), str) and value[field].strip()
                         for field in ("description", "developer_instructions")))
                valid = bool(valid) and all(key not in value or isinstance(value[key], str) and bool(value[key].strip())
                                           for key in ("model", "model_reasoning_effort"))
            except (OSError, ValueError):
                pass
        roles.append({"name": name, "present": file.is_file(), "toml_and_required_fields_valid": valid,
                      "configured_settings": configured_role_settings(parsed_config, value) if valid else None})
        if not valid:
            issues.append(f"Role missing or invalid: {name}")
    return {"python_supported": sys.version_info >= (3, 11), "config": config_result,
            "skill_candidates": candidates, "roles": roles, "issues": issues,
            "runtime": {"skill_discovered": "not_verified", "roles_discovered": "not_verified",
                        "model_access": "not_verified", "permissions_and_concurrency": "not_verified"},
            "next_step": "Inspect actual loaded Skills, role settings and tools. Role-file models override defaults; reported settings do not include live spawn values or session overrides."}


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
