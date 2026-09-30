# DevDay 2026 审查与迭代

核验日期：2026-09-30（Asia/Shanghai）。基线：b26551e / 0.2.0，以及审查开始时已有的 Lite 小范围写入、按文件归属并行两处未提交修改；这些既有修改予以保留。交付版本：0.3.0。

## 官方发布与本项目的关系

DevDay 在美国当地 9 月 29 日举行。此次覆盖模型、长期代理、云端执行、协作产物和插件能力。本次不把公告中的可用性等同于当前账号已开通，也不把 API 特性当成 Skill 能启用的客户端功能。[官方回顾](https://openai.com/index/devday-2026-recap/)

| 变化或资料 | 证据 | 本项目决定 |
| --- | --- | --- |
| GPT-6.1 Sol 的能力/成本定位 | [发布说明](https://openai.com/index/introducing-gpt-6-1-sol/) | 增加 Sol 比较预设；保留 Astra 选择，不宣称本项目已测出相同质量或固定节省比例 |
| 自定义角色覆盖默认模型 | [Codex 子任务配置](https://learn.chatgpt.com/docs/agent-configuration/subagents) | 移除模板硬编码模型；普通替换保留用户覆盖，显式预设才让受管角色继承新默认 |
| Codex Cloud 独立任务工作区 | [Cloud 文档](https://learn.chatgpt.com/docs/cloud) | 明确环境/文件状态边界；不假设本地目录在云端存在 |
| 托管 Agents API | [9 月 10 日发布](https://openai.com/index/introducing-the-agents-api/) | 使用现有运行时能力；本轮不引入托管执行器、API 密钥、SDK 或自建调度服务 |
| Decisions API 有限预览 | [DevDay 回顾](https://openai.com/index/devday-2026-recap/) | 暂不作为本地路由依赖，也不用于授予权限；规则先保持可读、可验证 |
| 按执行轨迹评测 | [Agent evals](https://developers.openai.com/api/docs/guides/agent-evals) | 更新对照矩阵，分别测模型、协议、档位；记录完整主线程/子任务成本和返工 |
| Dots 持续工作与云电脑 | [Dots 发布](https://openai.com/index/introducing-dots/) | Dots 可成为任务入口；本 Skill 负责具体工程任务的范围、证据和验收，不重复实现常驻代理 |

## 代码审查发现与修复

1. **选择预设却未真正切换子任务模型。** 旧角色模板固定 GPT-5.6，优先于默认子模型。现改为模型中性的角色；保留已有角色覆盖的普通安装，与显式选择新预设的安装分开验证。doctor 输出配置来源，实时生效状态仍标为未验证。
2. **只匹配退出码不足以约束验收。** 旧验证器允许一个无关但成功的检查满足命令验收。现在新合同固定 argv、cwd 和预期退出码，根验收要求三者匹配，并继续检查代码和日志摘要。旧 schema 2 数据仍可读取；缺少命令约束的旧验收项不能自动标记为满足。
3. **证据目录约束可能触发多余权限请求。** 旧 helper 强制写到项目外。现保留外部 sidecar，也允许显式 --exclude .orchestrator 后使用项目内专用目录；拒绝用任意排除的业务目录替代。
4. **并行描述超出 Full 实现能力。** 按文件归属的 Lite 优化予以保留，但 Full 仍观察整个工作区。明确并行 Full 写入需要隔离 worktree；不通过忽略未知改动来制造并行能力。
5. **简单任务隐式触发过宽。** 入口改为有独立委派、多阶段集成、持久交接或未解决跨模块问题时使用；参考资料按需读取。

## 模型与成本建议

本项目按维护者在 2026-09-30 的明确选择，将 Sol 与 Luna 默认推理档设为 max，保留 Standard 速度；困难判断仍可使用 Astra。此前 high 是控制日常成本的建议起点，不是官方最优档位或本地实测结论。Max 优先更充分的推理预算，实际质量、耗时与总用量仍须对照。[模型选择指导](https://developers.openai.com/api/docs/guides/latest-model?model=gpt-6.1-sol)

本项目的模型预设不会设置速度档。已有 Fast 配置会保留。Ultra 推理与 Ultrafast 加速属于不同设置；截至核验日期，Sol 的 Ultrafast 仍为预告。API 金额、购买的 credits 与订阅内额度不能混作同一种计费。[Codex Speed](https://learn.chatgpt.com/docs/agent-configuration/speed)

普通升级不改变用户模型。显式 --model-preset sol 会选择 Sol max 和默认 Luna max，并移除两个受管角色的旧模型覆盖。其他自定义角色不在这项迁移范围内。不要只看主模型名称就推断所有子任务也换了模型。

## Dots 的合理分工

官方文档描述 Dots 由 Astra 驱动；Codex 的默认模型配置不能被当作 Dots 模型开关。Dots 可以在已配置的 Codex Cloud 环境启动任务；连接本地电脑后也可调用当地任务与本地 Skill。[Dots 入门](https://help.openai.com/en/articles/20001530-getting-started-with-your-dot)

本项目建议：Dots 接收反馈、维护任务背景、提出有证据的问题；Codex 承担具体代码修改；Skill 冻结范围、界定文件归属、验证证据并交付。先选择一个持续职责，例如跟踪该仓库的新 issue/PR，生成问题摘要和可审查修复建议；用实际价值决定是否扩大任务数量。不要仅因为具备常驻能力就反复轮询无变化状态。

## 验证边界

自动化回归验证配置继承/保留、错误命令拒绝、项目内证据目录、原始文件保护及完整交接。它们不能证明真实模型效果、账户可用性或客户端已经加载。实际结果见随交付物生成的验证记录。

未实施的功能：Dots 自动开通或连接账号、云环境发布、付费速度档启用、Decisions API 调用、Agents API 应用迁移。需要这些功能时应以当时的账户能力和具体目标安排工作，不把它们藏入 Skill 安装过程。
