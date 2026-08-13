# Multi-agent principles

This reference explains why the Skill uses a graph and runtime-aware delegation. It is guidance, not a claim that every Codex runtime exposes the same models or tools.

## Graph and barriers

Treat work as nodes with dependencies, permissions, owners, outputs, and evidence. Use barriers to preserve causality:

- discovery before architecture;
- architecture and ownership before implementation;
- implementation before integration;
- integration before tests, review, and acceptance.

The root manager owns shared state and synthesizes evidence; workers are specialized tools, not autonomous project managers.

## Useful parallelism

Parallelize independent inspection, primary-source research, requirements criticism, risk analysis, competing architecture proposals, or post-integration review. Do not duplicate routine implementation, edit the same files concurrently, or spawn agents just because slots exist. The active runtime cap is authoritative; the public preset uses a maximum of three spawned agents and can be lowered or raised only by an explicit project configuration that the runtime actually honors.

## Budgets, reuse, and context

A concurrency limit alone does not prevent a long task from opening dozens of agents sequentially. Use a creation budget as well as the runtime cap:

- create no agents for simple work, at most one for medium work, and normally at most two new agents in a complex user turn;
- create at most six agents in one delivery stage, then integrate and checkpoint instead of opening another wave;
- inspect the existing roster before spawning and reuse an idle agent with the same responsibility;
- start focused agents with fresh context by default and pass a versioned Context Capsule containing the objective, acceptance criteria, decisions and evidence, non-goals, interfaces, ownership, safety boundaries, failures, and open questions;
- require the child to confirm the received version and declare `sufficient`, `missing_context`, `stale_context`, or `contradictory_context`; only `sufficient` may act, and every result returns a structured State Delta for root verification;
- keep scouts and workers as leaf roles and ask for one compact final result rather than routine progress messages;
- after a second context compaction, stop expanding the team and hand off to a fresh task.

The third runtime slot remains a safety ceiling. It is useful when a relevant existing agent is reused alongside two new independent assignments, not as a target for every complex request.

## Safety and authority

Keep an authority ledger with `allowed`, `must ask`, and `forbidden` actions. Production changes, credentials, external services, paid operations, destructive work, deployment, third-party copying, and scope changes require approval. Persistence does not create authority, and a different resource must never be substituted for a named one during destructive work.

## Graceful degradation

If native subagents are unavailable, run the same nodes sequentially and say so. If a role fails, retry once only for a transient failure with the same contract; otherwise replan or report the blocker. Never fill missing upstream evidence with guesses or claim unverified work passed.

## Completion

Completion requires an integrated artifact, acceptance criteria mapped to observable evidence, relevant checks run or marked unverified, must-fix findings resolved, and a root-owned report covering risks, omissions, and rollback.
