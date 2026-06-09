# Backlog

## Sprint 0 / Environment and context

- [x] Stand up WSL2 Ubuntu 24.04 or equivalent Linux development environment.
- [x] Verify NASM, binutils, gcc, make, python3, git, and time are installed.
- [x] Verify Docker/devcontainer build path.
- [ ] Keep VM images out of repository.

## Sprint 1

- [x] Implement file open/stat/mmap.
- [x] Implement ELF magic validation.
- [x] Validate ELF64 class.
- [x] Validate little-endian encoding.
- [x] Validate `EM_X86_64` machine type.
- [x] Print basic ELF header metadata.
- [x] Add invalid input tests.

## Sprint 1 follow-up hardening

- [x] Validate Sprint 1 implementation on WSL2 and Docker.
- [x] Write `docs/sprints/sprint-01-retro.md` after local validation.
- [x] Compare `x64lens info` against `readelf -h` using toy binaries and `/bin/ls`.
- [x] Add `tools/compare-readelf.sh` helper for repeatable side-by-side review.

## Sprint 2

- [x] Parse program headers.
- [x] Identify `PT_LOAD` segments.
- [x] Identify `PF_X` executable regions.
- [x] Create executable-region record model.
- [x] Detect `PT_GNU_STACK`.
- [x] Detect NX stack.
- [x] Detect executable stack.
- [x] Detect PIE.
- [x] Detect RWX load segments.
- [x] Detect baseline RELRO using `PT_GNU_RELRO`.
- [x] Detect dynamic linking using `PT_DYNAMIC`.
- [x] Add `x64lens mitigations <file>` command.
- [x] Add `minimal_execstack` toy corpus target.
- [x] Add malformed program-header rejection test.
- [x] Validate Sprint 2 implementation on WSL2 and Docker.
- [x] Compare mitigation findings against `readelf -l` for toy binaries and `/bin/ls`.
- [x] Write `docs/sprints/sprint-02-retro.md`.

## Sprint 2 follow-up hardening

- [ ] Automate `readelf` field comparison instead of side-by-side review.
- [ ] Add `checksec` comparison when available.
- [ ] Add `rabin2 -I` comparison when available.
- [ ] Add full RELRO detection through dynamic-section parsing.
- [ ] Add canary indicator detection through dynamic symbol or symbol-table parsing.
- [ ] Add section-header labels for executable regions.

## Sprint 3

- [x] Decide fixed candidate buffer vs immediate arena allocator for raw gadget candidates. Decision: fixed buffer first.
- [x] Implement fixed candidate record buffer.
- [x] Implement executable region scanner.
- [x] Detect `ret` terminators.
- [x] Detect `ret imm16` terminators.
- [x] Add bounded `--max-depth` option.
- [x] Extract bounded backward candidate windows.
- [x] Output raw candidates.
- [x] Add regression checks against `tests/bin/gadgets`.
- [x] Validate Patch 008 on WSL2 and Docker.
- [x] Add first scanner smoke benchmark harness.
- [x] Run first scanner smoke measurement and preserve generated TSV metadata.
- [x] Decide whether simple arena allocator lands in Sprint 3 Phase C or carries forward. Decision: implement in Phase C.
- [x] Add mmap-backed arena allocator for raw gadget candidate storage.
- [x] Validate arena-backed scanner path locally and in Docker.
- [x] Add exact byte-template pattern IDs.
- [x] Add exact pattern labels to `gadgets` output.
- [x] Add exact pattern count to scanner smoke benchmark output.
- [x] Update fixture validator for exact pattern matching.
- [x] Validate Patch 011 exact pattern matcher locally and in Docker.

## Sprint 4

- [x] Add initial exact pattern table. Completed early in Sprint 3 Phase D.
- [ ] Implement first real classifier routine in `src/classifier.asm`.
- [ ] Map exact pattern IDs into semantic classes.
- [ ] Classify `pop reg; ret` gadgets.
- [ ] Classify `leave; ret`.
- [ ] Classify `syscall`.
- [ ] Add register bitmap.
- [ ] Add primitive coverage summary.

## Sprint 5

- [ ] Add scoring model.
- [ ] Add JSON output.
- [ ] Add benchmark harness.
- [ ] Compare with ROPgadget.
- [ ] Compare with Ropper.
- [ ] Compare with ropr if available.

## Sprint 6

- [ ] Finalize README.
- [ ] Finalize architecture document.
- [ ] Finalize benchmark methodology.
- [ ] Produce final benchmark table.
- [ ] Produce paper outline.
- [ ] Produce final demo script.

## Local-only/private process backlog

Private context files, course-specific notes, and session-state tracking belong under `.local/project-context/` and are intentionally excluded from public commits.


## Sprint 7 through Sprint 12 candidate expansion

- [ ] Sprint 7: dynamic-section parsing for full RELRO, canary indicators, section labels, and external mitigation comparison helpers.
- [ ] Sprint 8: expanded primitive templates, multi-pop patterns, conservative register-transfer and memory templates, and larger fixture corpus.
- [ ] Sprint 9: compiler and hardening matrix corpus with reproducible build commands.
- [ ] Sprint 10: repeated research-grade baseline benchmarks against ROPgadget, Ropper, and ropr.
- [ ] Sprint 11: integrated `analyze` report with mitigation context, primitive coverage, scoring, JSON parity, and limitations.
- [ ] Sprint 12: IEEE paper draft, reproduction package, release-candidate artifacts, checksums, and extended-semester retrospective.

## Reviewer-readiness and future-proofing backlog

- [x] Add NASM rationale planning document.
- [x] Add decoder roadmap and future decoder seam.
- [x] Add raw/exact/semantic/scored metric boundary document.
- [x] Add parser safety and mutation smoke/fuzzing plan.
- [x] Add contributor maintainability planning document.
- [x] Add ADR for reviewer readiness and future seams.
- [ ] Add `make script-perms-check` to default scaffold validation. Patch 14 introduces this target.
- [ ] Add malformed-input mutation smoke harness in Sprint 7.
- [ ] Add automated readelf field comparison in Sprint 7.
- [ ] Add optional checksec comparison in Sprint 7.
- [ ] Add optional rabin2 comparison in Sprint 7.
- [ ] Add full RELRO detection through dynamic-section parsing.
- [ ] Add canary indicator detection through dynamic symbol or symbol-table parsing.
- [ ] Add section labels as analyst annotations, not runtime authority.
- [ ] Add public contributor guidance for pattern and semantic-class extension.
- [ ] Add optional C or Rust reference scanner only if benchmark ablation is needed.
- [ ] Keep ARM64 and non-ELF formats as future work unless the research scope changes.
