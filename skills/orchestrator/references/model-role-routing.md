# Model and role routing

The primary model is selected by the user/session, not by this Skill. The root is a hands-on engineer and retains shared decisions, authority, integration and acceptance. Preserve the user's explicit model/effort choices.

## Existing role setups

| Work | Route when available | Boundary |
| --- | --- | --- |
| Everyday development and direct fixes | GPT-6.1 Sol primary / max | Keep simple work direct |
| Substantial independent implementation | sol_worker configured for GPT-6.1 Sol / max | Explicit ownership, stable interface and the role's required Full contract |
| Focused code/document/log discovery | terra_scout configured for GPT-6 Luna / max | Read-only; legacy name does not select a model |
| Small understood changes and migrations | luna_worker configured for GPT-6 Luna / max | Bounded files and required Full contract |
| Consequential independent architecture/correctness analysis | astra_reviewer configured for GPT-6 Astra / high | Read-only second opinion; never release authority |

The kit installs terra_scout and luna_worker. sol_worker and astra_reviewer are optional existing local/runtime roles; their mention does not create them or promise their availability. Do not overwrite those user-owned profiles during routine kit installation. A different configured model/effort remains authoritative until explicitly changed.

## Escalation from a Sol primary

When a material architecture decision or cross-module/root-cause uncertainty remains unresolved after focused investigation, the root may invoke an available astra_reviewer for a bounded independent analysis. Existing task authorization and actual runtime permission must cover the delegation. No extra confirmation is needed solely because architecture or Astra is involved; an explicit restriction on delegation, model or spending still wins.

Pass the question, relevant files/evidence, attempted approaches and remaining uncertainty through the applicable Lite/Full contract. Request a supported diagnosis or tradeoff analysis, not a repeat of the entire task. Sol remains primary, reconciles the findings, continues implementation and performs final acceptance. Astra does not grant permission, change scope, or publish.

Leaf roles report blockers to the root and never spawn grandchildren. If a Luna assignment exposes unclear interfaces or wider impact, stop the affected mutation and return evidence. The root resolves machine facts, narrows the assignment or moves independent work to a capable available role.

Do not add review for routine resolved work. An Astra primary needs another Astra reviewer only when the independent opinion adds value. If the requested reviewer/model is unavailable, use the defined unavailable fallback once or continue supported root work and state the limitation. Never claim that a review occurred without a real call/result.

Custom role model/effort values can override spawn defaults. Inspect actual role configuration; do not assume a conflicting spawn argument changed the model. Model capability and Direct/Lite/Full selection are separate decisions.
