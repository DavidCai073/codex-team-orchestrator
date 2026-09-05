# Codex Team Orchestrator

一套零第三方依赖、可审计、可卸载恢复的 Codex 工程协作配置。主线程负责关键判断、困难实现、集成与验收；Terra 做聚焦调查，Luna 做接口明确的实现和回归。

> 非 OpenAI 官方项目。模型可用性、工具、权限和并发由实际客户端决定。当前没有真实任务对照评测结果，不承诺节省 Token 或提高成功率。

## 0.2.0 的变化

- 修复 TOML 数组表、多行字符串导致配置写错位置的问题；写入前验证目标值和所有非托管配置的语义不变。
- 默认应用调度预设时保留现有模型；显式选择 Astra 才调整主模型。
- 简单任务提前走主线程直接执行；委派保留 Lite / Full 两层，由脚本处理 Full 的机械字段。
- 复用现有授权，增加独立委派的正向条件；主线程可以亲自做困难实现。
- 按输入和约束变化处理结果失效；压缩后先恢复状态，不按次数直接放弃任务。
- Full schema 2 记录代码基线、实际改动和检查记录；区分执行结束与主线程验收通过。
- 必需检查通过且没有具体未解决问题时收口，避免重复验证。

## 安装与模型选择

需要 Python 3.11+ 和支持自定义 Skill/Agent 的目标客户端。先验证仓库：

~~~powershell
python -B scripts/validate.py
python -B scripts/install.py --dry-run
~~~

默认只复制 Skill 和两个角色文件：

~~~powershell
python -B scripts/install.py
~~~

应用调度、安全和并发设置，同时保留已有主模型和默认子模型：

~~~powershell
python -B scripts/install.py --dry-run --apply-preset
python -B scripts/install.py --apply-preset
~~~

在确认目标客户端支持后，显式迁移到 Astra high；Terra medium 为默认子模型。high 是迁移比较基线，没有宣称它最省：

~~~powershell
python -B scripts/install.py --dry-run --apply-preset --model-preset astra
python -B scripts/install.py --apply-preset --model-preset astra
~~~

配置来源分别是 presets/config.example.toml 与 presets/models.astra.toml。两个角色文件仍显式配置 Terra medium、Luna max，以便先比较主模型/协议变化。角色文件内的显式模型选择与默认子模型是两处设置；自定义时都要检查，不靠任务提示词假定覆盖。Luna 的职责限于清楚、稳定的执行任务，不承接所有困难实现。

安装器保留原始备份链。已有不同 Skill/角色文件时会停止；只有确认替换后才使用 --force。该选项不会绕过重复安装、旧备份链或无法证明安全的 TOML 合并。

合并支持普通表、数组表边界，以及非托管多行字符串/数组。涉及受管键的复杂引号、内联表或多行赋值时可能保守拒绝；原配置和安装目标不会部分写入。此时可只安装文件，再根据可见预设手工合并目标键。安装前后的非托管语义必须一致。

## 安装位置与诊断

默认 Skill 位置是 $CODEX_HOME/skills/orchestrator，角色位于 $CODEX_HOME/agents。未设置 CODEX_HOME 时按 ~/.codex 处理。

不同客户端的发现位置可能不同。如果目标客户端使用 ~/.agents/skills，可显式选择：

~~~powershell
python -B scripts/install.py --dry-run --skill-location agents
python -B scripts/install.py --skill-location agents
~~~

不会静默搬迁或删除另一个位置的副本；发现重复时停止，由用户核对。两种位置均支持卸载，旧安装清单也保留恢复能力。

~~~powershell
python -B scripts/doctor.py
~~~

doctor 区分文件存在、TOML/元数据有效、客户端发现和实际能力。前两项可检查；后两项明确输出 not_verified，不把文件存在当成加载成功。诊断只读，不输出配置正文或密钥值。

安装后重启目标客户端，检查它实际加载的 Skill、角色和工具。--codex-home 与 --user-home 可将安装、诊断和卸载限定到指定目录；测试全程使用临时目录。

## 使用方式

工程任务默认加载轻量路由，简单任务由主线程直接完成。显式使用也可以：

~~~text
$orchestrator 修复当前问题，遵守已有授权，完成必要验证后交付。
~~~

当有独立调查、兼容性核验或独立复核可以与主线程工作同时推进时，考虑并执行有收益的委派。没有独立交付物时留在主线程。

默认 3 个活跃子任务，中等任务通常新建 1 个，复杂回合通常新建 2 个，每阶段最多新建 6 个。运行时上限优先；创建预算是可配置保护值，不是已验证的最优策略。复用取决于问题域和上下文是否仍适用，没有“第三个位置只能复用”的限制。

遇到已经授权的登录修复，不因“涉及认证”再次暂停。授权不覆盖更换认证供应商、扩大权限或线上数据操作时，只暂停相关动作，继续其他已授权准备。可逆本身不是授权。

主线程和 Worker 共享目录时最多一个写入者；需要并行写入则隔离 worktree。用户中途改变约束时，识别受影响节点，使用现有中断/消息工具传播变化，接收结果时重新核对。没有实际中断能力时，不声称已停止外部动作。

## Full 交接与验收

Lite 用于普通低风险只读调查，不需要 JSON。Full 用于委派写入、执行检查、高风险分析、跨任务保存和依赖集成。主线程直接执行不需要生成协议文件。

Full schema 2 的权威定义在 skills/orchestrator/scripts/validate_context_contract.py：

~~~powershell
python -B skills/orchestrator/scripts/context_tool.py schema
python -B skills/orchestrator/scripts/context_tool.py --help
~~~

[完整命令示例](docs/full-handoff-example.md) 展示 prepare → ready → result → accept。执行检查用 run-check 记录真实命令、目录、退出码和输出摘要。请读取返回 JSON 的 exit_code；记录器成功退出不代表被记录的测试通过。

脚本生成默认字段、节点标识、摘要和工作区快照；主线程填写目标、范围、验收和风险。快照包含未提交文件内容和 Git 信息。协议及日志保存在被监测工作区外的 sidecar 目录，避免它们改变自己的基线或被打包。

写入前核对输入，回传时比较实际改动与自报文件，主线程验收时检查当前文件和证据对应状态。测试后再次改代码，旧测试不能证明新代码。历史失败可以保留为诊断记录；诊断验收可以预先指定非零退出码。

execution_status=completed 只表示执行结束。只有逐项验收满足、证据适用且主线程作出 accepted 决定，才算验收通过。不要把 standalone validator 的 VALID 当成项目通过验收。

这不是运行时沙盒：快照不证明改动者身份，不能监测数据库或网络，也不能证明人工证据的语义。显式排除的生成物/依赖目录不在监测范围内；排除项不能覆盖声明的输入或归属路径。路径摘要也不涵盖全部环境依赖，主线程仍须判断环境是否适用。未解释的并发改动会阻止自动验收，不会自动覆盖或删除。

更多协议细节见 [role-contracts.md](skills/orchestrator/references/role-contracts.md)。

## 升级与回滚

0.2.0 的 Full schema 与旧版不兼容，进行中的交接需要按新 schema 重新建立。不能用重建快照来掩盖未解释的改动。安装清单保持兼容，旧备份链不能覆盖。

先在更新后的仓库中预览卸载，再恢复旧文件；核对后重新安装所需选项：

~~~powershell
python -B scripts/uninstall.py --dry-run
python -B scripts/uninstall.py
python -B scripts/install.py --dry-run --apply-preset
python -B scripts/install.py --apply-preset
~~~

卸载发现 modified、missing 或备份损坏时停止，保留清单和备份，由用户先处理差异。不同安装方式之间也先卸载恢复，再重装，不用 --force 绕过。

## 验证与行为评测

~~~powershell
python -B scripts/validate.py
~~~

验证包含元数据与协议来源检查、TOML 回归、畸形输入、真实文件/日志证据、安装预览、重复安装、两种发现位置和卸载恢复。测试不会应用到当前用户的 Codex 配置。需要系统权限的检查会明确标记 skipped。

[行为评测方案](docs/behavior-evaluation.md) 将确定性回归与真实模型效果分开，比较原模型＋旧协议、Astra＋旧协议、Astra＋新协议，并保留单主线程对照。没有完成这些实测前，不宣称性能收益。

## 项目布局

- skills/orchestrator/：轻量入口、角色语义、Full 协议工具。
- agents/：调查与明确执行角色，模型映射可见。
- presets/：调度设置与显式模型迁移分开。
- scripts/：安装、卸载、配置合并、诊断和仓库验证。
- tests/：隔离目录中的确定性回归。
- docs/：可执行交接示例与行为评测方案。

插件清单只暴露 Skill；角色 TOML 与个人配置由安装器明确处理。没有内置 API 编排框架，也不会通过 Skill 文案启用客户端未提供的功能。

[MIT License](LICENSE) · [官方 Skills 文档](https://learn.chatgpt.com/docs/build-skills) · [官方 Subagents 文档](https://learn.chatgpt.com/docs/agent-configuration/subagents)
