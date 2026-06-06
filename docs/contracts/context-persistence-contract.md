# Context Persistence Contract

## Purpose

This contract prevents drift across chat sessions, coding sessions, sprint check-ins, and research-paper iterations.

## Canonical context files

The canonical high-level context files are:

- `PROJECT_CONTEXT.md`
- `PROJECT_STATE.md`
- `docs/project-charter.md`
- `docs/architecture.md`
- `docs/csc-773-integration.md`
- `docs/contracts/development-contract.md`
- `docs/contracts/research-contract.md`
- `docs/contracts/output-contract.md`
- `docs/contracts/release-contract.md`

## Update triggers

Update the project context when any of the following changes:

- course deliverable mapping,
- active sprint status,
- architecture decisions,
- CLI command behavior,
- JSON schema behavior,
- scoring model,
- semantic taxonomy,
- mitigation interpretation,
- benchmark methodology,
- publication strategy,
- safety/ethics boundaries.

## Session-start rule

At the start of a major new chat session, review or upload:

- `PROJECT_CONTEXT.md`,
- `PROJECT_STATE.md`,
- the active sprint plan,
- the relevant contract files.

## Session-end rule

At the end of any meaningful implementation or planning session, update:

- `PROJECT_STATE.md`,
- `docs/backlog.md`,
- the active sprint plan or retrospective,
- any contract affected by the session.

## Anti-drift rule

Do not implement a feature merely because it is interesting. Every new feature must map to at least one of:

- sprint acceptance criteria,
- research question,
- benchmark methodology,
- enterprise adoption requirement,
- long-term architecture seam.
