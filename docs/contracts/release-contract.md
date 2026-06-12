# Release Contract

## Release readiness checklist

Before a public release:

- [ ] `make clean && make` passes.
- [ ] `make test` passes.
- [ ] README usage is current.
- [ ] `CHANGELOG.md` is updated.
- [ ] CLI contract is updated.
- [ ] JSON schema is updated if output changed.
- [ ] Benchmark scripts still run.
- [ ] Security and ethics documents are current.
- [ ] Release artifacts have checksums.

## Artifact expectations

Future release artifacts should include:

- source archive,
- Linux x86_64 binary,
- SHA256 checksums,
- version output,
- benchmark smoke result.

## Signing

Signed releases are future work.

## Patch and release bundle hygiene

Patch and release bundles must exclude local-only and generated state unless the artifact is explicitly designed to contain it.

Forbidden in public source patch bundles:

- `.git/`,
- `.local/`,
- `build/`,
- `tests/bin/`,
- generated toy binaries,
- generated benchmark results,
- object files,
- private/course documents,
- nested ZIP files.

Validate generated patch bundles with:

```bash
BUNDLE=/path/to/patch.zip make patch-bundle-hygiene
```

Project context bundles are separate from public source patch bundles.
