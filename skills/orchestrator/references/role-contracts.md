# Role contracts

There are two delegated formats. Direct root work uses neither. The root supplies the installed helper's absolute path in Full assignments; never assume a project contains this Skill's scripts.

## Lite

Use an inline assignment for ordinary low-risk read-only discovery. A bounded local write can use Lite only if the actual role allows it; a role requiring Full (including the current luna_worker and any Full-configured sol_worker) still uses Full. Model tier does not relax the contract. For Lite writes, name exact owned files, expected current state, the single requested change, concrete acceptance/readback and stopping conditions. Do not delegate external actions or cross-task handoffs through this exception.

For read-only discovery:

- Role and one concrete objective.
- Scope, non-goals, and permission=read-only.
- Evidence required and a compact deliverable.
- Stop conditions: missing material input, changed authority, contradictory evidence, or scope expansion.

Return conclusion, evidence, risks/blockers and next step. No JSON, digest, file inventory or command receipts are required. Read-only inspection commands are allowed. An eligible Lite write returns actual changed paths and check results for root readback; it stops after the bounded change and necessary check. Other execution checks and retained writes require Full and the appropriate runtime role.

## Full: schema 2

Use Full for delegated writes/checks outside the eligible Lite case, high-risk analysis, cross-task persistence and dependent integration. Schema 1 capsules must be regenerated; installation manifests retain their existing rollback compatibility.

The authoritative machine fields, validation and enums are in ../scripts/validate_context_contract.py. Inspect them without loading a workspace:

    python -B /installed/skill/scripts/context_tool.py schema

The root writes a compact spec with stage_id, objective, acceptance_criteria, permission and non-empty safety_boundaries. Include owned_paths for writes and input_paths for read dependencies, using normalized relative paths. Optional decisions, non-goals, interfaces, failures, evidence and open questions default to empty lists. Decisions contain id, statement and a non-empty evidence list. Optional node_id and capsule_version identify this node; new nodes get a generated ID and version 1.

Each acceptance criterion contains id, description and verification ("command" or "manual"). New command criteria require command (a non-empty argv array), cwd (workspace-relative, defaults to ".") and integer expected_exit_code, normally 0. A diagnostic task can explicitly expect 1. Pin the actual executable spelling and arguments before execution. Schema 2 reports remain readable, but legacy command criteria without argv cannot be marked met; revise the node contract and produce matching evidence.

The helper supplies schema version, IDs/defaults, canonical digest, Git information and a file inventory. Store artifacts in an allowed sidecar directory, or use --exclude .orchestrator and keep them beneath the workspace's .orchestrator/ directory. The reserved directory must be explicitly excluded; arbitrary excluded code/vendor directories cannot be used for this exception. Respect runtime write roots. These artifacts may contain private paths/logs and must not be packaged or committed.

Use explicit exclusions only for generated/vendor data that is outside owned_paths and input_paths. Inventory covers all other files, including untracked and ignored files, and automatically excludes .git metadata. Large repositories should use an isolated workspace or deliberate generated/vendor exclusions. Every excluded path is an acknowledged gap, not an ownership allowance.

## Sequence

1. Root: context_tool.py prepare --workspace-root PROJECT --spec SPEC --out CAPSULE. Add --exclude PATH only for reviewed generated/vendor paths.
2. Worker: context_tool.py ready --workspace-root PROJECT --capsule CAPSULE. It reports received_capsule_version, context_status and context_issues from structural/file checks. Independently assess semantic context; echo sufficient only when both pass. Missing, stale or contradictory context stops affected writes/checks and returns specific issues to the root.
3. Worker: implement only owned files. Record required commands using context_tool.py run-check --workspace-root PROJECT --capsule CAPSULE --records-dir RECORDS -- COMMAND ARGS.
4. Worker: write a compact report, then context_tool.py result --workspace-root PROJECT --capsule CAPSULE --records-dir RECORDS --report REPORT --out DELTA.
5. Root: review the changes and evidence, write the criterion decisions, then context_tool.py accept --workspace-root PROJECT --capsule CAPSULE --records-dir RECORDS --delta DELTA --review REVIEW --out ACCEPTANCE.

All paths above are arguments, not literal filenames to copy. Use the README walkthrough for executable examples. An output path must be new; helpers do not overwrite existing contracts. Increment the affected node version and use a new file when scope, authority or acceptance changes.

A read-only scout or reviewer must not write sidecar files. It returns its compact Full report inline; the root materializes the Delta and review through the same helper. A task needing execution checks must use a runtime role with appropriate permission, not widen a read-only role implicitly.

## Worker report and evidence

The compact report requires execution_status ("completed", "blocked" or "needs_decision") and conclusion. Report changed_files explicitly, even though the helper observes actual changes: comparison detects omissions. Optional context_status defaults to sufficient; all issue/fact/risk lists default to empty and recommended_next to null.

Evidence entries contain id, kind ("path", "url" or "command"), ref, result and a boolean verified. A path ref is workspace-relative; a command ref is the generated check ID. check_records lists the generated receipt filenames. Do not handwrite successful exit codes or logs. The helper records argv, cwd, actual exit code, stdout/stderr hashes and code-state hashes.

run-check returns exit 0 when it successfully records an executed process, including a failed process. Its JSON exit_code/status carry the actual check outcome. Never treat the wrapper's exit code as the test result. Checks must leave monitored files stable to be reusable acceptance evidence. Put temporary test artifacts in a reviewed excluded directory or outside the workspace.

Historical failures can remain in a report. They cannot satisfy final-code acceptance unless their expected outcome and code state match the criterion. A skipped check is not passed.

## Root acceptance

execution_status=completed means the assigned execution is finished; it does not mean the feature passed.

The root review has acceptance_status ("accepted", "rejected" or "pending") and criteria. Each row has criterion_id, decision ("met", "unmet" or "unverified"), reason and evidence_ids. Cover each criterion exactly once. Accepted requires completed execution and all criteria met. Command criteria need a real receipt matching the planned argv, cwd, exit code and final code state. Another command exiting successfully cannot substitute. Manual criteria require root evidence review; a boolean cannot prove semantics.

The generated acceptance record binds the node capsule, Delta and reviewed file state. Current file state is compared with the worker result, and all baseline changes must match the reported list and ownership. Node version is compared only with that node's contract, never a global revision. Unexplained unrelated edits stop automatic acceptance and require root reconciliation; use isolated worktrees for independent writers.

The standalone validate_context_contract.py --kind delta --file DELTA --capsule-file CAPSULE checks the data contract. Add --workspace-root PROJECT to inspect current files. The accept helper additionally validates receipts and criterion mapping. A structurally valid Delta is never an accepted delivery.

## Limits and recovery

These are retrospective protocol/evidence checks, not a native pre-spawn/pre-merge gate or sandbox. They cannot prove who wrote a file, authenticate a self-reported semantic claim, revoke an external action, or monitor excluded/external state. A process able to forge all evidence can defeat file hashes. The root must inspect relevant evidence and runtime authority.

Recover context after compaction from the existing capsule, files, authority and evidence; do not regenerate a new baseline merely to erase a mismatch. When steering changes constraints, revise only affected node contracts, contact/interrupt affected workers through real tools, and recheck late results. Preserve valid independent work.
