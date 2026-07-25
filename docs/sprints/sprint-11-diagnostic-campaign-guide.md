# Sprint 11 Diagnostic Campaign Operator Guide

## Purpose

This guide explains how to regenerate the provisional corpus, execute the
Sprint 11 diagnostic campaign, verify the resulting evidence, and interpret the
outputs without overstating performance or gadget coverage.

The campaign is development evidence:

```text
evidence_class: diagnostic
frozen: false
publication_eligible: false
```

It may guide Sprints 12 through 14. It is not part of the Sprint 15-frozen
preview or publication dataset.

## 1. Host preparation

Run the repository inventory first:

```bash
make doctor
make corpus-tools-check
REQUIRE_BASELINES=1 make baseline-tools-check
```

The normal development toolchain includes NASM, GNU binutils, GCC, Clang,
GNU Make, Python 3 with `jsonschema`, Git, ZIP tools, and GNU time. Strict sprint
acceptance also uses ShellCheck and Docker. The exact comparison campaign uses:

```text
ROPgadget 7.7
Ropper 1.13.13
ropr 0.2.26
```

Install the repository-supported development dependencies with:

```bash
make install-dev-deps-ubuntu
```

Python baselines are normally installed in isolated environments:

```bash
pipx ensurepath
export PATH="$HOME/.local/bin:$PATH"
pipx install --force 'ROPGadget==7.7'
pipx install --force 'ropper==1.13.13'
```

`ropr` requires a sufficiently current Rust toolchain:

```bash
make install-rustup-user
. "$HOME/.cargo/env"
cargo install ropr --version 0.2.26 --locked
export PATH="$HOME/.cargo/bin:$PATH"
```

`REQUIRE_BASELINES=1` rejects an environment with no baseline tools; it does
not by itself require all three. Confirm all three exact executables and
versions before collecting all-tools evidence:

```bash
command -v ROPgadget ropper ropr
ROPgadget --version
ropper --version
ropr --version
REQUIRE_BASELINES=1 make baseline-tools-check
```

Optional diagnostic tools such as `strace` and `perf` help investigate process,
system-call, and scheduler behavior, but they are not runtime dependencies and
do not replace the campaign's own authenticated rows. A writable cgroup v2
hierarchy is useful for later process-tree RSS calibration. Some virtualized
Linux environments do not expose that control surface; record that as an
environment limitation instead of silently changing the RSS definition.

## 2. Freeze the source under test

Before building the corpus or running the campaign:

```bash
git rev-parse HEAD
git status --short
git diff --check
```

Use a clean tracked tree. Record the commit and do not rebuild or edit the
analyzer while a campaign is running. The runner deliberately rejects source
or retained-artifact drift.

## 3. Build and verify the analyzer

```bash
make normalize-perms
make clean
make
make samples
make test
```

A valid build should report:

```text
tests: ok
```

The capacity and malformed-input contracts remain independent acceptance gates:

```bash
make capacity-smoke
MALFORMED_TIMEOUT=2 make malformed-smoke
```

Expected behavior includes a complete 4,096-candidate report and exit code `6`
with empty stdout when a 4,097th candidate would be required.

## 4. Regenerate the provisional corpus

Remove only a recognized provisional corpus, then rebuild and verify it:

```bash
make clean-provisional-corpus
make provisional-corpus-build
make provisional-corpus-verify
```

The generated corpus contains 24 ELF64 x86_64 targets:

```text
2 compilers
x 2 optimization levels
x 3 requested linkage or role profiles
x 2 hardening profiles
= 24 targets
```

Requested PIE and shared-object roles are build intents until Sprint 12 adds the
bounded loader evidence needed to classify them independently.

## 5. Run the complete provisional campaign

Use a new UTC-stamped identifier. Never reuse an existing result identifier:

```bash
campaign="s11-p061-local-$(date -u +%Y%m%dT%H%M%SZ)"
S11_P060_CAMPAIGN_ID="$campaign" \
REQUIRE_BASELINES=1 \
make bench-sprint11-provisional-campaign
```

The tracked authority accounts for 30 conditions:

```text
6 selected targets x 4 comparison tools = 24 comparative conditions
6 independent x64lens analyze controls   =  6 control conditions
                                                30 total
```

The command prints the final result path. Save the campaign identifier and do
not edit the result tree.

## 6. Verify the retained evidence

Set the result path from the identifier used above:

```bash
result="benchmarks/results/diagnostic/$campaign"
python3 tools/verify-checksum-manifest.py "$result/SHA256SUMS.txt"
python3 -m json.tool "$result/manifest.json" >/dev/null
python3 -m json.tool "$result/condition-accounting.json" >/dev/null
python3 -m json.tool "$result/summaries/task-summary.json" >/dev/null
python3 -m json.tool "$result/engineering-gap-register.json" >/dev/null
```

Review the retained condition identities:

```bash
column -s $'\t' -t "$result/condition-accounting.tsv" | less -S
less "$result/summaries/task-summary.md"
less "$result/engineering-gap-register.md"
```

A complete all-tools run should account for all 30 conditions, retain warmups
and measured rows, produce the expected normalized relation artifacts, record
runtime-closure status for each tool scope, and retain an explicit coordinate
qualification state.

## 7. Read the result in evidence-layer order

### 7.1 Native execution status

Start with `condition-accounting.tsv`.

`status` describes native execution and timing eligibility:

- `success`: at least one measured row is eligible for the diagnostic summary;
- `below_timer_floor`: process execution succeeded, but the single-run duration
  is below the reliable floor;
- `unavailable_tool`: the exact baseline was not available;
- other failure states preserve nonzero exit, timeout, signal, extraction, or
  integrity failures.

A below-floor result is not zero runtime. It means the method cannot resolve a
stable single-run estimate for that condition.

### 7.2 Comparison qualification

`comparison_status` is separate from native success. A process can run
successfully while its cross-tool comparison remains blocked by:

- normalization failure;
- partial runtime closure;
- coordinate mismatch;
- insufficient positive relation evidence;
- a relation that is not applicable to that control condition.

Do not treat native success as proof that the comparison is qualified.

### 7.3 Tool-native records

Each baseline's native record total is tool-specific. Differences can result
from terminator policy, alignment, instruction depth, canonicalization,
duplicate handling, filtering, and output scope. They are not a common gadget
population and must not be renamed to an unlabeled `gadget_count`.

### 7.4 Normalized relations

The initial normalized relation is a narrow exact represented-text relation.
A zero result means only that the selected exact relation was absent under that
tool's retained native output and the adapter contract. It does not mean the
binary has no useful gadgets, that a tool failed, or that two discovery models
have equivalent coverage.

### 7.5 Address coordinates

Cross-tool address intersections require positive role-controlled anchors for:

```text
ET_EXEC
PIE-intended ET_DYN
shared-object-intended ET_DYN
```

`mismatch`, `insufficient_relation_evidence`, or `mixed_or_ambiguous` blocks an
address-level coverage comparison. Do not infer address agreement from an empty
intersection.

### 7.6 Runtime closure

A `complete` runtime closure means the bounded task-path observation resolved
its declared interpreter, imported Python package or module evidence, and native
ELF dependency closure. It is not a universal statement about every future
invocation. `partial` or failed closure status blocks dependency-surface
comparison for that tool until corrected.

### 7.7 Engineering priorities

The engineering gap register may select a roadmap item only when the retained
facts identify a concrete unresolved capability or method question. Diagnostic
selection is not implementation acceptance and does not convert the observation
into a release claim.

## 8. Timer-floor interpretation and refinement

The reliable floor is measured, not chosen to make a desired result appear.
Reducing its multiplier without new calibration would weaken the method rather
than improve it.

Use this order when a condition is below the floor:

1. prefer a larger target performing the same task;
2. reduce avoidable host noise and use fixed CPU affinity when available;
3. use the preregistered whole-batch protocol;
4. retain the condition as below-floor when the protocol cannot qualify it.

The Sprint 11 whole-batch protocol is
`preregistered_not_yet_executed`. It evaluates:

```text
batch sizes K: 2, 4, 8, 16, 32, 64
minimum counterbalanced batches per K: 9
required whole-batch median: at least 5 x the measured floor
maximum MAD / median: 0.10
comparison rule: same K only
```

A batch is the measurement unit. Do not divide its elapsed time into a claimed
single-run latency. A qualified batch may support a separately labeled
exploratory throughput value such as `K / batch_elapsed_time`; that value is not
single-run evidence.

## 9. Interpreting the Sprint 11 diagnostic observations

Keep the two retained evidence strata separate. The cloud checkpoint accounted
for 30 planned conditions while executing the 12 available x64lens conditions
and retaining 18 pinned-baseline conditions as unavailable. A later,
separately qualified WSL2 replay used the exact pinned baselines and, after one
narrow evidence-local correction to the ROPgadget 7.7 banner authority,
executed 30 of 30 conditions, retained 180 successful process rows, and
generated 24 normalized relations.

The WSL2 replay established these bounded observations:

- 17 conditions were above the 6,361,100 ns reliable single-process floor and
  13 were below it;
- all 12 x64lens gadget and analyze conditions remained below that host's
  6,361,100 ns reliable single-process floor;
- baseline-native record totals differed substantially across tools;
- the first selected exact relation was absent across the selected targets;
- exact-only `pop rbp; ret` evidence appeared consistently in x64lens reports;
- coordinate qualification lacked a positive anchor;
- the initial Python baseline closure method lost isolated-environment context,
  leaving two baseline closures incomplete; and
- coordinate calibration failed, so the replay was not comparison-qualified.

The strongest conclusion is methodological: the runner and task definitions
successfully exposed where performance, coverage, address, and dependency
questions were not yet identifiable. The observations do not prove universal
speed leadership, lower RSS, equivalent gadget coverage, or baseline defects.
Both evidence strata remain diagnostic, unfrozen, and publication-ineligible;
the WSL2 replay does not replace the fresh unmodified Patch 061 campaign.

## 10. Next evidence steps

After applying Patch 061 and before empirical acceptance:

1. run a fresh exact 30-condition campaign without authority edits;
2. require five complete task-path runtime closures;
3. require positive coordinate anchors before address intersections;
4. apply the whole-batch or larger-target protocol to unresolved x64lens timing;
5. keep tool-native populations separate while adding only task-relevant
   normalized relations;
6. continue active Sprint 12 work with bounded loader validity,
   overlap/provenance, PIE-versus-DSO identity, and GNU-property evidence.

Any change to analyzer behavior, task definition, corpus membership, adapter,
runner, or method receives a new diagnostic campaign identifier.
