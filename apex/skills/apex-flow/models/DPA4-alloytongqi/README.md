# DPA4 alloytongqi

- File: `model.pt`
- Model type: DPA4 (`dpa4_ener` fitting)
- Task form: single/default task (`model_branch_alias=[]`)
- Branch provenance: `alloytongqi`, supplied by the user; not embedded in the checkpoint
- Size: 30,403,297 bytes
- SHA-256: `c84b268cc6191afc72bd2d5c001cbe526a0d2e04ebf6dbd7df021306e9abe9ad`
- Current dedicated runtime: `registry.dp.tech/dptech/dp/native/prod-397953/397637/dpa4-alloytongqi-l20:20261015-slim02`
- Image selection: [runtime-images.md](../../reference/runtime-images.md)
- Historical incompatibility evidence (not a runtime recommendation): the old tag's Bohrium registry mirror, repo digest
  `sha256:43a27ca4a7bba7f774bbd56104d205a6a80cd9d65928f249f6109e9ef37b8402`,
  failed with `RuntimeError: Unknown model type: dpa4`; LAMMPS aborted while
  initializing `pair_style deepmd`.

Keep `model.pt` as the source identity; never pass it directly to LAMMPS under
the DPA4 L20 profile. The active profile requires an immutable image digest and
the recorded release/OpenAPI qualification on L20 SM 8.9. The release is
enabled; static make/run/post/retrieval passed, while the full benchmark
remains pending. T4 was absent from the sandbox catalog checked on
2026-10-15; its old artifacts are not interchangeable with the L20 build.
Generate using `generate_config.py create --runtime-profile
dpa4-alloytongqi-l20`; its generated commands use absolute
`/usr/local/bin/dpa4-lmp` and `/usr/local/bin/dpa4-phonolammps` wrappers. The configured `registry.dp.tech` endpoint was
pull-denied; the legacy digest above identifies the tested artifact from
`registry.bohrium.dp.tech`.
