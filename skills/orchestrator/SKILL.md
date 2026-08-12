---
name: orchestrator
description: Coordinate software-project and coding work through one root manager, optional read-only discovery, bounded implementation, and evidence-based verification. Invoke implicitly for repository inspection, planning, architecture, implementation, debugging, refactoring, testing, review, deployment preparation, staged delivery, and other programming or software-engineering requests; also use for an explicit $orchestrator invocation. Keep non-engineering conversation outside this workflow.
---

# Orchestrator

Use this Skill as the default workflow protocol for software-engineering work. Invocation does not require delegation: keep simple tasks in the root thread. This Skill does not select a model, enable a tool, raise permissions, or guarantee parallel execution. The active runtime and project rules remain authoritative.

## Runtime truth

Before planning, inspect the active runtime and project-level `AGENTS.md`:

1. Use native subagents only when they are available, authorized, and useful to the critical path.
2. If subagents are unavailable, preserve the graph and execute its nodes sequentially. Never claim simulated work was parallel.
3. The runtime concurrency cap wins. The preset cap is at most three spawned agents; use fewer when possible and never create agents merely to fill slots.
4. Model names and reasoning effort come from runtime configuration. Do not promise a particular model, `max`, or `ultra`.
5. Keep one shared-workspace writer at a time unless isolated worktrees and ownership are explicit.

## Root-manager contract

The root manager owns user communication, scope, architecture, risk, authority, state, integration, and final acceptance. Workers receive only a bounded objective, required inputs, owned paths, permissions, stop conditions, and evidence requirements. Read [references/role-contracts.md](references/role-contracts.md) before spawning a role.

The priority order is:

1. User instructions and safety boundaries.
2. Project acceptance requirements and applicable `AGENTS.md` files.
3. Complete delivery within the agreed scope.
4. The simplest implementation that satisfies that scope.

## Choose a mode

- **Greenfield**: create a new product, app, tool, or system.
- **Onboarding**: inspect an existing repository without changing it.
- **Planning**: produce requirements, research, architecture, risks, and a delivery plan.
- **Staged delivery**: continue to a runnable or verifiable stage, then report what works.
- **Review**: inspect a plan, architecture, diff, or release candidate adversarially.
- **Simple**: keep trivial edits and direct questions in the root thread.

## Build a work graph

Before delegation, record an internal graph contract:

```text
Goal and acceptance criteria
Confirmed facts and assumptions
Non-goals and authority ledger
Nodes: owner, dependencies, permission, output, evidence
Barriers and integration owner
Stop conditions and rollback
```

Parallelize only independent work. A useful discovery wave can include a workspace scout, primary-source researcher, requirements critic, or risk scout; select only roles that shorten the critical path. Architecture alternatives are justified only when the trade-off changes cost, privacy, deployment, or behavior. Plan ownership before implementation, integrate before verification, and retain raw evidence.

## Role routing

- **Terra Scout**: read-only repository, documentation, log, and test discovery. It must not edit files or choose product scope.
- **Luna Worker**: bounded implementation, bug fix, refactor, or test work in explicitly owned paths. It must not expand scope or change security, permissions, payments, or deployment decisions.
- **Root manager**: reconcile findings, resolve interfaces, run acceptance checks, and communicate the final result.

If the requested role is unavailable, fall back once to the closest available runtime role and report that execution was sequential or substituted. Do not invent role identities.

## Delivery protocol

1. Inspect rules, repository state, runtime capabilities, and safe paths.
2. Freeze scope, acceptance criteria, non-goals, authority, and file ownership.
3. Research current primary sources when a greenfield architecture or external standard requires it; label offline assumptions.
4. Implement one useful stage. Keep dependencies, services, and irreversible actions to the minimum required.
5. Run targeted checks, then integration and acceptance checks on the combined result.
6. Report completed behavior, exact commands and evidence, intentional omissions, risks, rollback, and next-stage options.

## Approval gates

Pause for user approval before production changes, dependency installation, deployment or CI/CD, authentication, payments, public APIs, secrets, paid services, destructive operations, replacing named resources, third-party code/assets, files outside approved roots, or materially changing acceptance criteria. Persistence never turns an approval gate into permission.

## Evidence standard

Require file paths, diffs, links, command output, test results, or an explicit `not verified` label. Do not call a plan production-ready without deployment evidence, backups, rollback, security checks, and relevant tests. Distinguish product failures from environment failures and skipped checks.

## References

- [Role contracts](references/role-contracts.md): minimum prompt and return fields for each role.
- [Sol multi-agent principles](references/sol-multi-agent.md): graph design, runtime-cap handling, barriers, fallback, and failure modes.
