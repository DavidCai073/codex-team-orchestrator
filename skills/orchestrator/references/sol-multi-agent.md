# Execution principles

This legacy filename contains model-independent guidance. The root is a hands-on engineer and the integration owner, not a dispatcher that must outsource all implementation.

## Independence and ownership

A delegated node needs an independent deliverable, bounded ownership, dependencies and evidence. Parallel discovery or independent review can be useful even when only one implementation stream is safe. Complete upstream decisions before dependent implementation; integrate before final acceptance. Do not create roles solely to fill a roster.

Keep one writer per owned file set including the root. A scout may run while the root writes elsewhere, but its inputs must remain stable or its findings must be rechecked. The Full helper still monitors a complete workspace, so simultaneous Full writers need isolated worktrees. This stricter implementation limit does not forbid eligible independent Lite work. Snapshot checks cannot attribute a change to a process; reconcile unexplained changes without discarding them.

Use the selection rules in SKILL.md and the single Lite / Full definition in role-contracts.md. Simple root work needs neither. Never turn every focused lookup into Full by applying a broad statement from a reference file.

## Node state and authority

capsule_version belongs to one stage_id/node_id contract. Global stage revision and another node's completion do not invalidate it. Compare the actual input and interface dependencies. If a constraint changes, increment affected node versions and send updates or interrupt through available tools before further affected actions. Revalidate late results. Sending an update does not revoke an already executed external operation.

The current helper conservatively rejects unexplained workspace changes outside ownership. For independent writers use isolated worktrees. For already reviewed unrelated changes the root may reconcile manually with the original evidence, refresh only affected checks, and create a new root review; do not silently rebase a capsule or regenerate hashes to conceal an unexplained edit.

After compaction, recover goal, authorizations, node versions, file baseline, pending work, accepted evidence and open issues. Resume recoverable work. Escalate only unresolved facts that block a concrete action. Prefer fresh child contexts; reuse a child only when its assumptions and domain remain applicable.

## Failures

- unavailable: use one closest supported runtime role or sequential execution, preserving scope and evidence requirements. Report the substitution.
- task_failure: retain evidence and return to the root for replanning; do not automatically retry a failed task or failing test.
- permission_boundary: stop the affected action. A different role or tool is not permission.
- invalid_scope: stop and report the mismatch before writing.

The root supplies discoverable missing inputs. User questions are reserved for material decisions or authority that cannot be resolved from available context.

## What verification proves

A digest identifies JSON or file content. It does not authenticate the author or prove a test's meaning. The local helper records argv, cwd, exit code, output hashes and file-state hashes; a party able to edit all records can forge them. Runtime sandboxing and root evidence review remain necessary.

Inventories cover regular files and symlinks, excluding .git metadata and explicitly declared generated/vendor paths. They capture uncommitted content as well as Git HEAD/dirty paths. They do not monitor network activity, databases, environment secrets, empty directories, or every permission bit. Watched symlinks are refused; snapshots are not atomic and a reverted intervening edit may be invisible. Use stable workspaces, no overlapping writers, and platform checks appropriate to the task.

Acceptance maps every criterion to evidence. A diagnostic task may expect a nonzero exit; freeze that expectation before execution. Historical failing checks may be retained, but only applicable final-state evidence may satisfy acceptance. Root manual judgments remain judgments; the helper cannot prove the semantics of a manual inspection.

Code-state hashes and the helper's Python/platform signature do not fingerprint every dependency, executable, external service or environment variable. The root must also assess environment applicability before reuse. Once required checks pass and no concrete concern remains, finish.
