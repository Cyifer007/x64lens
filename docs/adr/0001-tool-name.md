# ADR 0001: Tool Name

## Status

Accepted for initial development.

## Decision

Use `x64lens` as the repository and executable name.

## Rationale

The first research target is ELF64 x86_64 Linux binary analysis. The name `x64lens` communicates that initial scope clearly.

## Alternatives considered

| Name | Decision | Reason |
| ---- | -------- | ------ |
| `x64lens` | Accept | Clear, specific, professional, aligned with first target |
| `x86lens` | Reject | Ambiguous because x86 often implies 32-bit as well as the broader family |
| `x64semlens` | Reject | Too long and awkward |
| `binlens` | Reject | Too broad and collides conceptually with an existing commercial binary analysis product |
| `binsemlens` | Reject | Descriptive but clunky and less memorable |
| `exploitlens` | Reject | Too weaponized for enterprise and academic adoption |
| `explens` | Reject | Short but unclear |

## Consequences

The name constrains the first public identity to x86_64. That is acceptable because the project should become excellent at one architecture before generalizing.

If the tool becomes multi-architecture later, there are two options:

1. Keep `x64lens` as the original engine and create a broader umbrella project.
2. Keep the brand and add architecture modules despite the original name.

The project will document this choice rather than hiding it.
