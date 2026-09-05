from __future__ import annotations

import importlib.util
import sys
import tomllib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from config_merge import ConfigMergeError, merge_values, same_semantics

SELECTED = {"sandbox_mode": "workspace-write", "agents": {"enabled": True}}


class ConfigMergeTests(unittest.TestCase):
    def assert_merge(self, source: str) -> dict:
        before = tomllib.loads(source)
        after = tomllib.loads(merge_values(source, SELECTED))
        before["sandbox_mode"] = "workspace-write"
        before.setdefault("agents", {})["enabled"] = True
        self.assertEqual(after, before)
        return after

    def test_array_table_cannot_steal_agent_assignment(self):
        after = self.assert_merge('[agents]\ncustom_flag="keep"\n[[skills.config]]\npath="example"\nenabled=false\n')
        self.assertFalse(after["skills"]["config"][0]["enabled"])
        self.assertTrue(after["agents"]["enabled"])

    def test_root_keys_before_leading_array_table(self):
        after = self.assert_merge('[[skills.config]]\npath="example"\nenabled=false\n')
        self.assertNotIn("sandbox_mode", after["skills"]["config"][0])

    def test_basic_multiline_string_is_opaque(self):
        self.assert_merge('developer_instructions = """\nmodel = "example-only"\n[agents]\nenabled=false\n"""\n')

    def test_literal_multiline_string_is_opaque(self):
        self.assert_merge("developer_instructions = '''\n[agents]\nsandbox_mode = 'example'\n'''\n")

    def test_multiline_array_with_strings_and_comments(self):
        self.assert_merge('examples = [\n "[agents]", # comment\n "sandbox_mode = example",\n]\n[agents]\ncustom_flag="keep"\n')

    def test_comments_escapes_and_quote_closings(self):
        self.assert_merge('example = "escaped \\\" quote" # [agents]\ntext = """has trailing quotes"""""\n')

    def test_plain_config_and_idempotency(self):
        source = 'model="keep-model"\n[agents]\nenabled=false\ncustom_flag="keep"\n'
        self.assert_merge(source)
        once = merge_values(source, SELECTED)
        self.assertEqual(merge_values(once, SELECTED), once)

    def test_unselected_models_are_preserved(self):
        after = self.assert_merge('model="keep"\nmodel_reasoning_effort="high"\n[agents]\ndefault_subagent_model="custom"\n')
        self.assertEqual(after["model"], "keep")
        self.assertEqual(after["agents"]["default_subagent_model"], "custom")

    def test_quoted_or_inline_managed_table_is_safely_rejected(self):
        for source in ('["agents"]\nenabled=false\n', 'agents = {enabled=false}\n'):
            with self.subTest(source=source), self.assertRaises(ConfigMergeError):
                merge_values(source, SELECTED)

    def test_managed_multiline_value_is_safely_rejected(self):
        with self.assertRaises(ConfigMergeError):
            merge_values('sandbox_mode="""\nold\n"""\n', SELECTED)

    def test_invalid_toml_error_does_not_echo_contents(self):
        with self.assertRaises(ConfigMergeError) as caught:
            merge_values('secret_value = private-invalid-data', SELECTED)
        self.assertNotIn('private-invalid-data', str(caught.exception))

    def test_semantic_guard_distinguishes_booleans_from_integers(self):
        self.assertFalse(same_semantics({"value": True}, {"value": 1}))
        source = 'special = nan\n'
        self.assertTrue(same_semantics(tomllib.loads(source)["special"], tomllib.loads(merge_values(source, SELECTED))["special"]))


if __name__ == "__main__":
    unittest.main()
