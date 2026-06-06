# x64lens development container
#
# Purpose:
#   Provide a reproducible Ubuntu-based build and test environment for the
#   NASM-first x64lens toolchain. This container is meant for development,
#   CI smoke checks, professor/reviewer reproduction, and future benchmark
#   harness validation.
#
# Important:
#   Final publication benchmarks should be run on a stable documented host
#   or clean VM, not assumed from a developer laptop container alone.

FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

# Install only the baseline tools needed for Sprint 1 through Sprint 3.
# Additional optional comparison tools such as ROPgadget, Ropper, ropr,
# checksec, radare2, or Ghidra helpers should be added intentionally later
# when benchmark methodology requires them.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       build-essential \
       binutils \
       ca-certificates \
       curl \
       gdb \
       git \
       gcc \
       make \
       nasm \
       python3 \
       time \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /work
COPY . /work

# Validate repository shape at image build time. The full binary build is
# still performed by explicit `make` so developers see build errors directly.
RUN make scaffold-check

CMD ["bash"]
