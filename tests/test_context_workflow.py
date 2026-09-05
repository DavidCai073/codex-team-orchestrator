from __future__ import annotations

import copy
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "skills" / "orchestrator" / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))
import context_tool as workflow
from validate_context_contract import validate_capsule, validate_delta
from workspace_state import check_input_freshness, snapshot


class ContextWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="cto-contract-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "workspace"
        self.records = Path(self.temp.name) / "records"
        (self.root / "src").mkdir(parents=True)
        (self.root / "src" / "value.py").write_text("value = 1\n", encoding="utf-8")
        (self.root / "interface.txt").write_text("stable\n", encoding="utf-8")
        self.spec = {"stage_id": "stage-test", "objective": "Change value and verify it.",
                     "permission": "scoped-write", "owned_paths": ["src/value.py"],
                     "input_paths": ["interface.txt"], "safety_boundaries": ["Only local owned files"],
                     "acceptance_criteria": [{"id": "A-1", "description": "Value is two.",
                                              "verification": "command", "expected_exit_code": 0}]}
        self.cap = workflow.make_capsule(self.spec, self.root)

    def change_and_check(self):
        (self.root / "src" / "value.py").write_text("value = 2\n", encoding="utf-8")
        return workflow.run_check(self.cap, self.root, self.records,
            [sys.executable, "-B", "-c", "from src.value import value; assert value == 2; print('verified')"])

    def report(self, check):
        return {"execution_status": "completed", "conclusion": "Value changed and checked.",
                "changed_files": ["src/value.py"], "check_records": [check["record"]],
                "evidence": [{"id": "E-1", "kind": "command", "ref": check["id"],
                              "result": "Observed process result", "verified": True}]}

    def review(self):
        return {"acceptance_status": "accepted", "criteria": [
            {"criterion_id": "A-1", "decision": "met", "reason": "Command proves final value.", "evidence_ids": ["E-1"]}]}

    def test_complete_workflow_records_real_exit_and_output(self):
        check = self.change_and_check()
        delta = workflow.make_delta(self.report(check), self.cap, self.root, self.records)
        accepted = workflow.accept(self.review(), self.cap, delta, self.root, self.records)
        self.assertEqual(accepted["acceptance_status"], "accepted")
        self.assertEqual(check["exit_code"], 0)
        self.assertIn(b"verified", (self.records / (check["id"] + ".stdout")).read_bytes())
        self.assertEqual(set(delta), set(workflow.DELTA_FIELDS))
        self.assertEqual(set(self.cap), set(workflow.CAPSULE_FIELDS))

    def test_input_change_is_detected_before_execution(self):
        (self.root / "interface.txt").write_text("changed\n", encoding="utf-8")
        self.assertTrue(check_input_freshness(self.cap, snapshot(self.root)))
        with self.assertRaisesRegex(ValueError, "outside ownership"):
            self.change_and_check()

    def test_independent_change_does_not_make_ready_inputs_stale(self):
        (self.root / "independent.txt").write_text("unrelated", encoding="utf-8")
        self.assertEqual(check_input_freshness(self.cap, snapshot(self.root)), [])
        # Automatic receipt acceptance is stricter: unexplained concurrent writes require reconciliation.
        with self.assertRaises(ValueError):
            self.change_and_check()

    def test_unreported_or_out_of_scope_changes_are_rejected(self):
        check = self.change_and_check()
        report = self.report(check)
        report["changed_files"] = []
        with self.assertRaisesRegex(ValueError, "actual workspace changes"):
            workflow.make_delta(report, self.cap, self.root, self.records)
        (self.root / "outside.txt").write_text("unexpected", encoding="utf-8")
        report["changed_files"] = ["src/value.py", "outside.txt"]
        with self.assertRaisesRegex(ValueError, "outside owned_paths"):
            workflow.make_delta(report, self.cap, self.root, self.records)

    def test_later_code_edit_invalidates_accepted_test_evidence(self):
        check = self.change_and_check()
        (self.root / "src" / "value.py").write_text("value = 3\n", encoding="utf-8")
        delta = workflow.make_delta(self.report(check), self.cap, self.root, self.records)
        with self.assertRaisesRegex(ValueError, "final code state"):
            workflow.accept(self.review(), self.cap, delta, self.root, self.records)

    def test_code_changed_after_worker_return_is_rejected(self):
        check = self.change_and_check()
        delta = workflow.make_delta(self.report(check), self.cap, self.root, self.records)
        (self.root / "src" / "value.py").write_text("value = 4\n", encoding="utf-8")
        self.assertTrue(validate_delta(delta, capsule=self.cap, workspace_root=self.root))

    def test_tampered_log_cannot_be_accepted(self):
        check = self.change_and_check()
        delta = workflow.make_delta(self.report(check), self.cap, self.root, self.records)
        (self.records / (check["id"] + ".stdout")).write_text("changed", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "output digest mismatch"):
            workflow.accept(self.review(), self.cap, delta, self.root, self.records)

    def test_tampered_record_cannot_be_accepted(self):
        check = self.change_and_check()
        delta = workflow.make_delta(self.report(check), self.cap, self.root, self.records)
        receipt = json.loads((self.records / check["record"]).read_text(encoding="utf-8"))
        receipt["check"]["exit_code"] = 7
        (self.records / check["record"]).write_text(json.dumps(receipt), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "receipt does not match"):
            workflow.accept(self.review(), self.cap, delta, self.root, self.records)

    def test_old_failed_diagnostic_evidence_can_be_retained(self):
        failed = workflow.run_check(self.cap, self.root, self.records,
            [sys.executable, "-B", "-c", "raise SystemExit(1)"])
        passed = self.change_and_check()
        report = self.report(passed)
        report["check_records"].insert(0, failed["record"])
        delta = workflow.make_delta(report, self.cap, self.root, self.records)
        self.assertEqual(workflow.accept(self.review(), self.cap, delta, self.root, self.records)["acceptance_status"], "accepted")

    def test_exclusions_cannot_hide_owned_or_input_files(self):
        for exclusion in ("src", "interface.txt", "src/value.py"):
            with self.assertRaises(ValueError):
                workflow.make_capsule(self.spec, self.root, [exclusion])

    def test_contracts_are_sidecars_and_never_silently_overwritten(self):
        with self.assertRaises(ValueError):
            workflow.write_new(self.root / "capsule.json", self.cap, self.root)
        target = self.records / "capsule.json"
        workflow.write_new(target, self.cap, self.root)
        with self.assertRaises(FileExistsError):
            workflow.write_new(target, self.cap, self.root)

    def test_read_only_cannot_run_commands(self):
        self.spec["permission"] = "read-only"
        cap = workflow.make_capsule(self.spec, self.root)
        with self.assertRaisesRegex(ValueError, "do not authorize"):
            workflow.run_check(cap, self.root, self.records, [sys.executable, "--version"])

    def test_symlink_watched_path_is_rejected(self):
        link = self.root / "src" / "linked.py"
        try:
            link.symlink_to(self.root / "src" / "value.py")
        except OSError:
            self.skipTest("OS does not grant symlink creation")
        self.spec["owned_paths"] = ["src"]
        with self.assertRaisesRegex(ValueError, "symlinks"):
            workflow.make_capsule(self.spec, self.root)

    def test_snapshot_preserves_dirty_git_baseline(self):
        subprocess.run(["git", "init", "--quiet", str(self.root)], check=True, capture_output=True)
        subprocess.run(["git", "-C", str(self.root), "add", "src/value.py"], check=True, capture_output=True)
        state = snapshot(self.root)
        self.assertIn("src/value.py", state["dirty_paths"])
        self.assertIn("interface.txt", state["files"])
        self.assertFalse(any(path.startswith(".git/") for path in state["files"]))

    def test_cli_schema_prepare_ready_and_missing_fields(self):
        script = str(SCRIPT_DIR / "context_tool.py")
        result = subprocess.run([sys.executable, "-B", script, "schema"], text=True, capture_output=True, check=True)
        self.assertEqual(json.loads(result.stdout)["schema_version"], 2)
        spec_file = Path(self.temp.name) / "spec.json"
        spec_file.write_text(json.dumps(self.spec), encoding="utf-8")
        cap_file = self.records / "capsule.json"
        subprocess.run([sys.executable, "-B", script, "prepare", "--workspace-root", str(self.root),
            "--spec", str(spec_file), "--out", str(cap_file)], check=True, capture_output=True)
        result = subprocess.run([sys.executable, "-B", script, "ready", "--workspace-root", str(self.root),
            "--capsule", str(cap_file)], check=True, capture_output=True, text=True)
        self.assertEqual(json.loads(result.stdout)["context_status"], "sufficient")
        spec_file.write_text("{}", encoding="utf-8")
        result = subprocess.run([sys.executable, "-B", script, "prepare", "--workspace-root", str(self.root),
            "--spec", str(spec_file), "--out", str(self.records / "invalid.json")], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn("missing required field", result.stderr)

    def test_documented_example_matches_generated_protocol(self):
        content = (ROOT / "docs" / "full-handoff-example.md").read_text(encoding="utf-8")
        spec, report, review = [json.loads(block) for block in re.findall(r"```json\n(.*?)\n```", content, re.S)]
        (self.root / "README.md").write_text((ROOT / "README.md").read_text(encoding="utf-8"), encoding="utf-8")
        cap = workflow.make_capsule(spec, self.root)
        delta = workflow.make_delta(report, cap, self.root, self.records)
        self.assertEqual(workflow.accept(review, cap, delta, self.root, self.records)["acceptance_status"], "accepted")


if __name__ == "__main__":
    unittest.main()
