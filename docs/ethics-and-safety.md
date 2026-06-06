# Ethics and Safety

## Intended uses

x64lens is intended for:

- assembly language education,
- authorized reverse engineering,
- defensive binary triage,
- secure build validation,
- exploitability research,
- vulnerability management enrichment,
- reproducible benchmarking.

## Prohibited project scope

The baseline project will not include:

- exploit payload generation,
- remote target scanning,
- malware deployment,
- unauthorized access tooling,
- live exploitation automation,
- credential theft,
- persistence mechanisms,
- evasion guidance.

## Output language discipline

The tool should avoid overclaiming. It should not say:

```text
This binary is exploitable.
```

It should say:

```text
This binary exposes primitives consistent with certain exploit strategies, assuming an independent vulnerability and necessary runtime conditions.
```

## Sample handling

Do not commit:

- proprietary enterprise binaries,
- malware samples,
- customer data,
- production firmware without redistribution rights,
- private vulnerability evidence,
- exploit proofs against third-party software.

Use source-built toy binaries and redistributable open-source binaries for tests and benchmarks.
