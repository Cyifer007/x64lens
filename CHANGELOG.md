# Changelog

All notable changes to x64lens will be documented in this file.

The project follows semantic versioning once the first public release is cut.

## [0.1.0-dev] - Unreleased

### Added

- Repository skeleton for the CSC-732 assembly-first ELF64 analysis project.
- NASM build contract using `make`.
- CLI command contract for `info`, `mitigations`, `gadgets`, `analyze`, `bench`, and `version`.
- Documentation contracts for development, research, output, benchmark, and release discipline.
- Initial research questions RQ1, RQ2, and RQ3.
- Initial JSON schema draft.
- Sprint 1 and Sprint 2 planning documents.

### Planned

- Sprint 1: implement file mapping and ELF64 header validation.
- Sprint 2: implement program header parsing, executable region discovery, and baseline mitigation reporting.
- Sprint 3: implement raw gadget candidate scanning.

## 0.1.0-dev context update

### Added

- Project context persistence files: `PROJECT_CONTEXT.md` and `PROJECT_STATE.md`.
- CSC-773 integration documentation.
- Development environment plan for WSL2, Docker/devcontainer, Codespaces/Codex, and publication benchmarks.
- Visualization plan with Mermaid and Graphviz source diagrams.
- Context persistence and comment/documentation contracts.
- Human-readable comments across current assembly, config, script, and workflow scaffolding.
- `.devcontainer/devcontainer.json` for reproducible development environments.

### Changed

- README now documents the dual CSC-732 and CSC-773 deliverable model.
- Sprint 1 now explicitly includes environment setup, context persistence, and comment/documentation hygiene.
- Makefile scaffold check now validates core context and documentation files.
