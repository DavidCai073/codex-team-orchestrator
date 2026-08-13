# Team orchestration preset

Use the repository's project-level `AGENTS.md` as the acceptance authority. This file is a neutral template: merge it deliberately with existing rules rather than replacing user-owned instructions.

## Routing

- The root manager owns scope, architecture, risk, authority, integration, and final acceptance.
- `terra_scout` is read-only and may inspect code, documentation, logs, and tests.
- `luna_worker` performs only bounded writes in explicitly owned paths.
- Use the fewest agents that shorten the critical path. The default preset allows at most three spawned agents; never fill slots for their own sake.
- Treat three as a simultaneous hard ceiling, not a launch target. Keep simple work in the root, create at most one new agent for medium work, and normally create at most two new agents in one complex user turn.
- Create at most six agents in one delivery stage. When the stage reaches that budget, stop expansion, integrate and checkpoint before continuing; do not relabel work merely to reset the count.
- Before spawning, inspect the existing roster and reuse an idle agent with matching responsibility. Never duplicate an objective or file ownership.
- Start focused agents with fresh context by default and restate all task-specific safety, permission, ownership, and evidence requirements. Avoid full-history forks unless they are strictly necessary.
- Use a compact Lite Task Envelope for ordinary low-risk read-only discovery: role, objective, scope and non-goals, `permission=read-only`, evidence required, deliverable, and stop conditions. It returns a compact Read-only Result and does not require JSON, version, or digest.
- Upgrade to a versioned Full Context Capsule for writes, state-changing checks, high-risk judgments, cross-task persistence, or dependent merges. Include objective, acceptance criteria, decisions and evidence, non-goals, interfaces, ownership, safety boundaries, known failures, evidence index, and open questions; use empty JSON lists only where the schema permits them.
- For a Full Capsule, require `received_capsule_version` and `context_status`. Only `sufficient` may proceed; `missing_context`, `stale_context`, or `contradictory_context` must stop before mutation and identify the exact issue.
- Require one compact State Delta for a Full Capsule. The root manager verifies its evidence and capsule binding, rejects stale versions, merges accepted changes, and increments `capsule_version` after a material update.
- Scouts and workers are leaf roles: they do not delegate and return one compact result instead of routine progress chatter.
- After a second observed context compaction in the same task, create no new agents; integrate current work, write a concise handoff, and recommend a fresh task.
- In a shared workspace, allow one writer at a time unless isolated worktrees and ownership are explicit.
- User instructions and safety boundaries outrank project acceptance; project acceptance outranks complete agreed scope; complete scope outranks minimal implementation.

## Invocation

- Apply the `orchestrator` routing protocol implicitly to every programming and software-project request; the user does not need to name the Skill.
- Skill invocation does not require delegation. Keep simple edits and direct technical questions in the root thread, and expand into graph-based coordination only when complexity or independent work justifies it.
- Keep non-engineering conversation outside this routing protocol. `$orchestrator` remains available when the user wants to request it explicitly.
- Classify failures before retrying: `unavailable` may fall back once; `task_failure` returns to the root for replanning; `permission_boundary` must not be bypassed; `invalid_scope` stops immediately.
- If a requested role or model is `unavailable`, fall back once to the closest available runtime role, state the substitution, and preserve evidence requirements.
- If delegation is unavailable, execute the graph sequentially without claiming parallelism.

## Safety and acceptance

- Read the applicable project `AGENTS.md` before editing.
- Do not install dependencies, use credentials, change production systems, deploy, alter authentication/payments/public APIs, copy third-party code/assets, or perform destructive operations without explicit approval.
- Do not modify files outside the approved scope or silently change acceptance criteria.
- Require real paths, diffs, links, command output, or test results. Mark skipped or unavailable checks as `not verified`.
- Final acceptance belongs to the root manager and must cover behavior, tests, risks, omissions, and rollback.

## Project-level acceptance

Each real project should define its own `AGENTS.md` with the supported `run`, `build`, and `test` commands; observable acceptance criteria; protected paths and data; security requirements; deployment boundaries; and backup and rollback procedures. This global preset cannot decide that a project is production-ready without those facts.
