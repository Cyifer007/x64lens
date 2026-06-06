# Security Policy

## Project scope

x64lens is a local binary analysis tool for authorized research, defensive binary triage, secure build validation, and educational reverse engineering.

The project does not support remote exploitation, payload delivery, unauthorized target scanning, or malware deployment.

## Supported versions

| Version | Supported |
| ------- | --------- |
| 0.1.x   | Development only |

## Reporting security issues

If you discover a vulnerability in x64lens itself, open a private security advisory if GitHub security advisories are enabled. If private advisories are unavailable, contact the maintainer directly before public disclosure.

## Parser hardening expectations

x64lens analyzes untrusted binaries. Every parser path must treat input as hostile.

Required safety rules:

- Validate every file offset before reading.
- Validate every size before arithmetic.
- Check for integer overflow before computing `offset + size`.
- Reject truncated headers.
- Reject impossible program header or section header counts.
- Never trust string table offsets.
- Never execute analyzed binaries.
- Prefer read-only mappings.

## Responsible use

Use x64lens only on binaries you are authorized to analyze.
