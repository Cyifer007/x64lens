# Changelog

All notable public changes to x64lens will be documented in this file.

The project follows semantic versioning once the first public release is cut.

## [0.1.0-dev] - Unreleased

### Added

- Repository skeleton for an assembly-first ELF64 analysis research prototype.
- NASM build contract using `make`.
- CLI command contract for `info`, `mitigations`, `gadgets`, `analyze`, `bench`, and `version`.
- Documentation contracts for development, research, output, benchmark, and release discipline.
- Initial research questions RQ1, RQ2, and RQ3.
- Initial JSON schema draft.
- Sprint planning documents.
- Development environment plan for WSL2, Docker/devcontainer, remote development, and publication benchmarks.
- Visualization plan with Mermaid and Graphviz source diagrams.
- Human-readable comments across current assembly, config, script, and workflow scaffolding.
- `.devcontainer/devcontainer.json` for reproducible development environments.

### Changed

- Public documentation is now separated from local-only private project context.
- Local-only planning/context files are expected under `.local/project-context/` and excluded by `.gitignore`.
- Makefile scaffold checks now validate only public repository structure.

### Planned

- Sprint 1: implement file mapping and ELF64 header validation.
- Sprint 2: implement program header parsing, executable region discovery, and baseline mitigation reporting.
- Sprint 3: implement raw gadget candidate scanning.
