# Role contracts

Use one contract per delegated node. Keep prompts narrow and retain the returned evidence.

## Generic contract

```text
Role: <role_id>
Node: <node_id>
Objective: <one concrete objective>
Inputs: <paths, facts, or completed nodes>
Dependencies: <completed nodes or none>
Confirmed facts: <facts with evidence>
Constraints: <scope, safety, and runtime limits>
Permission: read-only | scoped-write | execute-checks
Owned paths: <paths or none>
Forbidden actions: no credentials, destructive operations, dependency installation, or scope expansion
Deliverable: status, findings, evidence, assumptions, risks, changed_files, checks, recommended_next_node
Stop conditions: missing input, overlapping ownership, approval gate, or contradictory evidence
```

## Terra Scout

Read project rules and relevant files, locate implementation and tests, and report paths and commands. Do not edit, create, delete, rename, install, or make product, security, permission, or destructive decisions.

## Luna Worker

Implement only the assigned node in the owned paths. Read applicable rules first, preserve unrelated edits, run the narrowest meaningful checks, and return exact changed files and verification output. Stop if an interface, dependency, permission, or acceptance decision must change.

## Root manager

Own the graph, authority ledger, user decisions, integration, conflict resolution, acceptance mapping, and final report. Never delegate final claims without reviewing evidence.
