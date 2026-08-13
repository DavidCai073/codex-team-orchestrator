# Project Instructions

## Goal

Build and publish a small, auditable Codex team-orchestration kit. It packages one orchestration Skill, two custom agent profiles, safe configuration templates, and reversible installation tooling.

## Scope

- Keep the plugin and installer dependency-free.
- Support Windows, macOS, and Linux when the Python standard library is sufficient.
- Treat `config.toml` and global `AGENTS.md` as user-owned files.
- Keep model names and reasoning efforts visible and easy to customize.

## Safety

- Never include personal absolute paths, tokens, credentials, logs, caches, plugin state, project history, or machine identifiers.
- Never overwrite an existing user file without a backup and an explicit install option.
- Installation must support a dry run and record enough state for a safe uninstall.
- Uninstall must not erase files that changed after installation.
- Default permissions must remain `workspace-write` with `on-request` approvals.

## Structure

- `.codex-plugin/`: plugin manifest.
- `skills/orchestrator/`: reusable orchestration Skill and direct references.
- `agents/`: custom Codex agent TOML files.
- `presets/`: sanitized configuration and instruction templates.
- `scripts/`: installer, uninstaller, and deterministic validation.

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
