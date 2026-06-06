# Visualization and Code Understanding Plan

## Recommendation

Use diagrams-as-code in Sprint 1. Do not build a heavy visualization pipeline yet.

The project should maintain two visual layers:

1. **Architecture diagrams:** stable module-level diagrams that explain how data flows through the analyzer.
2. **Implementation flow diagrams:** smaller command-level diagrams that explain one command path at a time, such as `x64lens info <file>`.

## Why diagrams-as-code

Diagrams-as-code keeps the visuals reviewable in Git, easy to update, and easy to include in documentation or a paper later. The first choices are Mermaid and Graphviz DOT.

## Sprint 1 visualization scope

Create and maintain:

- `docs/diagrams/architecture-flow.mmd`
- `docs/diagrams/info-command-flow.mmd`
- `docs/diagrams/module-graph.dot`

Do not attempt full automatic assembly control-flow reconstruction in Sprint 1. That is a rabbit hole. Once the binary becomes more complex, use `objdump`, GDB, Ghidra, or radare2 to inspect compiled paths.

## Recommended workflow

- Maintain Mermaid diagrams beside the documentation.
- Preview Mermaid in GitHub Markdown or VS Code.
- Use Graphviz only when a static module dependency graph is useful.
- Add screenshots only for papers or presentations, not as the source of truth.

## Future AI-assisted visualization

AI can help summarize code paths, propose diagrams, and compare implementation against architecture contracts. However, the canonical source should remain the Markdown, Mermaid, DOT, and source code in the repository.

## Future tooling candidates

- Mermaid for architecture and command flow.
- Graphviz DOT for module dependency graphs.
- Ghidra for reverse engineering compiled `x64lens` binaries.
- radare2 for control-flow graphs and disassembly inspection.
- GDB for runtime trace validation.
- Doxygen only if a useful convention emerges for NASM comments, not as a Sprint 1 dependency.
