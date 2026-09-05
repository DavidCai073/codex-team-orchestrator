# Project Instructions

## Goal

Build and publish a small, auditable Codex team-orchestration kit. It packages one orchestration Skill, two custom agent profiles, safe configuration templates, and reversible installation tooling.

## Scope

- Keep the plugin and installer dependency-free.
- Support Windows, macOS, and Linux when the Python standard library is sufficient.
- Treat `config.toml` and global `AGENTS.md` as user-owned files.
- Keep model names and reasoning efforts visible and easy to customize.
- Keep Lite / Full as the only delegated handoff formats. Direct root work needs neither.
- The root may perform difficult implementation; delegation must have an independent deliverable.
- Preserve existing model choices unless the user explicitly selects a model preset.

## Safety

- Never include personal absolute paths, tokens, credentials, logs, caches, plugin state, project history, or machine identifiers.
- Never overwrite an existing user file without a backup and an explicit install option.
- Installation must support a dry run and record enough state for a safe uninstall.
- Uninstall must not erase files that changed after installation.
- Default permissions must remain `workspace-write` with `on-request` approvals.
- Config merges must prove target values and preservation of every unmanaged semantic value before writing. Reject unsupported TOML layouts without partial installation.
- Repository development does not authorize installation into the active user's configuration or a Git push.

## Structure

- `.codex-plugin/`: plugin manifest.
- `skills/orchestrator/`: reusable orchestration Skill and direct references.
- `agents/`: custom Codex agent TOML files.
- `presets/`: sanitized configuration and instruction templates.
- `scripts/`: installer, uninstaller, and deterministic validation.
- `tests/`: deterministic regressions using disposable workspaces and homes.
- `docs/`: protocol decisions and reproducible behavior-evaluation instructions.
- Keep task capsules, command logs, and workspace inventories outside the monitored workspace; never package them.

## Run, build, test, and acceptance

- Run: `python -B scripts/install.py --dry-run` or `python -B scripts/doctor.py --help`.
- Build: no compilation or third-party dependencies; Python 3.11 or newer is required.
- Test: `python -B scripts/validate.py` (includes unit regressions and isolated installation cycles).
- Acceptance: array tables and multiline strings survive config merging; unselected models stay unchanged; contracts reject malformed payloads without crashing; actual workspace changes and input freshness are checked; acceptance remains a separate root decision backed by mapped evidence.
- Schema 2 handoffs replace schema 1 handoffs; regenerate in-flight capsules. Keep legacy installation manifests uninstallable.
- Permission checks must reuse valid session authorization. Reversibility alone grants no authority.
- Run required and targeted checks once per relevant code state; broaden only for a concrete failure, changed dependency, or project requirement.

## Deploy and rollback

- Prepare reviewable local changes and an archive; publishing and changing the active Codex installation require their own authorization.
- Installer/uninstaller regressions must use explicitly isolated temporary homes and verify restoration.
- Preserve the installation backup chain, stop on externally modified files, and restore all successfully written files on an installation failure.
- State inventories and contract checks are retrospective evidence, not runtime sandboxes or proof of agent attribution.

## Validation

Run these before release:

```powershell
python scripts/validate.py
python scripts/install.py --dry-run --codex-home <temp-codex-home> --user-home <temp-user-home>
```

Validation must cover plugin JSON, Skill frontmatter, TOML parsing, required files, the Context Capsule handshake and State Delta contract, privacy-sensitive path patterns, install behavior, and uninstall restoration.

## Release

- Use semantic versioning beginning at `0.1.0`.
- Use an MIT license.
- Commit messages must be concise English.
- Only the root agent may initialize Git, create the GitHub repository, push, tag, or publish a release.
