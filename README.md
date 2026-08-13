# Codex Team Orchestrator

一套可审计、可回滚的 Codex 多智能体配置：由主线程负责范围、架构、风险和最终验收，Terra 负责只读调查，Luna 负责边界明确的实现与测试。

> 非 OpenAI 官方项目，与 OpenAI 无隶属或背书关系。本项目不会保证节省 Token，也不会仅凭模型和多智能体配置保证项目达到生产级。

**English summary:** Codex Team Orchestrator is an unofficial, dependency-free configuration kit that makes orchestration available implicitly across software-engineering work, with read-only Terra discovery, bounded Luna implementation, safe presets, and reversible installation. Runtime model access, token usage, permissions, and concurrency remain account- and client-dependent.

## 它解决什么问题

```text
简单任务 ─────────────────────────────→ 主线程直接完成
独立只读调查 ─────────────────────────→ Terra Scout
明确范围的实现、修复、重构和测试 ─────→ Luna Worker
架构、安全、权限、支付和最终验收 ─────→ 主线程保留
所有编程场景 ─────────────────────────→ 隐式加载 orchestrator 路由
```

它提供四层能力：

- `skills/orchestrator/`：复杂工程的图状拆分、权限边界、集成和证据协议。
- `agents/`：`terra_scout` 与 `luna_worker` 的窄职责配置。
- `presets/`：匿名、可移植的安全配置和全局路由模板。
- `scripts/`：支持预览、备份、安装、冲突保护和卸载恢复的零依赖工具。

## 前提与限制

- 需要当前支持自定义 Agent 和 Skills 的 Codex 客户端。
- 示例模型为 `gpt-5.6-sol`、`gpt-5.6-terra` 和 `gpt-5.6-luna`；具体模型与推理档位是否可用取决于你的账户和运行时。
- 多智能体通常比单智能体消耗更多总 Token。它的主要价值是隔离上下文、缩短可并行工作的等待时间并增加独立验证，不是免费算力。
- 默认最多三个同时活跃的子智能体，不含主线程；普通一轮最多新建两个、单个交付阶段累计最多新建六个，达到预算后先集成和收口。
- Skill 默认允许在所有编程和软件项目场景中隐式触发；普通聊天不会主动进入工程编排。
- 隐式触发只代表加载路由规则，不代表每次都启动子智能体。简单任务仍由主线程直接完成。

## 快速安装

先克隆并验证：

```powershell
git clone https://github.com/DavidCai073/codex-team-orchestrator.git
cd codex-team-orchestrator
python scripts/validate.py
```

先预览，不写入任何文件：

```powershell
python scripts/install.py --dry-run
```

只安装 Skill 和两个 Agent，不修改你的 `config.toml` 或全局 `AGENTS.md`：

```powershell
python scripts/install.py
```

如果还希望合并推荐的权限、模型、并发和路由规则：

```powershell
python scripts/install.py --dry-run --apply-preset
python scripts/install.py --apply-preset
```

安装器会先备份被修改的文件，保留无关 TOML 键和已有 `AGENTS.md` 内容，并记录安装后的哈希。如果 Skill 或 Agent 目标位置已有不同文件，安装会停止；确认替换意图后才能使用 `--force`。

如果已经存在本工具的安装状态，而新命令与原安装方式不同，安装器会要求先卸载再重装；即使传入 `--force` 也不会覆盖原始备份链。

安装完成后完全重启 Codex。

### 从旧版本升级

新版不会覆盖旧安装的备份链。先使用更新后的仓库卸载旧版，再重新安装：

```powershell
git pull
python scripts/uninstall.py
python scripts/install.py --apply-preset
```

重新启动 Codex 后，隐式触发规则才会进入新会话。

## 使用

安装后，普通编程请求无需点名 Skill：

```text
帮我修复这个报错并运行相关测试。
```

Codex 会隐式加载 `orchestrator` 路由，再判断应由主线程直接完成，还是委派 Terra 调查或 Luna 执行。隐式触发是基于 Skill 描述的模型路由，不是保证每一轮都启动团队。

仍然可以显式调用完整工作流：

```text
$orchestrator 接手当前项目，先检查规则和代码，再推进到可运行、可验证阶段。
```

应用了 `AGENTS.example.md` 预设后，所有编程和软件项目请求都会遵循同一套路由协议。主线程会按任务性质选择只读调查或边界明确的实现角色；没有独立工作时仍应由主线程直接完成。

建议每个真实项目在仓库根目录维护项目级 `AGENTS.md`，至少写清：

- `run`、`build`、`test` 命令；
- 可观察的验收标准；
- 受保护的路径、数据和安全要求；
- 部署权限、备份和回滚方式。

全局路由只能分工，无法代替项目自己的“完成定义”。

## 效率与任务生命周期

这套配置把“同时运行上限”和“累计新建预算”分开：三个是运行时刹车，不是启动目标。简单任务不委派，中等任务通常只开一个，复杂任务通常最多新建两个；同职责优先复用已有 Agent。单个阶段累计新建六个后必须先集成、验证和形成检查点，不能继续接力开人。

聚焦任务默认使用新鲜上下文，由主线程在委派合同中重述目标、权限、文件归属和安全边界。这样可以减少把整段旧对话复制给每个 Agent，也能降低子智能体误读父级编排指令的概率。一个任务发生第二次上下文压缩后，应停止扩员，生成简短交接并换新任务继续。

为了避免“新鲜上下文”变成“缺少上下文”，写入、高风险、跨任务持久化或有依赖的合并才携带有版本号的 Full Context Capsule：目标、验收标准、已确认决策及证据、明确不做的内容、接口与依赖、文件归属、安全边界、已知失败和待决问题。普通低风险只读使用紧凑的 Lite Task Envelope（角色、目标、范围与不做项、`permission=read-only`、证据要求、交付物和停止条件），不强制 JSON 或摘要校验。需要升级时，Terra 或 Luna 必须先确认收到的版本，并把上下文标记为 `sufficient`、`missing_context`、`stale_context` 或 `contradictory_context`；只有 `sufficient` 才能继续，其余状态在写入前停手。

完整胶囊任务完成后，子智能体只返回 State Delta：结论、证据、修改文件、检查结果、新事实、失效假设和待决问题。主线程核验后才合并，并在实质状态变化后递增版本。它不会消除摘要误差，只能在流程被遵守时帮助暴露部分漏传、旧信息和身份不匹配。

写入型、高风险或跨任务持久化的交接还可以使用随 Skill 安装的零依赖校验器：

```powershell
python skills/orchestrator/scripts/validate_context_contract.py --kind capsule --file capsule.json --expected-version 3
python skills/orchestrator/scripts/validate_context_contract.py --kind delta --file delta.json --capsule-file capsule.json --expected-version 3
```

普通低风险只读调查只做 Lite 内联握手，不强制产生 JSON 文件，避免验证本身拖慢任务。

校验器只检查协议结构、版本、身份和摘要绑定；它不是 Codex 原生的 pre-spawn/pre-merge gate，不能证明证据结果语义真实，也不能覆盖运行时的实时权限。

这些规则不能让 `ultra` 获得与低推理档位相同的响应速度，但能避免重复调查、历史 Agent 累积和无效上下文复制。

## 手动安装

如果不使用脚本：

1. 将 `skills/orchestrator/` 复制到 `$CODEX_HOME/skills/orchestrator/`（未设置 `CODEX_HOME` 时通常是 `~/.codex/skills/orchestrator/`）。旧版 `~/.agents/skills/orchestrator/` 仅由卸载器兼容恢复，不再作为新安装目标。
2. 将 `agents/*.toml` 复制到 `~/.codex/agents/`，或放入项目的 `.codex/agents/`。
3. 按需把 `presets/config.example.toml` 中的设置合并到 `~/.codex/config.toml`。
4. 按需把 `presets/AGENTS.example.md` 合并到 `~/.codex/AGENTS.md`。
5. 重启 Codex。

不要直接覆盖已有配置。Windows 示例中的 `[windows] sandbox = "elevated"` 被注释掉，因为它只适用于 Windows；它表示更强的 Windows 原生沙盒实现，不等于 `danger-full-access`。

## 自定义模型与成本

配置都是可见默认值：

- 日常主线程：Sol `high`；
- 默认子智能体：Terra `medium`；
- 只读调查：Terra `medium`；
- 困难且明确的执行任务：Luna `max`；
- 子智能体硬上限：3。

如果账户没有这些模型，修改 `agents/*.toml` 和 `presets/config.example.toml`。若更关心额度，可降低 Luna 推理档位或只在困难实现中调用它。不要宣称修改后一定更省 Token，应以真实任务观察为准。

## 权限与安全

推荐默认值是：

```toml
approval_policy = "on-request"
sandbox_mode = "workspace-write"
approvals_reviewer = "user"
```

子智能体会受到当前会话实际权限的影响。不要依赖 Agent 文件里的文字约束来弥补主线程的全盘权限，也不要把 `danger-full-access + never` 当作日常默认。

安装器不会读取或上传密钥，不会复制本机完整配置，也不会包含项目历史、插件状态、Hook 状态或个人绝对路径。卸载前若检测到安装后的文件被修改，会停止而不是覆盖你的新改动。

## 卸载

先预览：

```powershell
python scripts/uninstall.py --dry-run
```

确认后卸载并恢复安装前备份：

```powershell
python scripts/uninstall.py
```

如果卸载报告 `modified` 或 `missing`，表示文件在安装后发生了变化。工具会保留安装状态和备份，等待你手动核对，不会强制删除。

## 验证

```powershell
python scripts/validate.py
```

验证覆盖插件 JSON、Skill 元数据、TOML、Context Capsule 握手、State Delta 回传、隐私模式、占位符、禁止打包的 Python 编译缓存，以及临时目录中的 dry-run、安装、重复安装和卸载恢复闭环。

## Plugin 说明

仓库包含有效的 `.codex-plugin/plugin.json`，因此 `orchestrator` Skill 可以作为 skills-only Plugin 打包。当前推荐仓库安装器，是因为自定义 Agent TOML 和用户配置预设不应由 Plugin 静默覆盖。提交到公共 Plugin 目录属于后续发布流程，不包含在 GitHub `v0.1.2` 中。

## 官方资料

- [Build skills](https://learn.chatgpt.com/docs/build-skills)
- [Build plugins](https://learn.chatgpt.com/docs/build-plugins)
- [Subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents)
- [AGENTS.md](https://learn.chatgpt.com/docs/agent-configuration/agents-md)
- [Sandboxing](https://learn.chatgpt.com/docs/sandboxing)
- [Windows sandbox](https://learn.chatgpt.com/docs/windows/windows-sandbox)

## License

[MIT](LICENSE) © 2026 DavidCai073
