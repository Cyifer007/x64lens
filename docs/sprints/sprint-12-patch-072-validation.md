# Sprint 12 Patch 072 Validation

## Status

Implementation candidate pending complete local native and Docker acceptance.
Patch 072 addresses confirmed Patch 071 tooling/delivery findings and performs
the planned outcome-blind external-natural acquisition plus same-byte
environment parity. It changes no runtime assembly, include, or JSON schema
file.

## Source precondition

Patch 072 applies to the exact committed Patch 071 source:

```text
HEAD:   d1c1f910e9bc925e01467e1449e65a2d36ad6f0f
parent: ac26a3c39923f05cbfc14bcb332ad5952174fbaa
base tree: 73e54da25224f991178ec7b3083cf465eb1bd362
```

The worktree and index must be clean before application.

## Corrective behavior

- Owned-root tokens use version-3 device, inode, `statx` birth-time, and mount
  identity.
- Fixed-length random quarantine names do not inherit hostile component length.
- Ancestor identity failures close newly opened descriptors.
- Final file, directory, and root removals reauthenticate the held object inside
  the low-level unlink boundary.
- Batch authority version 3 contains 29 cases and 87 executions, including
  leader-exit/inherited-pipe and detached-descendant cases.
- Deadline enforcement continues after direct-leader exit while output or
  adopted descendants remain live.
- Normal and signal transaction roots use identity-bound cleanup.
- Signal publication acceptance consumes an inotify-backed transition record.
- Batch execution follows explicit authenticated `case_order`; JSON object-member order is non-semantic.
- Batch and delivery JSON reject duplicate keys recursively.
- Recursive delivery custody rejects duplicate `root_label` and retains exact
  membership, hash, size, and mode checks.

Focused corrective validation:

```bash
make script-perms-check
make scaffold-check
make sprint12-batch-transaction-smoke
make patch071-corrective-regression-smoke
git diff --check
```

Expected banners:

```text
sprint12-batch-transaction-smoke: ok cases=29 executions=87 stable_hashes=87 successful_batches=3 failed_batches=18 failure_index_0=10 failure_index_1=4 failure_index_2=4 process_tree_cases=2 descendant_failures=1 signals=8 stage_residue=0 survivors=0 fd_growth=0 timing_claims=0

patch071-corrective-regression-smoke: ok cleanup_long_name=1 final_file=1 final_directory=1 final_root=1 generation_identity=1 ancestor_fd=1 duplicate_json=2 case_order=1 leader_exit_deadline=1 detached_descendant=1 normal_root_cas=1 signal_root_cas=1 publication_transition=1 custody_duplicate=1
```

## External-natural acquisition

The host must provide GNU `readelf`, `dpkg-query`, the development toolchain,
and the exact installed source lineages named by the authority.

```bash
make sprint12-external-natural-acquisition-smoke
```

The gate freezes 48 identities before outcomes and then requires:

```text
4 source lineages
12 objects per lineage
28 executable-path objects
20 shared-library-path objects
144 private probe processes
2,592 private run-field records
864 object-field summaries
192 public commands
192 readelf processes
864 readelf field dispositions
0 eligible readelf mismatches
```

The exact `match`, `ambiguous`, `unavailable`, `not_eligible`, and public exit
counts are observed results, not a selection criterion. Capacity exit 6 remains
a valid retained public-command outcome only when stdout is empty and the stable
fail-closed contract is preserved.

A development-host acquisition rehearsal completed the intended denominators over
four installed lineages. It retained 624 eligible matches, 48 ambiguous cells,
192 unavailable cells, and zero eligible mismatches. Forty-six `gadgets` and
`analyze` pairs succeeded; two pairs returned capacity exit 6 with empty stdout.
All 48 private IBT and SHSTK states remained unknown in this selected natural
stratum. These are diagnostic observations, not prevalence or runtime-CET
claims.

## Native/container same-byte parity

```bash
make sprint12-role-property-environment-parity-smoke
```

The target mounts one held-out matrix and the same analyzer, probe, and schema
bytes into both planes. Acceptance requires:

```text
96 objects
5,184 private fields per environment
10,368 combined private fields
5,184 paired private-field agreements
288 paired byte-identical probe processes
768 combined public command closures
384 paired path-normalized public tuples
0 mismatches
```

A two-plane same-host logic rehearsal completed these denominators. Because
that development environment had no Docker command or daemon, the rehearsal is
labeled logic-only and is not native/container acceptance. The Docker parity gate
remains required in WSL2.

## Complete Patch 072 acceptance

```bash
make clean
make
make samples
MALFORMED_TIMEOUT=2 make validation-smoke
SHELLCHECK_STRICT=1 make shellcheck-smoke
make sprint-closeout-smoke
make docker-build
make docker-test
MALFORMED_TIMEOUT=2 make docker-validation-smoke
make sprint12-p072-acceptance-smoke
```

`make sprint12-p072-acceptance-smoke` deliberately keeps package-specific
external acquisition and Docker parity outside the portable native aggregate.
It runs the normal aggregate first, then both Patch 072 host/environment gates.

## Unchanged product contracts

- tool version `0.1.0-dev`;
- JSON schema `0.2.0`;
- program-header and file-backed `PT_LOAD + PF_X` executable authority;
- separate scanner, matcher, classifier, provenance/effect side-cars, scorer,
  and reporters;
- distinct raw, exact-suffix, semantic-exact, unknown, future decoder-backed,
  and scored facts;
- candidate capacity 4,096 and candidate-4,097 exit 6 before stdout;
- malformed-input no-partial-output behavior;
- read-only targets and no target execution;
- dependency-free, decoder-free, one-worker reference runtime; and
- no public PIE/DSO, IBT, or SHSTK field.

## Interpretation and next gate

Passing Patch 072 supports a bounded claim that the maintained private fact
plane agrees with independent vectors and eligible GNU `readelf` evidence on
the selected natural package stratum and that the same bytes produce the same
private/public tuples in native and container environments. It does not prove
runtime CET enforcement, representativeness, mitigation prevalence, complete
loader semantics, publication readiness, or exploitability.

Patch 073 owns the non-reinterpretive public-policy decision. It may expose
compatible optional `0.2.x` indicators only when the complete Patch 072
acceptance evidence and limitations justify them; otherwise it records explicit
deferral. Patch 074 owns Sprint 12 closeout.
