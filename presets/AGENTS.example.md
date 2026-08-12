# Team orchestration preset

Use the repository's project-level `AGENTS.md` as the acceptance authority. This file is a neutral template: merge it deliberately with existing rules rather than replacing user-owned instructions.

## Routing

- The root manager owns scope, architecture, risk, authority, integration, and final acceptance.
- `terra_scout` is read-only and may inspect code, documentation, logs, and tests.
- `luna_worker` performs only bounded writes in explicitly owned paths.
- Use the fewest agents that shorten the critical path. The default preset allows at most three spawned agents; never fill slots for their own sake.
- In a shared workspace, allow one writer at a time unless isolated worktrees and ownership are explicit.
- User instructions and safety boundaries outrank project acceptance; project acceptance outranks complete agreed scope; complete scope outranks minimal implementation.

## Invocation

- Use `$orchestrator` for complex, staged, greenfield, onboarding, architecture, research, testing, or review work.
- Keep simple edits and direct questions in the root thread.
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
