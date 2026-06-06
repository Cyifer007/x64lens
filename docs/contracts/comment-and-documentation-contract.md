# Comment and Documentation Contract

## Purpose

x64lens is a learning project, a research artifact, and a production-oriented security tool. Human-readable comments and documentation are therefore first-class deliverables.

## Code comment requirements

Every assembly file must include:

- file purpose,
- sprint phase or roadmap role,
- public symbols exported by the module,
- expected inputs and outputs for implemented routines,
- register clobber notes where practical,
- safety assumptions,
- next-step notes for placeholders.

## Config comment requirements

Every config file should explain:

- why the file exists,
- what workflow consumes it,
- which dependencies or assumptions it encodes,
- what should be updated later.

## Documentation requirements

Markdown files are maintained with the same seriousness as code. If code behavior changes, update relevant documentation in the same commit or sprint.

## Implementation response requirement

Every implementation update should include:

- what changed,
- how to build,
- how to test,
- expected output,
- what to do next if tests pass,
- what to inspect if tests fail.

## Review rule

Before each two-week checkpoint, review:

- active sprint plan,
- active sprint retrospective,
- active local project state, when maintained outside the public repo,
- `docs/backlog.md`,
- touched source files,
- touched contracts.
