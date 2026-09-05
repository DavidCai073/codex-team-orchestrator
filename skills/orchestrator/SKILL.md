---
name: orchestrator
description: Route software-engineering work through a hands-on root, useful independent discovery, bounded implementation, and observable acceptance. Invoke implicitly for coding, repository inspection, planning, debugging, refactoring, testing, review, and deployment preparation; also use for an explicit $orchestrator request. Keep non-engineering conversation outside this workflow.
---

# Orchestrator

The root owns scope, authority, difficult implementation, integration, and acceptance. This Skill does not enable tools, select models, raise permissions, or guarantee parallelism. The active runtime and applicable project rules win.

## Route early

Inspect relevant project instructions, repository state, user intent, and available tools. Choose the shortest complete route before loading reference protocols.

- **Direct:** a small edit, direct explanation, or tightly coupled task stays in the root. Do the work and required checks; no graph, capsule, or delegation ceremony.
- **Lite:** delegate an independent low-risk read-only question with a compact inline assignment.
- **Full:** delegated writes, execution checks, high-risk analysis, persistent handoffs, and dependent integration use the generated versioned contract.

Lite and Full are the only delegated formats. Read [role-contracts.md](references/role-contracts.md) when delegation is justified, not for every direct task. Recover missing machine facts from the workspace; never ask the user to fill fields that the root can determine.

## Continue within authority

Match the concrete action and resource to existing session authorization and live permissions. Continue necessary authorized work without asking for the same authorization again. Reversibility alone grants no authority.

Resolve uncertainty through code, logs, documentation, and recorded decisions first. Ask only when an unresolved decision materially affects behavior, cost, authority, or irreversible outcomes. Block only the affected action and continue independent authorized preparation. Before an unapproved release or external change, prepare the code, checks and reviewable change description, then identify the exact remaining action and environment.

Authentication-related code is not automatically a new authorization request. Replacing the authentication provider, widening access, spending money, publishing, destructive data work, or touching a different resource must be covered by authorization. Never use a Skill or fallback role to bypass a runtime denial.

## Delegate when useful

With available tools, permission and budget, actually delegate when there is an independent deliverable and a concrete benefit:

- two independent investigations can run together;
- the root can implement while a scout investigates a separate compatibility question;
- an important change merits independent review of a defined code state.

After dispatch, continue independent root work; do not repeat the delegated investigation or poll unchanged status. Keep tightly coupled work together. The root implements the hardest parts when those depend on its full context; being the manager does not prohibit coding.

Terra is for focused read-only discovery. Luna is for clear implementation, regression tests and mechanical migrations with stable interfaces. Complex architecture, ambiguous debugging, security decisions and integration remain with the root. Use only roles/models exposed by the runtime, and preserve configured model choices unless a change is authorized.

Defaults: at most 3 active children, 0 new for simple work, normally 1 for medium work or 2 for a complex user turn, and 6 new per delivery stage. These are configurable guardrails, not measured optimal values; actual runtime limits always win. Do not relabel a stage to evade its budget. At the stage budget, integrate and checkpoint before deciding the next stage.

Inspect the existing roster before spawning. Reuse only when stage, problem domain, assumptions and context remain applicable; a matching role name alone is insufficient. There is no rule tying the third slot to agent age. Prefer fresh focused context using supported runtime options; never invent a tool parameter. Scouts and workers are leaves.

## Own state and changes

Before a Full assignment, freeze goal, acceptance, non-goals, authority, dependencies, and owned files. Use the helper to generate identities, defaults, node version, digest and file baseline. Keep one writer per shared workspace, including the root. Use isolated worktrees for concurrent writers.

Before acting, check the assigned inputs and state context sufficiency. The helper checks files and structure; the worker must still judge whether the assignment is understandable. Missing or conflicting context stops the affected mutation and goes back to the root.

Compare actual file changes against the baseline and the reported file list. Unexplained concurrent edits require reconciliation, not overwrite or deletion. A node version changes when its own contract changes. A stage revision alone does not invalidate independent results; changed inputs, interfaces, authority or acceptance may do so.

On user steering: update constraints, identify affected nodes, stop issuing affected actions, and use real interrupt/message tools where available. Recheck returned results against the updated authority. Do not claim that a message has stopped an external action; preserve still-valid work.

After compaction, recover goal, authority, baseline, pending nodes, accepted evidence and unresolved decisions. Continue when recoverable; repair missing evidence or pause only dependent work. Compaction count alone is not a reason to abandon a task.

## Verify and finish

Before editing, identify required behavior, mandatory project checks, conditions that require broader checks, and the code state to which results apply. Choose checks by impact, not line count.

Worker execution completion and root acceptance are separate. Map each acceptance criterion to observable evidence. Reuse applicable worker checks; rerun when relevant code/environment changes, a concrete concern remains, or project rules require it. Required checks passed with no unresolved concrete issue means stop checking and deliver.

Report completed behavior, checks and their limits, remaining risks, and the next necessary action. Do not claim production readiness without the relevant security, deployment, backup and rollback evidence. Distinguish product failures, environmental failures and skipped checks.

For failure classification, evidence limitations, and independent result reconciliation, read [execution principles](references/sol-multi-agent.md) as needed.
