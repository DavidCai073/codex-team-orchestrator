from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "skills" / "orchestrator" / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))
import validate_context_contract as validator
from workspace_state import digest


def inventory(contents: str = "old") -> dict:
    result = {"files": {"src/contract.py": {"digest": digest(contents), "kind": "file", "executable": False}},
              "excluded_paths": [], "git_head": None, "dirty_paths": []}
    result["digest"] = digest(result)
    return result


def capsule(permission: str = "scoped-write") -> dict:
    return {
        "schema_version": 2, "stage_id": "stage-contract", "capsule_version": 10,
        "node_id": "node-write-contract", "objective": "Harden the contract validator.",
        "acceptance_criteria": [{"id": "A-1", "description": "Regression passes.", "verification": "command", "expected_exit_code": 0}],
        "confirmed_decisions": [], "non_goals": [], "dependencies_and_interfaces": [],
        "owned_paths": ["src", "tests/test_contract.py"], "input_paths": [],
        "permission": permission, "safety_boundaries": ["No files outside ownership"],
        "known_failures": [], "evidence_index": [], "open_questions": [], "workspace_base": inventory(),
    }


def delta_for(cap: dict, **updates: object) -> dict:
    check = {"id": "check-1", "command": ["python", "-B", "-m", "unittest"], "cwd": ".",
             "exit_code": 0, "status": "passed", "summary": "Passed",
             "workspace_digest": digest(inventory("new")["files"]), "stdout_digest": digest("output"),
             "stderr_digest": digest(""), "record": "check-1.json"}
    result = {
        "schema_version": 2, "stage_id": cap["stage_id"], "node_id": cap["node_id"],
        "execution_status": "completed", "received_capsule_version": cap["capsule_version"],
        "context_status": "sufficient", "context_issues": [], "capsule_digest": validator.capsule_digest(cap),
        "conclusion": "Contract changed.", "evidence": [
            {"id": "E-1", "kind": "command", "ref": "check-1", "result": "Passed", "verified": True}],
        "changed_files": ["src/contract.py"], "checks": [check], "new_facts": [],
        "invalidated_assumptions": [], "open_questions": [], "risks": [], "recommended_next": None,
        "workspace_after": inventory("new"),
    }
    result.update(updates)
    return result


def review() -> dict:
    return {"acceptance_status": "accepted", "criteria": [
        {"criterion_id": "A-1", "decision": "met", "reason": "Observed expected exit.",
         "evidence_ids": ["E-1"]}]}


class ContextContractTests(unittest.TestCase):
    def test_valid_pair(self):
        cap = capsule()
        self.assertEqual(validator.validate_capsule(cap), [])
        self.assertEqual(validator.validate_delta(delta_for(cap), capsule=cap), [])

    def test_malformed_top_level_fields_never_crash(self):
        for key in validator.CAPSULE_FIELDS:
            for value in (None, [], {}, True, 123):
                cap = capsule()
                cap[key] = value
                with self.subTest(kind="capsule", key=key, value=value):
                    errors = validator.validate_capsule(cap)
                    self.assertIsInstance(errors, list)
        cap = capsule()
        for key in validator.DELTA_FIELDS:
            for value in (None, [], {}, True, 123):
                with self.subTest(kind="delta", key=key, value=value):
                    self.assertIsInstance(validator.validate_delta(delta_for(cap, **{key: value}), capsule=cap), list)

    def test_bool_schema_version_rejected(self):
        cap = capsule()
        cap["schema_version"] = True
        self.assertTrue(validator.validate_capsule(cap))

    def test_nonportable_paths_rejected(self):
        for path in ("../escape", "C:src", "C:/src", "/src", "src//x", "src\\x", "src/../x", " src", "src/x."):
            cap = capsule()
            cap["owned_paths"] = [path]
            with self.subTest(path=path):
                self.assertTrue(validator.validate_capsule(cap))

    def test_sufficient_with_context_issues_rejected(self):
        cap = capsule()
        self.assertTrue(validator.validate_delta(delta_for(cap, context_issues=["old"]), capsule=cap))

    def test_non_sufficient_cannot_mutate_or_execute(self):
        cap = capsule()
        errors = validator.validate_delta(delta_for(cap, execution_status="blocked",
            context_status="stale_context", context_issues=["input changed"]), capsule=cap)
        self.assertTrue(any("must not report changed_files or execution checks" in e for e in errors))

    def test_read_only_and_execute_checks_cannot_change_files(self):
        for permission in ("read-only", "execute-checks"):
            cap = capsule(permission)
            self.assertTrue(validator.validate_delta(delta_for(cap), capsule=cap))

    def test_binding_mismatches_rejected(self):
        cap = capsule()
        for field, value in (("stage_id", "other"), ("node_id", "sibling"),
                             ("received_capsule_version", 9), ("capsule_digest", "sha256:" + "0" * 64)):
            self.assertTrue(validator.validate_delta(delta_for(cap, **{field: value}), capsule=cap))

    def test_unreported_changes_rejected(self):
        cap = capsule()
        errors = validator.validate_delta(delta_for(cap, changed_files=[]), capsule=cap)
        self.assertTrue(any("actual workspace changes" in e for e in errors))

    def test_outside_ownership_detected_from_snapshot(self):
        cap = capsule()
        after = inventory("new")
        after["files"]["outside.txt"] = after["files"]["src/contract.py"]
        after["digest"] = digest({k: v for k, v in after.items() if k != "digest"})
        errors = validator.validate_delta(delta_for(cap, workspace_after=after,
            changed_files=["src/contract.py", "outside.txt"]), capsule=cap)
        self.assertTrue(any("outside owned_paths" in e for e in errors))

    def test_completed_failure_is_execution_only(self):
        cap = capsule()
        delta = delta_for(cap)
        delta["checks"][0].update(status="failed", exit_code=1)
        self.assertEqual(validator.validate_delta(delta, capsule=cap), [])
        self.assertTrue(validator.validate_acceptance(review(), cap, delta))

    def test_expected_failure_can_satisfy_diagnostic_criterion(self):
        cap = capsule()
        cap["acceptance_criteria"][0]["expected_exit_code"] = 1
        delta = delta_for(cap)
        delta["checks"][0].update(status="failed", exit_code=1)
        self.assertEqual(validator.validate_acceptance(review(), cap, delta), [])

    def test_missing_check_cannot_be_accepted(self):
        cap = capsule()
        self.assertTrue(validator.validate_acceptance(review(), cap, delta_for(cap, checks=[])))

    def test_unverified_evidence_and_unmapped_criterion_rejected(self):
        cap = capsule()
        delta = delta_for(cap)
        delta["evidence"][0]["verified"] = False
        self.assertTrue(validator.validate_acceptance(review(), cap, delta))
        self.assertTrue(validator.validate_acceptance({"acceptance_status": "accepted", "criteria": []}, cap, delta))

    def test_cli_missing_capsule_and_actual_stale_reason(self):
        path = str(SCRIPT_DIR / "validate_context_contract.py")
        result = subprocess.run([sys.executable, "-B", path, "--kind", "delta"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn("--capsule-file is required", result.stderr)
        with tempfile.TemporaryDirectory() as folder:
            cap = capsule()
            capsule_path = Path(folder) / "capsule.json"
            capsule_path.write_text(json.dumps(cap), encoding="utf-8")
            bad = delta_for(cap, execution_status="blocked", context_status="stale_context", context_issues=["changed"])
            result = subprocess.run([sys.executable, "-B", path, "--kind", "delta",
                "--capsule-file", str(capsule_path)], input=json.dumps(bad), text=True, capture_output=True)
            self.assertEqual(result.returncode, 2)
            self.assertIn("must not report changed_files or execution checks", result.stderr)

    def test_null_evidence_with_workspace_rejected_without_crash(self):
        cap = capsule()
        self.assertTrue(validator.validate_delta(delta_for(cap, evidence=None), capsule=cap, workspace_root=ROOT))

    def test_symlink_policy_without_platform_privileges(self):
        cap = capsule()
        cap["workspace_base"]["files"]["src/contract.py"]["kind"] = "symlink"
        cap["workspace_base"]["digest"] = digest({k: v for k, v in cap["workspace_base"].items() if k != "digest"})
        self.assertTrue(any("symlinks" in error for error in validator.validate_capsule(cap)))

    def test_read_only_execution_receipt_rejected(self):
        cap = capsule("read-only")
        errors = validator.validate_delta(delta_for(cap, changed_files=[], workspace_after=cap["workspace_base"]), capsule=cap)
        self.assertTrue(any("must not execute checks" in error for error in errors))

    def test_manual_criterion_cannot_hide_missing_command_receipt(self):
        cap = capsule()
        cap["acceptance_criteria"][0]["verification"] = "manual"
        errors = validator.validate_acceptance(review(), cap, delta_for(cap, checks=[]))
        self.assertTrue(any("unreported check" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
