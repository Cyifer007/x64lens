# Enterprise Adoption Plan

## Adoption principles

Enterprise adoption requires stability, safety, and automation compatibility.

## Required capabilities

- Stable CLI.
- Stable exit codes.
- JSON output.
- Versioned schema.
- Containerized build environment.
- Release checksums.
- Documentation.
- Security policy.
- Non-proprietary test corpus.

## Future enterprise integrations

- GitHub Actions.
- GitLab CI.
- Jenkins.
- SARIF output.
- Jira enrichment.
- Vulnerability management enrichment.
- SIEM ingestion.

## Enterprise guardrails

- Do not upload proprietary binaries to public benchmark results.
- Do not emit exploit payloads.
- Do not scan remote systems.
- Clearly mark heuristic outputs.


## Environment distribution model

Enterprise users should not need a VM image. The preferred distribution model is:

1. Source repository with Makefile.
2. Dockerfile/devcontainer for reproducible builds.
3. GitHub Actions or GitLab CI examples.
4. Signed release binary and checksum in future releases.
5. Versioned JSON schema.

## Production-readiness gates

Before any `1.0.0` release, require:

- parser fuzz testing,
- malformed corpus testing,
- stable CLI contract,
- stable JSON schema,
- release checksum generation,
- reproducible benchmark results,
- documented safety boundaries.
