# Runtime images — APEX 1.3.4

Use these roles when generating a new configuration. The executable defaults
are in `scripts/generate_config.py`, `data/default_templates.json`, and
`data/dpa4_alloytongqi_l20_profile.json`. Existing jobs and saved `global.json`
files retain their explicit image settings; installing a new skill does not
rewrite them. Check the submitted configuration and inner-job receipt.

## Current APEX/LAMMPS images

All three tags below use the prefix
`registry.dp.tech/dptech/dp/native/prod-397953/397637/`.
Use the complete address in a configuration.

| Role | Tag | Acceptance scope |
|---|---|---|
| Outer client, make/post, classical LAMMPS | `apex-flow-cpu:1.3.4-20261016-offline` | Al EAM relaxation, gamma make/run/post/archive, small phonon; CPU OpenAPI joint workflow |
| General DeePMD GPU calculator | `apex-deepmd-gpu:3.1.3-20261016` | L20; tested TF `.pb` and DPA-3.2 PyTorch `.pth`; GPU OpenAPI relaxation workflow |
| DPA4-alloytongqi calculator | `dpa4-alloytongqi-l20:20261015-slim02` | Pinned L20 profile; 108-atom FeCoNi static OpenAPI make/run/post/retrieval/archive; full benchmark pending |

The general DeePMD image cannot load the bundled alloytongqi DPA4 architecture.
Use `--runtime-profile dpa4-alloytongqi-l20` for that checkpoint. Preserve its
image digest, image-resident `.pt2` hash, Python wrapper and single-L20 checks.
Do not substitute another model or infer convergence from successful execution.

| Runtime | LAMMPS | Scientific Python | phonoLAMMPS executable |
|---|---|---|---|
| CPU | `/usr/bin/lmp` | `/opt/apex-venv/bin/python` | `/opt/apex-venv/bin/phonolammps` |
| General GPU | `/usr/local/bin/apex-lmp` | `/usr/local/bin/apex-calculator-python` | `/opt/deepmd-kit-3.1.3/bin/phonolammps` |
| Alloytongqi | `/usr/local/bin/dpa4-lmp` | `/usr/local/bin/dpa4-python` | `/usr/local/bin/dpa4-phonolammps` |

LAMMPS commands append `-in in.lammps`. Each phonoLAMMPS command appends
`{input_file} -c {poscar} --dim {dim} {primitive_axes}`. Use the generator's
complete commands, including its environment settings. Do not shorten commands
to bare `python3`, `lmp`, or `phonolammps`: shell PATH can select the wrong
environment. Runtime jobs must not install or upgrade scientific packages.
Keep `type_map: "auto"` expansion through `apex submit`; direct Python submission
must perform the same preprocessing rather than pass the literal string onward.

For L20, native job SKU is `1 * NVIDIA L20_48g`; the OpenAPI sandbox SKU is
`c16_m120_1 * NVIDIA L20`. Do not interchange them or silently fall back to CPU.
The outer client may be CPU even when the inner calculator requires a GPU.
T4 was absent from the sandbox catalog checked on 2026-10-15; query current
availability before allocating resources.

## Other roles

- ABACUS uses `registry.dp.tech/dptech/abacus:3.8.2`, matching the generator.
  It is a separate DFT backend, not an alternative DPA calculator. This release's
  CPU/GPU tests do not constitute a new ABACUS acceptance run.
- OpenAPI dispatch uses
  `registry.dp.tech/dptech/polycalibur:dpdispatcher-storehost-plan-a-20260811`.
  This is the dispatcher image, not the APEX make/post or calculator image.
- VASP requires a user-provided licensed image. MACE, NEP, GAP, RANN and SNAP
  require separately validated custom runtimes; do not reuse the general GPU
  image merely because a model needs a GPU.

## Historical references and distribution

Old `deepmd-kit-phonolammps:3.1.3`, `dpa4-phonolammps:0.0.2` and
`apex-flow:1.3.0.post` references in build provenance, changelogs or failure
records are historical evidence, not current recommendations. Phonon and
Grüneisen submission must not force an old image over the selected runtime.
Benchmark placeholders identify a new candidate to qualify, not a usable image.

These addresses are Bohrium registry images. Project access may be required.
Docker Hub publication has not been verified; do not invent public Docker Hub
aliases. For a downloaded MM ZIP, replace/reload the installed skill and
regenerate the configuration before submitting a new job.
