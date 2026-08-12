from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
REQUIRED_FILES = [
    ".codex-plugin/plugin.json",
    "skills/orchestrator/SKILL.md",
    "skills/orchestrator/agents/openai.yaml",
    "skills/orchestrator/references/role-contracts.md",
    "skills/orchestrator/references/sol-multi-agent.md",
    "agents/luna_worker.toml",
    "agents/terra_scout.toml",
    "presets/config.example.toml",
    "presets/AGENTS.example.md",
    "scripts/install.py",
    "scripts/uninstall.py",
    "scripts/kitlib.py",
    "README.md",
    "LICENSE",
]


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        raise AssertionError(
            f"Command failed ({result.returncode}): {' '.join(command)}\n{result.stdout}\n{result.stderr}"
        )
    return result


def validate_structure() -> None:
    for relative in REQUIRED_FILES:
        check((ROOT / relative).is_file(), f"Missing required file: {relative}")
    compiled_artifacts = sorted(
        path.relative_to(ROOT)
        for path in ROOT.rglob("*")
        if path.is_file() and (path.suffix.lower() == ".pyc" or "__pycache__" in path.parts)
    )
    check(
        not compiled_artifacts,
        "Remove compiled Python artifacts before packaging:\n"
        + "\n".join(str(path) for path in compiled_artifacts),
    )

    manifest = json.loads((ROOT / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))
    check(manifest.get("name") == "codex-team-orchestrator", "Unexpected plugin name")
    check(manifest.get("version") == "0.1.0", "Unexpected plugin version")
    check(manifest.get("skills") == "./skills/", "Plugin must expose ./skills/")
    check(manifest.get("license") == "MIT", "Plugin license must be MIT")

    skill_text = (ROOT / "skills" / "orchestrator" / "SKILL.md").read_text(encoding="utf-8")
    frontmatter = re.match(r"\A---\n(.*?)\n---\n", skill_text, re.DOTALL)
    check(frontmatter is not None, "Skill frontmatter is missing")
    header = frontmatter.group(1) if frontmatter else ""
    check(re.search(r"^name:\s*orchestrator\s*$", header, re.MULTILINE) is not None, "Skill name is invalid")
    check(re.search(r"^description:\s*.+$", header, re.MULTILINE) is not None, "Skill description is missing")

    yaml_text = (ROOT / "skills" / "orchestrator" / "agents" / "openai.yaml").read_text(encoding="utf-8")
    check("$orchestrator" in yaml_text, "openai.yaml default_prompt must mention $orchestrator")
    check(re.search(r"allow_implicit_invocation:\s*false", yaml_text) is not None, "Implicit invocation must be disabled")

    config = tomllib.loads((ROOT / "presets" / "config.example.toml").read_text(encoding="utf-8"))
    luna = tomllib.loads((ROOT / "agents" / "luna_worker.toml").read_text(encoding="utf-8"))
    terra = tomllib.loads((ROOT / "agents" / "terra_scout.toml").read_text(encoding="utf-8"))
    check(config["approval_policy"] == "on-request", "Preset approval policy is unsafe")
    check(config["sandbox_mode"] == "workspace-write", "Preset sandbox is unsafe")
    check(config["agents"]["max_concurrent_threads_per_session"] == 3, "Preset cap must be 3")
    check(luna["model"] == "gpt-5.6-luna" and luna["model_reasoning_effort"] == "max", "Luna profile is invalid")
    check(terra["model"] == "gpt-5.6-terra" and terra["sandbox_mode"] == "read-only", "Terra profile is invalid")


def validate_privacy() -> None:
    forbidden = {
        "unfinished marker": re.compile(r"\bTO" + r"DO\b|\[TO" + r"DO:", re.IGNORECASE),
        "Windows user path": re.compile(r"[A-Za-z]:\\Users\\", re.IGNORECASE),
        "macOS user path": re.compile(r"/Us" + r"ers/[^/\s]+/"),
        "Linux user path": re.compile(r"/ho" + r"me/[^/\s]+/"),
        "OpenAI-style secret": re.compile(r"\bsk-[A-Za-z0-9_-]{16,}"),
        "GitHub token": re.compile(r"\bgh[opsu]_[A-Za-z0-9]{16,}"),
        "private key": re.compile(r"BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY"),
    }
    failures: list[str] = []
    for path in sorted(item for item in ROOT.rglob("*") if item.is_file() and ".git" not in item.parts):
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for label, pattern in forbidden.items():
            if pattern.search(text):
                failures.append(f"{label}: {path.relative_to(ROOT)}")
    check(not failures, "Privacy/content scan failed:\n" + "\n".join(failures))


def validate_install_cycle() -> None:
    with tempfile.TemporaryDirectory(prefix="cto-validate-") as temporary:
        temp = Path(temporary)
        user_home = temp / "user"
        codex_home = temp / "codex"
        user_home.mkdir()
        codex_home.mkdir()
        original_config = (
            'service_tier = "priority"\n'
            'model = "existing-model"\n\n'
            '[agents]\n'
            'enabled = false\n'
            'custom_flag = "keep"\n\n'
            '[desktop]\n'
            'localeOverride = "zh-CN"\n'
        )
        original_agents = "# Existing instructions\n\n- Preserve this line.\n"
        (codex_home / "config.toml").write_text(original_config, encoding="utf-8")
        (codex_home / "AGENTS.md").write_text(original_agents, encoding="utf-8")

        common = ["--codex-home", str(codex_home), "--user-home", str(user_home)]
        dry = run([sys.executable, "-B", "scripts/install.py", "--dry-run", "--apply-preset", *common])
        check("Dry run complete" in dry.stdout, "Installer dry run did not complete")
        check(not (user_home / ".agents").exists(), "Dry run created user files")

        run([sys.executable, "-B", "scripts/install.py", "--apply-preset", *common])
        installed = tomllib.loads((codex_home / "config.toml").read_text(encoding="utf-8"))
        check(installed["service_tier"] == "priority", "Config merge lost an unrelated top-level key")
        check(installed["model"] == "gpt-5.6-sol", "Config merge did not apply Sol")
        check(installed["agents"]["custom_flag"] == "keep", "Config merge lost an unrelated agents key")
        check(installed["desktop"]["localeOverride"] == "zh-CN", "Config merge lost an unrelated table")
        check((codex_home / "agents" / "luna_worker.toml").is_file(), "Luna agent was not installed")
        check((user_home / ".agents" / "skills" / "orchestrator" / "SKILL.md").is_file(), "Skill was not installed")
        check("codex-team-orchestrator:start" in (codex_home / "AGENTS.md").read_text(encoding="utf-8"), "AGENTS preset was not applied")

        second = run([sys.executable, "-B", "scripts/install.py", "--apply-preset", *common])
        check("Already installed" in second.stdout, "Second install was not idempotent")
        changed_mode = subprocess.run(
            [sys.executable, "-B", "scripts/install.py", "--force", *common],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        check(changed_mode.returncode == 2, "Installer overwrote an existing backup chain")
        check("Uninstall it first" in changed_mode.stderr, "Installer did not explain safe reinstall procedure")
        run([sys.executable, "-B", "scripts/uninstall.py", *common])
        check((codex_home / "config.toml").read_text(encoding="utf-8") == original_config, "Uninstall did not restore config.toml")
        check((codex_home / "AGENTS.md").read_text(encoding="utf-8") == original_agents, "Uninstall did not restore AGENTS.md")
        check(not (codex_home / "agents" / "luna_worker.toml").exists(), "Uninstall left Luna agent behind")
        check(not (user_home / ".agents" / "skills" / "orchestrator" / "SKILL.md").exists(), "Uninstall left Skill behind")


def main() -> int:
    validate_structure()
    print("PASS structure and metadata")
    validate_privacy()
    print("PASS privacy and placeholder scan")
    validate_install_cycle()
    print("PASS dry-run, install, idempotency, and uninstall restoration")
    print("All validations passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
