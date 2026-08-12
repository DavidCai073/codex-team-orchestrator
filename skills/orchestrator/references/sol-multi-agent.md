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

## Safety and authority

Keep an authority ledger with `allowed`, `must ask`, and `forbidden` actions. Production changes, credentials, external services, paid operations, destructive work, deployment, third-party copying, and scope changes require approval. Persistence does not create authority, and a different resource must never be substituted for a named one during destructive work.

## Graceful degradation

If native subagents are unavailable, run the same nodes sequentially and say so. If a role fails, retry once only for a transient failure with the same contract; otherwise replan or report the blocker. Never fill missing upstream evidence with guesses or claim unverified work passed.

## Completion

Completion requires an integrated artifact, acceptance criteria mapped to observable evidence, relevant checks run or marked unverified, must-fix findings resolved, and a root-owned report covering risks, omissions, and rollback.
