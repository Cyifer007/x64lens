# Dev Container Notes

This directory defines the optional VS Code/GitHub Codespaces development container.

JSON does not support comments, so this README documents the intent:

- use the repository `Dockerfile`,
- mount the project at `/work`,
- install useful VS Code extensions for C/C++, Markdown, and Mermaid diagrams,
- run `make scaffold-check` after container creation.

This environment is for development and reproducibility checks. Final publication benchmarks should be run on a stable documented host or clean VM.
