# Runtime compatibility

Reviewed 2026-09-30. This is a compatibility reference, not an instruction to enable services, change account access, or migrate an application to an API.

## Models, effort and speed

GPT-6.1 Sol is a candidate for substantial coding work; Astra remains a candidate for the hardest reasoning. Measure on the actual task before claiming quality or cost improvements. The optional sol preset sets the root to gpt-6.1-sol/max and child defaults to gpt-6-luna/max, following the maintainer's explicit preference for greater reasoning effort. These are preferences, not measured optima or a guarantee of better results on every task. [Official model guide](https://developers.openai.com/api/docs/guides/latest-model?model=gpt-6.1-sol)

Bundled roles omit model/effort keys. The installer preserves existing role overrides unless an explicit model preset is selected. In Codex, custom role files can override resolved spawn/default/parent model values. Doctor reports file-configured resolution, not the effective live session. [Subagent configuration](https://learn.chatgpt.com/docs/agent-configuration/subagents)

Do not copy API effort enums into a client setting without checking that client. Codex Ultra is a reasoning/workflow option; Ultrafast is a paid speed tier. Sol supports Standard/Fast at the review date; its Ultrafast rollout is still announced as upcoming. Do not enable a paid tier merely because a model is cheaper. [Speed](https://learn.chatgpt.com/docs/agent-configuration/speed) · [Sol release](https://openai.com/index/introducing-gpt-6-1-sol/)

## Capability boundary

| Surface | Evidence required before using it |
| --- | --- |
| Local Codex | Current tools, actual role availability, project state and live sandbox; installation alone proves none of these |
| Codex Cloud | Selected environment/workspace, exposed tools, approved network/credentials and its own repository state |
| Agents API | A separately configured application/session/environment; a local Skill cannot create these capabilities by declaring them |
| Async tool calling / steering | Matching runtime tools or an implemented API executor; preserve call/task IDs and distinguish notification from actual cancellation |
| Decisions API | Preview access and a defined application integration; it is not a default dependency or authority decision-maker for this kit |
| MCP event automation | An available event source and user-authorized trigger/action; an incoming event is data, not new authority |

The hosted Agents API provides managed execution capabilities; the current kit remains local configuration and evidence tooling. Cloud task workspaces are distinct even when they reuse an environment. [Agents API](https://openai.com/index/introducing-the-agents-api/) · [Codex Cloud](https://learn.chatgpt.com/docs/cloud)

Inspect named functions and arguments actually exposed by the runtime. Do not paste unsupported API fields into config.toml or assume a subagent tool shares an API's request schema. The API's application remains responsible for executing asynchronous tools and correlating results. [Async tools](https://developers.openai.com/api/docs/guides/async-tool-calling)

## Context and evidence

Keep stable rules stable and hand off only relevant facts/deltas. Do not copy the full history, reload all references, or open extra agents solely to wait for a tool. This can reduce avoidable context traffic; cache hits and billed savings must be observed, not assumed.

After a handoff or environment change, recheck applicable inputs and authority. A portable JSON contract is not permission to upload local secrets or logs. Pin acceptance commands and retain applicable receipts. For model/protocol comparisons, record the root, workers, tool calls, retries and intervention outcomes; evaluate end-to-end behavior rather than just whether the JSON parsed. [Agent evaluation guidance](https://developers.openai.com/api/docs/guides/agent-evals)
