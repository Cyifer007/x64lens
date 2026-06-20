# Parser Regression Fixtures

This directory stores minimized, reviewed inputs that reproduce a parser defect.

A committed fixture must document:

- the malformed field or range,
- the original failure mode,
- the stable expected exit code after the fix,
- the commands that exercise the regression,
- whether the issue affected native, Docker, or both environments.

Generated mutation campaigns do not belong here. Only durable regressions that protect a specific fix should be committed.

## Current fixtures

### `elf64-shentsize-63.bin`

- Size: 128 bytes.
- SHA-256: `44333510c037c8addf46cd1fc76754b91b421fb82e36fa6a9f6d56324cef6e97`.
- Defect: the ELF64 validator previously accepted any nonzero `e_shentsize` when `e_shnum` was nonzero.
- Risk: future section-table iteration could treat an invalid 63-byte stride as safe.
- Fixed behavior: reject the file as malformed with exit code `5` before section parsing.
- Exercised commands: `info`, `mitigations`, `gadgets`, and `analyze`.
- Validation environments: native and Docker through the normal regression suite.
