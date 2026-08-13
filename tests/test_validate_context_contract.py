from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = ROOT / "skills" / "orchestrator" / "scripts" / "validate_context_contract.py"
SPEC = importlib.util.spec_from_file_location("context_validator", VALIDATOR_PATH)
assert SPEC and SPEC.loader
validator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validator)


def capsule(permission: str = "scoped-write") -> dict[str, object]:
    return {
        "schema_version": 1,
        "stage_id": "stage-contract",
        "capsule_version": 10,
        "node_id": "node-write-contract",
        "objective": "Harden the contract validator.",
        "acceptance_criteria": ["Adversarial payloads are rejected."],
        "confirmed_decisions": [
            {"id": "D-1", "statement": "Use canonical digest binding.", "evidence": ["README.md"]}
        ],
        "non_goals": ["Do not change runtime model settings."],
        "dependencies_and_interfaces": ["Python 3.11 stdlib"],
        "owned_paths": ["src", "tests/test_contract.py"],
        "permission": permission,
        "safety_boundaries": ["No dependencies", "No files outside owned paths"],
        "known_failures": [],
        "evidence_index": [
            {"kind": "path", "ref": "README.md", "result": "contract documented", "verified": True}
        ],
        "open_questions": [],
    }


def delta_for(cap: dict[str, object], **updates: object) -> dict[str, object]:
    result: dict[str, object] = {
        "stage_id": cap["stage_id"],
        "node_id": cap["node_id"],
        "status": "completed",
        "received_capsule_version": cap["capsule_version"],
        "context_status": "sufficient",
        "context_issues": [],
        "capsule_digest": validator.capsule_digest(cap),
        "conclusion": "Contract hardening is complete.",
        "evidence": [
            {"kind": "command", "ref": "python -B -m unittest", "result": "passed", "verified": True}
        ],
        "changed_files": ["src/contract.py"],
        "checks": [{"command": "python -B -m unittest", "status": "passed", "summary": "passed"}],
        "new_facts": [],
        "invalidated_assumptions": [],
        "open_questions": [],
        "risks": [],
        "recommended_next": None,
    }
    result.update(updates)
    return result


class ContextContractTests(unittest.TestCase):
    def assert_valid_capsule(self, cap: dict[str, object]) -> None:
        self.assertEqual(validator.validate_capsule(cap), [])

    def test_valid_pair(self) -> None:
        cap = capsule()
        self.assert_valid_capsule(cap)
        self.assertEqual(validator.validate_delta(delta_for(cap), capsule=cap), [])

    def test_wrong_list_item_and_empty_string_are_rejected(self) -> None:
        cap = capsule()
        cap["acceptance_criteria"] = [""]
        cap["non_goals"] = [123]
        cap["confirmed_decisions"] = ["not an object"]
        errors = validator.validate_capsule(cap)
        self.assertTrue(any("acceptance_criteria[0]" in error for error in errors))
        self.assertTrue(any("non_goals[0]" in error for error in errors))
        self.assertTrue(any("confirmed_decisions[0]" in error for error in errors))

    def test_sufficient_with_context_issues_is_rejected(self) -> None:
        cap = capsule()
        errors = validator.validate_delta(delta_for(cap, context_issues=["old issue"]), capsule=cap)
        self.assertTrue(any("context_issues to be []" in error for error in errors))

    def test_completed_without_verified_evidence_is_rejected(self) -> None:
        cap = capsule()
        unverified = [{"kind": "command", "ref": "echo", "result": "passed", "verified": False}]
        errors = validator.validate_delta(delta_for(cap, evidence=unverified), capsule=cap)
        self.assertTrue(any("verified evidence" in error for error in errors))

    def test_read_only_delta_cannot_change_files(self) -> None:
        cap = capsule("read-only")
        errors = validator.validate_delta(delta_for(cap), capsule=cap)
        self.assertTrue(any("read-only capsule" in error for error in errors))

    def test_execute_checks_delta_cannot_change_files(self) -> None:
        cap = capsule("execute-checks")
        errors = validator.validate_delta(
            delta_for(cap, changed_files=["outside.txt"]), capsule=cap
        )
        self.assertTrue(any("execute-checks capsule" in error for error in errors))

    def test_owned_path_escape_is_rejected(self) -> None:
        cap = capsule()
        errors = validator.validate_delta(delta_for(cap, changed_files=["other/file.py"]), capsule=cap)
        self.assertTrue(any("outside owned_paths" in error for error in errors))

    def test_stage_node_version_mismatch_is_rejected(self) -> None:
        cap = capsule()
        errors = validator.validate_delta(
            delta_for(cap, stage_id="wrong-stage", node_id="sibling", received_capsule_version=9),
            capsule=cap,
        )
        self.assertTrue(any("stage_id does not match" in error for error in errors))
        self.assertTrue(any("node_id does not match" in error for error in errors))
        self.assertTrue(any("received_capsule_version does not match" in error for error in errors))

    def test_digest_tamper_is_rejected(self) -> None:
        cap = capsule()
        errors = validator.validate_delta(delta_for(cap, capsule_digest="sha256:" + "0" * 64), capsule=cap)
        self.assertTrue(any("capsule_digest does not match" in error for error in errors))

    def test_sibling_node_digest_pair_is_rejected(self) -> None:
        cap = capsule()
        sibling = capsule()
        sibling["node_id"] = "sibling-node"
        delta = delta_for(cap)
        errors = validator.validate_delta(delta, capsule=sibling)
        self.assertTrue(any("node_id does not match" in error for error in errors))

    def test_stale_context_cannot_mutate_or_run_checks(self) -> None:
        cap = capsule()
        errors = validator.validate_delta(
            delta_for(
                cap,
                status="blocked",
                context_status="stale_context",
                context_issues=["version is stale"],
                changed_files=["src/contract.py"],
                checks=[{"command": "pytest", "status": "passed", "summary": "passed"}],
            ),
            capsule=cap,
        )
        self.assertTrue(any("must not report changed_files" in error for error in errors))
        self.assertTrue(any("must not run execution checks" in error for error in errors))

    def test_workspace_root_checks_path_evidence(self) -> None:
        cap = capsule()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "evidence.txt").write_text("verified", encoding="utf-8")
            evidence = [{"kind": "path", "ref": "evidence.txt", "result": "present", "verified": True}]
            delta = delta_for(cap, evidence=evidence)
            self.assertEqual(validator.validate_delta(delta, capsule=cap, workspace_root=root), [])
            missing = delta_for(
                cap,
                evidence=[{"kind": "path", "ref": "missing.txt", "result": "present", "verified": True}],
            )
            self.assertTrue(validator.validate_delta(missing, capsule=cap, workspace_root=root))

    def test_cli_requires_capsule_file_for_delta(self) -> None:
        cap = capsule()
        delta = delta_for(cap)
        with tempfile.TemporaryDirectory() as directory:
            delta_file = Path(directory) / "delta.json"
            delta_file.write_text(json.dumps(delta), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, "-B", str(VALIDATOR_PATH), "--kind", "delta", "--file", str(delta_file)],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("--capsule-file is required", result.stderr)

    def test_cli_valid_pair_emits_digest_and_leaves_no_cache(self) -> None:
        cap = capsule()
        delta = delta_for(cap)
        with tempfile.TemporaryDirectory() as directory:
            directory_path = Path(directory)
            capsule_file = directory_path / "capsule.json"
            delta_file = directory_path / "delta.json"
            capsule_file.write_text(json.dumps(cap, ensure_ascii=False), encoding="utf-8")
            delta_file.write_text(json.dumps(delta, ensure_ascii=False), encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(VALIDATOR_PATH),
                    "--kind",
                    "delta",
                    "--file",
                    str(delta_file),
                    "--capsule-file",
                    str(capsule_file),
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("VALID delta version=10 digest=sha256:", result.stdout)
            self.assertFalse(any(path.name == "__pycache__" for path in ROOT.rglob("__pycache__")))


if __name__ == "__main__":
    unittest.main()
