# Runtime images — APEX 1.3.4

Generate image settings with `scripts/generate_config.py`. The profile data in
`data/default_templates.json` and `data/dpa4_alloytongqi_l20_profile.json`
provides exact values.

## Current APEX/LAMMPS images

All three tags below use the prefix
`registry.dp.tech/dptech/dp/native/prod-397953/397637/`.
Use the complete address in a configuration.

| Role | Tag | Use |
|---|---|---|
| Outer client, make/post, classical LAMMPS | `apex-flow-cpu:1.3.4-20261016-offline` | APEX client, make/post and classical potentials |
| General DeePMD GPU calculator | `apex-deepmd-gpu:3.1.3-20261016` | L20; compatible TensorFlow `.pb` and PyTorch `.pth` models |
| DPA4-alloytongqi calculator | `dpa4-alloytongqi-l20:20261015-slim02` | Pinned L20 profile and image-resident `.pt2` |

Use `--runtime-profile dpa4-alloytongqi-l20` for that checkpoint. Preserve its
image digest, image-resident `.pt2` hash, Python wrapper and single-L20 checks.
Use the selected model and verify convergence from calculator outputs.

| Runtime | LAMMPS | Scientific Python | phonoLAMMPS executable |
|---|---|---|---|
| CPU | `/usr/bin/lmp` | `/opt/apex-venv/bin/python` | `/opt/apex-venv/bin/phonolammps` |
| General GPU | `/usr/local/bin/apex-lmp` | `/usr/local/bin/apex-calculator-python` | `/opt/deepmd-kit-3.1.3/bin/phonolammps` |
| Alloytongqi | `/usr/local/bin/dpa4-lmp` | `/usr/local/bin/dpa4-python` | `/usr/local/bin/dpa4-phonolammps` |

LAMMPS commands append `-in in.lammps`. Each phonoLAMMPS command appends
`{input_file} -c {poscar} --dim {dim} {primitive_axes}`. Use the generator's
complete commands, including its environment settings. The generated absolute paths select the image’s preinstalled scientific environment.
Keep `type_map: "auto"` expansion through `apex submit`; direct Python submission
uses the same preprocessing helper described in [Debug](debug.md).

For L20, native job SKU is `1 * NVIDIA L20_48g`; the OpenAPI sandbox SKU is
`c16_m120_1 * NVIDIA L20`. Use the identifier for the selected backend.
The outer client may be CPU even when the inner calculator requires a GPU.
Query the matching live machine catalog before allocating resources.

## Other roles

- ABACUS uses `registry.dp.tech/dptech/abacus:3.8.2`, matching the generator.
  Select it for the ABACUS DFT backend.
- OpenAPI dispatch uses
  `registry.dp.tech/dptech/polycalibur:dpdispatcher-storehost-plan-a-20260811`.
  It launches DPDispatcher jobs.
- VASP requires a user-provided licensed image. MACE, NEP, GAP, RANN and SNAP
  use separately validated custom runtimes.

## Diagnostics

See [Debug](debug.md) for runtime compatibility,
registry access, saved configurations and troubleshooting.
