# Role contracts

Use the smallest contract that preserves the boundary. A normal, low-risk read-only lookup uses the inline Lite Task Envelope. Any write, state-changing check, high-risk judgment, cross-task persistence, or dependent merge uses a JSON Full Context Capsule and a bound State Delta.

## Lite Task Envelope

Put these fields directly in the assignment:

```text
Role: <terra_scout or other read-only role>
Objective: <one concrete question or lookup>
Scope and non-goals: <paths to inspect and explicit exclusions>
Permission: read-only
Evidence required: <paths, commands, or observations to report>
Deliverable: compact Read-only Result with conclusion, evidence, risks, and next step
Stop conditions: missing input, permission boundary, contradictory evidence, or scope expansion
```

The result must not claim writes or execution checks. Upgrade to the Full Context Capsule when the node may mutate files, run a state-changing check, make a high-risk decision, persist context across tasks, or merge dependent work.

## Full Context Capsule

Serialize this schema as JSON for scoped-write, execute-checks, high-risk, persistent, or dependent handoffs:

```json
{
  "schema_version": 1,
  "stage_id": "stable stage identifier",
  "capsule_version": 1,
  "node_id": "unique node identifier",
  "objective": "one concrete objective",
  "acceptance_criteria": ["observable criterion"],
  "confirmed_decisions": [
    {"id": "D-1", "statement": "frozen decision", "evidence": ["path or command"]}
  ],
  "non_goals": ["explicit exclusion"],
  "dependencies_and_interfaces": ["completed node or frozen interface"],
  "owned_paths": ["relative/path.py", "relative/directory"],
  "permission": "read-only | scoped-write | execute-checks",
  "safety_boundaries": ["non-empty task-specific boundary"],
  "known_failures": ["exact failed check or none"],
  "evidence_index": [
    {"kind": "path | url | command", "ref": "non-empty reference", "result": "non-empty result", "verified": true}
  ],
  "open_questions": ["unresolved question or none"]
}
```

Every string array item must be a non-blank string. `owned_paths` are normalized relative paths or directory prefixes: no absolute paths, `..`, empty components, or wildcards. Keep `permission` independent from the non-empty `safety_boundaries` array. Decisions are objects with `id`, `statement`, and non-empty `evidence`; evidence-index entries use the object shape above.

## Required handshake and State Delta

Before acting, echo `received_capsule_version` and exactly one `context_status`: `sufficient`, `missing_context`, `stale_context`, or `contradictory_context`, plus `context_issues`. Only `sufficient` may proceed. A non-sufficient node must be `blocked` or `needs_decision`, report no changed files, and run no execution checks.

Return one State Delta with this shape:

```json
{
  "stage_id": "same as capsule",
  "node_id": "same as capsule",
  "status": "completed | blocked | needs_decision",
  "received_capsule_version": 1,
  "context_status": "sufficient",
  "context_issues": [],
  "capsule_digest": "sha256:<64 lowercase hex characters>",
  "conclusion": "compact result",
  "evidence": [
    {"kind": "path | url | command", "ref": "non-empty reference", "result": "non-empty result", "verified": true}
  ],
  "changed_files": [],
  "checks": [
    {"command": "non-empty command", "status": "passed | failed | not_run", "summary": "non-empty summary"}
  ],
  "new_facts": [],
  "invalidated_assumptions": [],
  "open_questions": [],
  "risks": [],
  "recommended_next": "one next action or null"
}
```

The digest is SHA-256 over the capsule's canonical JSON (`sort_keys=True`, compact separators, UTF-8, `ensure_ascii=False`). The validator binds stage, node, version, and digest to the exact capsule supplied with `--capsule-file`; it does not prove that evidence result text is true or enforce native Codex permissions. It is a protocol check, not a Codex native pre-spawn/pre-merge gate.

For a `read-only` or `execute-checks` capsule, `changed_files` must be empty. `execute-checks` permits commands but not persistent deliverable-file changes; use `scoped-write` and explicit ownership when a check must create or update retained files. For `scoped-write`, every changed path must equal or be below an `owned_paths` entry. A completed result requires sufficient context, no context issues, and at least one `verified: true` evidence item.

Validate a pair with the bundled stdlib-only checker:

```text
python scripts/validate_context_contract.py --kind capsule --file capsule.json --expected-version 1
python scripts/validate_context_contract.py --kind delta --file delta.json --capsule-file capsule.json --workspace-root .
```

## Role boundaries

- Terra Scout uses Lite for ordinary read-only discovery and returns only a compact Read-only Result. Upgrade when the task crosses the Full Capsule rules.
- Luna Worker validates a Full Capsule before writing, edits only owned paths, runs the narrowest meaningful check, and returns one State Delta.
- The root manager owns scope, authority, capsule versions, integration, and final acceptance. It verifies evidence and increments the version after an accepted material change.
