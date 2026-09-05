# Full handoff example

This example performs a persistent read-only review of this repository's README. Ordinary ephemeral discovery should use Lite instead. Run commands from the repository root with Python 3.11+. Create a sibling directory named handoff; all JSON and logs belong there, outside the monitored repository.

Save the following as ../handoff/spec.json. These are judgment fields; the helper supplies node identity, version defaults and actual file state.

```json
{
  "stage_id": "readme-review",
  "objective": "Check that installation instructions distinguish routing from model migration.",
  "permission": "read-only",
  "owned_paths": [],
  "input_paths": ["README.md"],
  "safety_boundaries": ["Read local files only; no installation or external actions."],
  "acceptance_criteria": [
    {"id": "A-1", "description": "README distinguishes apply-preset from explicit Astra migration.", "verification": "manual"}
  ]
}
```

```powershell
python -B skills/orchestrator/scripts/context_tool.py prepare --workspace-root . --spec ../handoff/spec.json --out ../handoff/capsule.json
python -B skills/orchestrator/scripts/context_tool.py ready --workspace-root . --capsule ../handoff/capsule.json
```

The reviewer now reads README.md and checks the stated behavior. The file check alone cannot judge whether the description is correct. Only after observing the documented distinction, save this report as ../handoff/report.json; change its conclusion/status/evidence if the actual finding differs. Terra returns the report inline and the root writes the sidecar file because Terra is read-only.

```json
{
  "execution_status": "completed",
  "conclusion": "README separates routing/safety settings from the explicit Astra model option.",
  "changed_files": [],
  "evidence": [
    {"id": "E-1", "kind": "path", "ref": "README.md", "result": "Installation section documents both apply-preset and model-preset astra.", "verified": true}
  ]
}
```

```powershell
python -B skills/orchestrator/scripts/context_tool.py result --workspace-root . --capsule ../handoff/capsule.json --records-dir ../handoff/records --report ../handoff/report.json --out ../handoff/delta.json
```

The root independently reviews the cited README and authorizes acceptance. Save its decision as ../handoff/review.json only after that review:

```json
{
  "acceptance_status": "accepted",
  "criteria": [
    {"criterion_id": "A-1", "decision": "met", "reason": "The cited installation section explicitly distinguishes the two options.", "evidence_ids": ["E-1"]}
  ]
}
```

```powershell
python -B skills/orchestrator/scripts/context_tool.py accept --workspace-root . --capsule ../handoff/capsule.json --records-dir ../handoff/records --delta ../handoff/delta.json --review ../handoff/review.json --out ../handoff/acceptance.json
```

The generated acceptance binds the exact capsule, Delta and observed file state. Reusing these commands with an existing output file stops instead of overwriting history. A new or changed assignment needs a new output path and the appropriate node version.

For delegated implementation, use scoped-write, explicit owned_paths and command criteria with expected_exit_code. run-check accepts an argv after -- and writes a receipt with the actual process outcome. Put the receipt filename in report.check_records and reference its check ID from command evidence. Do not execute checks through read-only roles.

To see the complete implementation/check/acceptance path in an isolated temporary project, run:

```powershell
python -B -m unittest tests.test_context_workflow.ContextWorkflowTests.test_complete_workflow_records_real_exit_and_output -v
```

Receipt hashes detect mismatched or changed records, not a malicious actor who can rewrite all records. Manual acceptance remains a root judgment. Files outside the workspace, databases, services and environment state require separate task-specific checks.
