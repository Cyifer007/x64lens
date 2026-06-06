# Dev Container Notes

This directory defines the optional VS Code/GitHub Codespaces development container.

JSON does not support comments, so this README documents the intent:

- use the repository `Dockerfile`,
- mount the project at `/work`,
- run as the non-root `ubuntu` user,
- let VS Code update the remote user UID where supported,
- install useful VS Code extensions for C/C++, Markdown, and Mermaid diagrams,
- run `make scaffold-check` after container creation.

The non-root user choice is important. Running build/test commands as root inside a bind-mounted repository can create root-owned files that WSL/Linux cannot later delete with `make clean`.

This environment is for development and reproducibility checks. Final publication benchmarks should be run on a stable documented host or clean VM.
