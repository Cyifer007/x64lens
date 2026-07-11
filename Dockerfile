# x64lens development container
#
# Purpose:
#   Provide a reproducible Ubuntu-based build and test environment for the
#   NASM-first x64lens toolchain. This container is meant for development,
#   CI smoke checks, professor/reviewer reproduction, and future benchmark
#   harness validation.
#
# Permission model:
#   The image creates/uses an `ubuntu` user and switches to that user after
#   dependency installation. The Makefile Docker targets also pass the host
#   UID/GID at `docker run` time. This double layer prevents root-owned build
#   artifacts when the repository is bind-mounted from WSL2 or Linux.
#
# Important:
#   Final publication benchmarks should be run on a stable documented host
#   or clean VM, not assumed from a developer laptop container alone.

FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

# Install the baseline tools needed for local build/test parity.
# Optional comparison tools such as ROPgadget, Ropper, and ropr remain
# intentionally outside the image because publication baseline environments
# should record tool installation and versions explicitly.
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
       python3-jsonschema \
       time \
       unzip \
       zip \
    && rm -rf /var/lib/apt/lists/*

# Ubuntu 24.04 images commonly provide an `ubuntu` user. This fallback keeps
# the Dockerfile robust if that ever changes in a derivative image.
RUN if ! id -u ubuntu >/dev/null 2>&1; then useradd -m -s /bin/bash -u 1000 ubuntu; fi

WORKDIR /work
COPY . /work

# Validate repository shape at image build time. The full binary build is
# still performed by explicit `make` so developers see build errors directly.
RUN make scaffold-check \
    && chown -R ubuntu:ubuntu /work

USER ubuntu
ENV HOME=/home/ubuntu

CMD ["bash"]
