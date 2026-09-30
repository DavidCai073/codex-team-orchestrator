from __future__ import annotations

import json
import hashlib
import contextlib
import io
import subprocess
import sys
import tempfile
import tomllib
import unittest
from unittest import mock
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from doctor import diagnose, configured_role_settings


class InstallOptionsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="cto-install-")
        self.addCleanup(self.temp.cleanup)
        self.user = Path(self.temp.name) / "user"
        self.codex = Path(self.temp.name) / "codex"
        self.codex.mkdir()
        self.user.mkdir()
        self.original = 'model="keep-model"\nmodel_reasoning_effort="high"\n[agents]\ncustom_flag="keep"\n[[skills.config]]\npath="example"\nenabled=false\n'
        (self.codex / "config.toml").write_text(self.original, encoding="utf-8")
        self.original_agents = "# Existing personal instructions\n\nPreserve this user-owned rule.\n"
        (self.codex / "AGENTS.md").write_text(self.original_agents, encoding="utf-8")
        self.common = ["--codex-home", str(self.codex), "--user-home", str(self.user)]

    def run_script(self, name, *options):
        return subprocess.run([sys.executable, "-B", str(ROOT / "scripts" / name), *self.common, *options],
                              capture_output=True, text=True, cwd=ROOT)

    def test_preset_preserves_models_and_disabled_skill_then_restores(self):
        installed = self.run_script("install.py", "--apply-preset")
        self.assertEqual(installed.returncode, 0, installed.stderr)
        config = tomllib.loads((self.codex / "config.toml").read_text(encoding="utf-8"))
        self.assertEqual(config["model"], "keep-model")
        self.assertFalse(config["skills"]["config"][0]["enabled"])
        self.assertTrue(config["agents"]["enabled"])
        self.assertIn("Preserve this user-owned rule.", (self.codex / "AGENTS.md").read_text(encoding="utf-8"))
        self.assertFalse(diagnose(self.codex, self.user)["issues"])
        self.assertEqual(self.run_script("uninstall.py").returncode, 0)
        self.assertEqual((self.codex / "config.toml").read_text(encoding="utf-8"), self.original)
        self.assertEqual((self.codex / "AGENTS.md").read_text(encoding="utf-8"), self.original_agents)

    def test_explicit_astra_preset_and_mode_conflict(self):
        result = self.run_script("install.py", "--apply-preset", "--model-preset", "astra")
        self.assertEqual(result.returncode, 0, result.stderr)
        config = tomllib.loads((self.codex / "config.toml").read_text(encoding="utf-8"))
        self.assertEqual(config["model"], "gpt-6-astra")
        self.assertEqual(config["model_reasoning_effort"], "high")
        self.assertEqual(self.run_script("install.py", "--apply-preset", "--model-preset", "astra").returncode, 0)
        self.assertEqual(self.run_script("install.py", "--apply-preset", "--force").returncode, 2)

    def test_unsupported_merge_does_not_partially_install(self):
        before = 'agents = {enabled=false}\n'
        (self.codex / "config.toml").write_text(before, encoding="utf-8")
        result = self.run_script("install.py", "--apply-preset")
        self.assertEqual(result.returncode, 2)
        self.assertEqual((self.codex / "config.toml").read_text(encoding="utf-8"), before)
        self.assertFalse((self.codex / "agents").exists())
        self.assertFalse((self.codex / "skills").exists())
        self.assertFalse((self.codex / ".codex-team-orchestrator").exists())

    def test_selected_alternate_skill_location_installs_and_uninstalls(self):
        result = self.run_script("install.py", "--skill-location", "agents")
        self.assertEqual(result.returncode, 0, result.stderr)
        target = self.user / ".agents" / "skills" / "orchestrator"
        self.assertTrue((target / "SKILL.md").is_file())
        self.assertFalse((self.codex / "skills").exists())
        self.assertEqual(self.run_script("install.py", "--skill-location", "agents").returncode, 0)
        self.assertEqual(self.run_script("uninstall.py").returncode, 0)
        self.assertFalse(target.exists())

    def test_dry_run_never_creates_any_files(self):
        before = sorted(path.relative_to(self.temp.name) for path in Path(self.temp.name).rglob("*"))
        result = self.run_script("install.py", "--apply-preset", "--dry-run")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(sorted(path.relative_to(self.temp.name) for path in Path(self.temp.name).rglob("*")), before)

    def test_modified_config_blocks_uninstall_and_keeps_backup(self):
        self.assertEqual(self.run_script("install.py", "--apply-preset").returncode, 0)
        config = self.codex / "config.toml"
        config.write_text(config.read_text(encoding="utf-8") + '\n[custom]\nkeep=true\n', encoding="utf-8")
        changed = config.read_bytes()
        self.assertEqual(self.run_script("uninstall.py").returncode, 2)
        self.assertEqual(config.read_bytes(), changed)
        self.assertTrue((self.codex / ".codex-team-orchestrator" / "install-state.json").is_file())

    def test_doctor_distinguishes_files_from_runtime(self):
        self.assertEqual(self.run_script("install.py").returncode, 0)
        report = diagnose(self.codex, self.user)
        self.assertEqual(report["issues"], [])
        self.assertEqual(set(report["runtime"].values()), {"not_verified"})
        duplicate = self.user / ".agents" / "skills" / "orchestrator"
        duplicate.mkdir(parents=True)
        (duplicate / "SKILL.md").write_text("duplicate", encoding="utf-8")
        self.assertTrue(diagnose(self.codex, self.user)["issues"])

    def test_invalid_config_diagnostic_does_not_echo_sensitive_contents(self):
        (self.codex / "config.toml").write_text("secret=private-invalid-data", encoding="utf-8")
        report = diagnose(self.codex, self.user)
        self.assertFalse(report["config"]["toml_valid"])
        self.assertNotIn("private-invalid-data", json.dumps(report))

    def test_legacy_install_manifest_restores_alternate_location(self):
        target = self.user / ".agents" / "skills" / "orchestrator" / "SKILL.md"
        target.parent.mkdir(parents=True)
        target.write_text("old managed skill", encoding="utf-8")
        state = self.codex / ".codex-team-orchestrator"
        state.mkdir()
        (state / "install-state.json").write_text(json.dumps({"schema_version": 1, "version": "0.1.1", "files": [
            {"path": str(target.resolve()), "kind": "skill", "created": True,
             "installed_sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
             "backup_path": None, "original_sha256": None}]}), encoding="utf-8")
        result = self.run_script("uninstall.py")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(target.exists())

    def test_forced_replacement_is_backed_up_and_restored(self):
        target = self.codex / "agents" / "luna_worker.toml"
        target.parent.mkdir()
        original = b'name = "user-custom-role"\n'
        target.write_bytes(original)
        self.assertEqual(self.run_script("install.py").returncode, 2)
        self.assertEqual(target.read_bytes(), original)
        self.assertEqual(self.run_script("install.py", "--force").returncode, 0)
        self.assertEqual(self.run_script("uninstall.py").returncode, 0)
        self.assertEqual(target.read_bytes(), original)

    def test_write_failure_rolls_back_successful_writes(self):
        import install
        real_write = install.atomic_write
        failed = False
        def fail_once(path, data):
            nonlocal failed
            if path == self.codex / "config.toml" and not failed:
                failed = True
                raise OSError("injected write failure")
            real_write(path, data)
        with mock.patch.object(sys, "argv", ["install.py", *self.common, "--apply-preset"]), \
             mock.patch.object(install, "atomic_write", side_effect=fail_once), \
             contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(OSError, "injected write failure"):
                install.main()
        self.assertEqual((self.codex / "config.toml").read_text(encoding="utf-8"), self.original)
        self.assertEqual((self.codex / "AGENTS.md").read_text(encoding="utf-8"), self.original_agents)
        self.assertFalse((self.codex / "agents" / "luna_worker.toml").exists())
        self.assertFalse((self.codex / "skills" / "orchestrator" / "SKILL.md").exists())
        self.assertFalse((self.codex / ".codex-team-orchestrator" / "install-state.json").exists())

    def test_sol_preset_applies_to_root_and_both_inheriting_roles(self):
        result = self.run_script("install.py", "--apply-preset", "--model-preset", "sol")
        self.assertEqual(result.returncode, 0, result.stderr)
        config = tomllib.loads((self.codex / "config.toml").read_text(encoding="utf-8"))
        self.assertEqual(config["model"], "gpt-6.1-sol")
        self.assertEqual(config["model_reasoning_effort"], "max")
        for role in diagnose(self.codex, self.user)["roles"]:
            settings = role["configured_settings"]
            self.assertEqual(settings["model"], "gpt-6-luna")
            self.assertEqual(settings["model_source"], "agents_default")
            self.assertEqual(settings["reasoning_effort"], "max")
        self.assertEqual(self.run_script("install.py", "--apply-preset", "--model-preset", "sol").returncode, 0)

    def test_ordinary_replacement_preserves_role_overrides(self):
        role_path = self.codex / "agents" / "terra_scout.toml"
        role_path.parent.mkdir()
        original = 'name="terra_scout"\nmodel="custom-scout"\nmodel_reasoning_effort="high"\n'
        role_path.write_text(original, encoding="utf-8")
        self.assertEqual(self.run_script("install.py", "--force", "--apply-preset").returncode, 0)
        role = tomllib.loads(role_path.read_text(encoding="utf-8"))
        self.assertEqual(role["model"], "custom-scout")
        self.assertEqual(role["model_reasoning_effort"], "high")
        self.assertEqual(self.run_script("install.py", "--force", "--apply-preset").returncode, 0)
        self.assertEqual(self.run_script("uninstall.py").returncode, 0)
        self.assertEqual(role_path.read_text(encoding="utf-8"), original)

    def test_explicit_preset_removes_old_managed_role_override(self):
        role_path = self.codex / "agents" / "terra_scout.toml"
        role_path.parent.mkdir()
        role_path.write_text('model="old-model"\nmodel_reasoning_effort="max"\n', encoding="utf-8")
        result = self.run_script("install.py", "--force", "--apply-preset", "--model-preset", "sol")
        self.assertEqual(result.returncode, 0, result.stderr)
        role = tomllib.loads(role_path.read_text(encoding="utf-8"))
        self.assertNotIn("model", role)
        self.assertNotIn("model_reasoning_effort", role)

    def test_doctor_explains_role_override_and_unresolved_effort(self):
        config = {"model": "root", "model_reasoning_effort": "ultra", "agents": {"default_subagent_model": "child"}}
        settings = configured_role_settings(config, {})
        self.assertEqual(settings["model"], "child")
        self.assertIsNone(settings["reasoning_effort"])
        settings = configured_role_settings(config, {"model": "override", "model_reasoning_effort": "high"})
        self.assertEqual(settings["model_source"], "role_file")
        self.assertEqual(settings["reasoning_effort"], "high")


if __name__ == "__main__":
    unittest.main()
