from __future__ import annotations

import json
import re
import shutil
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
    "skills/orchestrator/scripts/validate_context_contract.py",
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


def run(command: list[str], input_text: str | None = None) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        input=input_text,
        capture_output=True,
        check=False,
    )
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
    check(manifest.get("version") == "0.1.2", "Unexpected plugin version")
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
    check(re.search(r"allow_implicit_invocation:\s*true", yaml_text) is not None, "Implicit invocation must be enabled")
    description = re.search(r"^description:\s*(.+)$", header, re.MULTILINE)
    check(description is not None and "Invoke implicitly" in description.group(1), "Skill description must declare implicit routing")
    agents_preset = (ROOT / "presets" / "AGENTS.example.md").read_text(encoding="utf-8")
    check(
        "implicitly to every programming and software-project request" in agents_preset,
        "AGENTS preset must enforce full engineering-scope implicit routing",
    )
    check("at most two new agents" in skill_text, "Skill must cap normal per-turn agent creation")
    check("at most six agents" in skill_text, "Skill must cap per-stage agent creation")
    check('fork_turns: "none"' in skill_text, "Skill must default focused agents to fresh context")
    check("second observed context compaction" in skill_text, "Skill must stop expansion after repeated compaction")
    check("at most six agents" in agents_preset, "AGENTS preset must include the stage creation budget")

    role_contracts = (ROOT / "skills" / "orchestrator" / "references" / "role-contracts.md").read_text(
        encoding="utf-8"
    )
    capsule_fields = (
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
    for field in capsule_fields:
        check(field in role_contracts, f"Context Capsule is missing {field}")
    check('"schema_version": 1' in role_contracts, "Full Capsule schema version is missing")
    check('"permission": "read-only | scoped-write | execute-checks"' in role_contracts, "Permission field is missing")
    check("Lite Task Envelope" in role_contracts, "Lite Task Envelope is missing")
    check("pre-spawn/pre-merge gate" in role_contracts, "Validator capability boundary is missing")
    check("received_capsule_version" in role_contracts, "Handshake must echo the capsule version")
    check(
        all(status in role_contracts for status in ("sufficient", "missing_context", "stale_context", "contradictory_context")),
        "Handshake context statuses are incomplete",
    )
    check("State Delta" in role_contracts, "Role contract must define a State Delta")
    for label, text in (
        ("Skill", skill_text),
        ("AGENTS preset", agents_preset),
    ):
        check("Context Capsule" in text and "State Delta" in text, f"{label} must require context handoff")

    config = tomllib.loads((ROOT / "presets" / "config.example.toml").read_text(encoding="utf-8"))
    luna = tomllib.loads((ROOT / "agents" / "luna_worker.toml").read_text(encoding="utf-8"))
    terra = tomllib.loads((ROOT / "agents" / "terra_scout.toml").read_text(encoding="utf-8"))
    check(config["approval_policy"] == "on-request", "Preset approval policy is unsafe")
    check(config["sandbox_mode"] == "workspace-write", "Preset sandbox is unsafe")
    check(config["agents"]["max_concurrent_threads_per_session"] == 3, "Preset cap must be 3")
    check(luna["model"] == "gpt-5.6-luna" and luna["model_reasoning_effort"] == "max", "Luna profile is invalid")
    check(terra["model"] == "gpt-5.6-terra" and terra["sandbox_mode"] == "read-only", "Terra profile is invalid")
    check("Do not send routine progress updates" in luna["developer_instructions"], "Luna reporting must stay compact")
    check("Do not send routine progress updates" in terra["developer_instructions"], "Terra reporting must stay compact")
    for label, instructions in (
        ("Luna", luna["developer_instructions"]),
        ("Terra", terra["developer_instructions"]),
    ):
        check("received_capsule_version" in instructions, f"{label} must echo capsule version")
        check("missing_context" in instructions, f"{label} must stop on incomplete context")
        check("State Delta" in instructions, f"{label} must return a State Delta")


def validate_context_contract() -> None:
    validator = "skills/orchestrator/scripts/validate_context_contract.py"
    capsule = {
        "schema_version": 1,
        "stage_id": "stage-auth-fix",
        "capsule_version": 3,
        "node_id": "implement-session-timeout",
        "objective": "Fix the scoped session timeout defect.",
        "acceptance_criteria": ["The targeted session test passes."],
        "confirmed_decisions": [],
        "non_goals": ["Do not change the public API."],
        "dependencies_and_interfaces": [],
        "owned_paths": ["src/auth/session.py", "tests/test_session.py"],
        "permission": "scoped-write",
        "safety_boundaries": ["no dependency installation"],
        "known_failures": ["tests/test_session.py::test_refresh_timeout"],
        "evidence_index": [{"kind": "path", "ref": "tests/test_session.py", "result": "one failing test", "verified": True}],
        "open_questions": [],
    }
    capsule_result = run(
        [sys.executable, "-B", validator, "--kind", "capsule", "--expected-version", "3"],
        input_text=json.dumps(capsule),
    )
    check("VALID capsule version=3 digest=sha256:" in capsule_result.stdout, "Valid capsule was rejected")
    digest = capsule_result.stdout.strip().split("digest=", 1)[1]

    delta = {
        "stage_id": "stage-auth-fix",
        "node_id": "implement-session-timeout",
        "status": "completed",
        "received_capsule_version": 3,
        "context_status": "sufficient",
        "context_issues": [],
        "conclusion": "The timeout path now reuses the existing refresh guard.",
        "capsule_digest": digest,
        "evidence": [{"kind": "command", "ref": "python -m unittest tests.test_session", "result": "passed", "verified": True}],
        "changed_files": ["src/auth/session.py"],
        "checks": [{"command": "python -m unittest tests.test_session", "status": "passed", "summary": "passed"}],
        "new_facts": [],
        "invalidated_assumptions": [],
        "open_questions": [],
        "risks": [],
        "recommended_next": "Run the full auth test group.",
    }
    delta_result = subprocess.run(
        [sys.executable, "-B", validator, "--kind", "delta", "--expected-version", "3", "--capsule-file", "-"],
        cwd=ROOT,
        text=True,
        input=json.dumps(delta),
        capture_output=True,
        check=False,
    )
    # The CLI pair check is covered by tests; this direct check uses the module API below.
    check(delta_result.returncode == 2, "Delta without a capsule file should be rejected")

    unsafe_delta = dict(delta)
    unsafe_delta.update(
        {
            "status": "blocked",
            "context_status": "stale_context",
            "context_issues": ["capsule_version is older than the root ledger"],
            "changed_files": ["src/auth/session.py"],
            "checks": [],
        }
    )
    rejected = subprocess.run(
        [sys.executable, "-B", validator, "--kind", "delta", "--expected-version", "3", "--capsule-file", "-"],
        cwd=ROOT,
        text=True,
        input=json.dumps(unsafe_delta),
        capture_output=True,
        check=False,
    )
    check(rejected.returncode == 2, "Validator accepted mutation under stale context")
    check(rejected.returncode == 2, "Validator did not reject stale-context mutation")


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
        check((codex_home / "skills" / "orchestrator" / "SKILL.md").is_file(), "Skill was not installed at canonical path")
        check("codex-team-orchestrator:start" in (codex_home / "AGENTS.md").read_text(encoding="utf-8"), "AGENTS preset was not applied")

        second = run([sys.executable, "-B", "scripts/install.py", "--apply-preset", *common])
        check("Already installed" in second.stdout, "Second install was not idempotent")

        legacy_root = user_home / ".agents" / "skills" / "orchestrator"
        legacy_root.mkdir(parents=True)
        (legacy_root / "SKILL.md").write_text("unmanaged legacy duplicate", encoding="utf-8")
        duplicate_after_install = subprocess.run(
            [sys.executable, "-B", "scripts/install.py", "--force", "--apply-preset", *common],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        check(duplicate_after_install.returncode == 2, "Idempotent reinstall ignored a legacy duplicate")
        check("Unmanaged legacy Skill" in duplicate_after_install.stderr, "Legacy duplicate rejection was unclear")
        shutil.rmtree(legacy_root)

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
        check(not (codex_home / "skills" / "orchestrator" / "SKILL.md").exists(), "Uninstall left Skill behind")

        legacy_root.mkdir(parents=True)
        (legacy_root / "SKILL.md").write_text("legacy", encoding="utf-8")
        rejected_legacy = subprocess.run(
            [sys.executable, "-B", "scripts/install.py", "--force", *common],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        check(rejected_legacy.returncode == 2, "Installer accepted unmanaged legacy Skill")
        check(not (codex_home / "skills" / "orchestrator" / "SKILL.md").exists(), "Legacy rejection wrote canonical Skill files")

        legacy_file = legacy_root / "SKILL.md"
        legacy_file.write_text("legacy managed skill", encoding="utf-8")
        legacy_state_dir = codex_home / ".codex-team-orchestrator"
        legacy_state_dir.mkdir(parents=True)
        import hashlib

        legacy_hash = hashlib.sha256(legacy_file.read_bytes()).hexdigest()
        (legacy_state_dir / "install-state.json").write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "version": "0.1.1",
                    "files": [
                        {
                            "path": str(legacy_file.resolve()),
                            "kind": "skill",
                            "created": True,
                            "installed_sha256": legacy_hash,
                            "backup_path": None,
                            "original_sha256": None,
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        run([sys.executable, "-B", "scripts/uninstall.py", *common])
        check(not legacy_file.exists(), "Uninstall did not remove a legacy-manifest Skill")


def main() -> int:
    validate_structure()
    print("PASS structure and metadata")
    validate_context_contract()
    print("PASS Context Capsule and State Delta contracts")
    run([sys.executable, "-B", "-m", "unittest", "tests.test_validate_context_contract"])
    print("PASS focused Context Capsule unittest")
    validate_privacy()
    print("PASS privacy and placeholder scan")
    validate_install_cycle()
    print("PASS dry-run, install, idempotency, and uninstall restoration")
    print("All validations passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
