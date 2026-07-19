# Candidate-Scoped Decoder and Parallelism Design Gate

## Goal

Preserve the bounded, dependency-free one-worker x64lens core while defining a
credible route toward decoder-backed validity and scalable throughput.

## Bounded hybrid pipeline

```text
loader-authoritative PT_LOAD + PF_X regions
  -> byte-oriented terminator scan
  -> bounded candidate windows
  -> exact suffix recognition
  -> semantic-exact classification
  -> optional candidate-scoped decoder adapter
  -> decoder evidence side-car
  -> optional semantic-decoded classification
  -> independent scoring
  -> deterministic reporting
```

The adapter examines only retained candidate windows. For each terminator it
may test candidate starts within the bounded window and retain all justified
decoded sequences or a policy-selected canonical sequence. It must not rescan
non-executable bytes, redefine raw counts, or erase exact/unknown facts.

## Required decoder record facts

A future `decode_record[]`, keyed by candidate index, should include at least:

```text
selected_start
decoded_length
instruction_count
full_sequence_valid
terminator_kind
controlled_registers
clobbered_registers
stack_effect_kind
stack_delta_when_known
memory_read/write facts
validator identity and version
```

Variable-length instructions and operands use arena offsets and lengths, not
persistent raw pointers.

## False-positive and false-negative interpretation

- Raw unaligned candidates are expected scanner observations, not automatically
  product false positives.
- Candidate-scoped decoding can reject or qualify invalid starts without
  removing the raw record.
- Zero canonical terminator misses in a development sample does not prove zero
  false negatives for all binaries, terminator families, depths, or decoder
  policies.
- Exact-catalog undercoverage is distinct from raw terminator recall. Sprint 10
  expands semantic families; decoder evidence may later justify additional
  semantic-decoded families.

## Parallel execution candidates

### Candidate validation parallelism

After the single-threaded scan creates a stable record array, workers can
validate disjoint candidate-index ranges. This is the lowest-risk concurrency
seam because file mapping, ELF parsing, executable-region authority, and raw
record order are already fixed.

### Executable-region parallelism

Independent executable regions may be scanned concurrently. Many binaries have
only one executable load region, so this profile may offer little benefit.

### Chunked scanning

Large regions may be partitioned with an overlap of at least the maximum
candidate-window width. Workers must deduplicate overlap terminators and merge
records by file offset/virtual address. This is the highest-complexity option.

## Determinism and capacity

Any parallel profile must:

- produce byte-identical JSON to one-worker execution for identical options;
- merge by stable `(file_offset, virtual_address, candidate_index)` ordering;
- enforce one global candidate capacity and fail before output if exceeded;
- keep worker-local failures from producing partial output;
- bound worker count, stack size, arena slices, and overlap storage;
- report worker/profile identity in benchmark metadata, not analyzer facts,
  until the CLI contract explicitly adds it.

## Acceptance gate

Do not ship or default-enable acceleration until fixed-corpus evidence shows:

1. no correctness or ordering regression;
2. a meaningful wall-time improvement on defined target sizes;
3. acceptable peak-RSS and binary-size growth;
4. startup overhead does not regress small CI/IR targets materially;
5. malformed-input and interruption behavior remain bounded;
6. single-worker mode remains independently available;
7. the dependency-free default remains viable for air-gapped deployment.

Sprint 11 builds the diagnostic measurement infrastructure. Sprint 14 performs
the pre-freeze optional-profile ablation. Accepted profiles are frozen in Sprint
15 and measured separately in Sprints 16 and 17. Any implementation before those
gates is an experimental profile, not the default runtime.

## Sprint 9 closeout decision

The reference profile is one worker with no decoder. Candidate-scoped validation is the preferred optional correctness profile because it bounds decoder work to evidence already retained by the scanner. Parallelism is not forced into the core before measurement.

The first throughput ablation should compare target-level concurrency, candidate-validation concurrency, and region-level concurrency. Any in-process mode must produce the same ordered facts, global capacity outcome, exit status, and JSON bytes as the one-worker reference while reporting additional CPU, RSS, startup, and synchronization cost.
