# Contributing

x64lens is currently a student research project and early-stage security tool. Contributions should preserve the research discipline, assembly-first learning goals, and safety constraints of the project.

## Contribution priorities

1. Correctness.
2. Parser safety.
3. Reproducibility.
4. Benchmarkability.
5. Modularity.
6. Performance.
7. Documentation.

## Development workflow

1. Open an issue for feature changes.
2. Link the change to a sprint goal or backlog item.
3. Keep assembly modules narrow and testable.
4. Update documentation contracts when behavior changes.
5. Add or update tests for new behavior.
6. Document limitations honestly.

## Coding rules

- Keep scanner logic separate from semantic classification.
- Keep reporting separate from analysis facts.
- Avoid direct string printing from deep parser modules after Sprint 2.
- Prefer internal records for data that will later feed JSON output.
- Validate all untrusted binary offsets and lengths.
- Do not add exploit payload generation to the baseline tool.

## Commit message style

Use concise, structured messages:

```text
area: short imperative summary
```

Examples:

```text
build: add nasm object build contract
elf64: validate header size before field reads
scanner: add ret terminator discovery skeleton
```
