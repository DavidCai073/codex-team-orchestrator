from __future__ import annotations

import json
import re
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_FILES = [
    ".codex-plugin/plugin.json", "skills/orchestrator/SKILL.md", "skills/orchestrator/agents/openai.yaml",
    "skills/orchestrator/references/role-contracts.md", "skills/orchestrator/references/sol-multi-agent.md",
    "skills/orchestrator/scripts/validate_context_contract.py", "skills/orchestrator/scripts/workspace_state.py",
    "skills/orchestrator/scripts/context_tool.py", "agents/luna_worker.toml", "agents/terra_scout.toml",
    "presets/config.example.toml", "presets/models.astra.toml", "presets/AGENTS.example.md",
    "scripts/install.py", "scripts/uninstall.py", "scripts/kitlib.py", "scripts/config_merge.py",
    "scripts/doctor.py", "README.md", "AGENTS.md", "LICENSE",
    "docs/behavior-evaluation.md", "docs/full-handoff-example.md",
]


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def validate_structure() -> None:
    for relative in REQUIRED_FILES:
        check((ROOT / relative).is_file(), f"Missing required file: {relative}")
    manifest = json.loads((ROOT / ".codex-plugin/plugin.json").read_text(encoding="utf-8"))
    check(manifest.get("name") == "codex-team-orchestrator", "Unexpected plugin name")
    check(manifest.get("skills") == "./skills/", "Plugin must expose ./skills/")
    check(manifest.get("license") == "MIT", "Plugin license must be MIT")
    sys.path.insert(0, str(ROOT / "scripts"))
    from install import VERSION
    check(manifest.get("version") == VERSION, "Installer and plugin versions disagree")

    skill = (ROOT / "skills/orchestrator/SKILL.md").read_text(encoding="utf-8")
    check(re.match(r"\A---\nname: orchestrator\ndescription: .+\n---\n", skill) is not None,
          "Skill frontmatter is invalid")
    ui = (ROOT / "skills/orchestrator/agents/openai.yaml").read_text(encoding="utf-8")
    check("$orchestrator" in ui, "Skill UI must reference its invocation name")
    check(re.search(r"allow_implicit_invocation:\s*true", ui) is not None, "Implicit routing is disabled")
    config = tomllib.loads((ROOT / "presets/config.example.toml").read_text(encoding="utf-8"))
    check(config["approval_policy"] == "on-request" and config["sandbox_mode"] == "workspace-write",
          "Safety preset defaults changed")
    check("model" not in config and "default_subagent_model" not in config["agents"],
          "General routing preset must not silently select models")
    check(type(config["agents"]["max_concurrent_threads_per_session"]) is int
          and config["agents"]["max_concurrent_threads_per_session"] > 0, "Invalid concurrency preset")
    tomllib.loads((ROOT / "presets/models.astra.toml").read_text(encoding="utf-8"))
    for role, sandbox in (("terra_scout", "read-only"), ("luna_worker", "workspace-write")):
        profile = tomllib.loads((ROOT / "agents" / f"{role}.toml").read_text(encoding="utf-8"))
        check(profile.get("name") == role and profile.get("sandbox_mode") == sandbox, f"Invalid role: {role}")
        check(isinstance(profile.get("model"), str) and bool(profile["model"]), f"Missing model: {role}")
        check(isinstance(profile.get("developer_instructions"), str), f"Missing instructions: {role}")
        check("validate_context_contract.py" in profile["developer_instructions"],
              f"{role} must reference the authoritative schema instead of duplicating it")

    # Verify real relative references; don't freeze exact prose or model effort choices.
    for file in (ROOT / "skills/orchestrator").rglob("*.md"):
        for target in re.findall(r"\]\(([^)]+)\)", file.read_text(encoding="utf-8")):
            if "://" not in target and not target.startswith("#"):
                check((file.parent / target.split("#")[0]).exists(), f"Broken reference in {file.name}: {target}")
    print("PASS structure, metadata, model separation and references", flush=True)


def validate_content() -> None:
    forbidden = {
        "unfinished marker": re.compile(r"\bTO" + r"DO\b|\[TO" + r"DO:", re.IGNORECASE),
        "Windows user path": re.compile(r"[A-Za-z]:[\\/]Users[\\/]", re.IGNORECASE),
        "macOS user path": re.compile(r"/Us" + r"ers/[^/\s]+/"),
        "Linux user path": re.compile(r"/ho" + r"me/[^/\s]+/"),
        "OpenAI-style secret": re.compile(r"\bsk-[A-Za-z0-9_-]{16,}"),
        "GitHub token": re.compile(r"\bgh[opsu]_[A-Za-z0-9]{16,}"),
        "private key": re.compile(r"BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY"),
    }
    failures = []
    for file in sorted(item for item in ROOT.rglob("*") if item.is_file() and ".git" not in item.parts):
        if file.suffix == ".pyc" or "__pycache__" in file.parts:
            failures.append(f"Compiled cache: {file.relative_to(ROOT)}")
        try:
            content = file.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for label, pattern in forbidden.items():
            if pattern.search(content):
                failures.append(f"{label}: {file.relative_to(ROOT)}")
    check(not failures, "Content scan failed:\n" + "\n".join(failures))
    print("PASS privacy, placeholders and compiled-cache scan", flush=True)


def main() -> int:
    validate_structure()
    result = subprocess.run([sys.executable, "-B", "-m", "unittest", "discover", "-s", "tests", "-v"],
                            cwd=ROOT, check=False)
    check(result.returncode == 0, "Regression suite failed")
    validate_content()
    print("All deterministic validations passed. Native client discovery and live-model benchmarks are not verified.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
