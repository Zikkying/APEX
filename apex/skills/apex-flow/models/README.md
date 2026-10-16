# Bundled DPA4 model

> **Naming:** APEX **backend** = `lammps` / `abacus` / `vasp`.
> DPA4 alloytongqi is a DeePMD model used by the LAMMPS backend.

The skill ships exactly one model:

| Path | Size | Task/branch provenance |
|------|------|------------------------|
| `DPA4-alloytongqi/model.pt` | 30,403,297 bytes | Single/default task; `alloytongqi` supplied by the user |

SHA-256:
`c84b268cc6191afc72bd2d5c001cbe526a0d2e04ebf6dbd7df021306e9abe9ad`.

Safe static inspection confirms `model_params.type=dpa4`, fitting type
`dpa4_ener`, and `model_branch_alias=[]`. The file does not embed the literal
branch name or a Git commit, so `alloytongqi` is recorded as user-provided
provenance. Do not infer observed-element or training-domain support from the
type map alone.

## Runtime compatibility boundary

Use the current image roles in [runtime-images.md](../reference/runtime-images.md).
For this checkpoint, select `--runtime-profile dpa4-alloytongqi-l20`;
the general DeePMD image cannot load its DPA4 architecture.

### Historical incompatibility evidence (not a recommendation)

The legacy DeePMD 3.1.3 image was tested before the current runtime release.
It is no longer a default or a forced phonon/Grüneisen runtime.

On 2026-08-10, the configured `registry.dp.tech` endpoint was pull-denied, but
the same repository path/tag was available from the Bohrium registry mirror.
The tested mirror artifact was linux/amd64 with repo digest
`sha256:43a27ca4a7bba7f774bbd56104d205a6a80cd9d65928f249f6109e9ef37b8402`,
DeepMD-kit 3.1.3, phonoLAMMPS 0.10.1, and LAMMPS 29 Aug 2024. Against the
bundled file matching the SHA-256 above:

- `dp show` failed with `RuntimeError: Unknown model type: dpa4`.
- LAMMPS 29 Aug 2024 aborted while initializing `pair_style deepmd`; it never
  reached `run 0`.

This proves that digest's DeepMD-kit 3.1.3 runtime cannot execute the model.
Retain the mirror registry domain and digest when reporting provenance; the
configured registry endpoint itself was not readable. Do not submit this model
with that legacy image. Do not restore it as a default or phonon override.

The active profile is `dpa4-alloytongqi-l20`. Read its image identity and
release and qualification status from `data/dpa4_alloytongqi_l20_profile.json`.
The release is enabled and OpenAPI static make/run/post/retrieval acceptance
passed; the full benchmark remains pending. These are separate statuses. T4 is absent from the
sandbox catalog checked on 2026-10-15. Historical T4 evidence and artifacts
remain provenance and must not be reused as L20 qualification.

The target is one L20 (SM 8.9), one MPI rank. Sandboxes use
`c16_m120_1 * NVIDIA L20`; jobs use `1 * NVIDIA L20_48g`.
4090 checkpoint inference is preliminary evidence, not production acceptance.
Cross-family `.pt2` reuse, CPU production, multi-rank and multi-GPU are blocked.

## Agent workflow

1. Retain `models/DPA4-alloytongqi/model.pt` as the source identity; do not pass
   it to LAMMPS.
2. Inspect the candidate with `validate_apex_combo.py list-combos
   --runtime-profile dpa4-alloytongqi-l20`.
3. Generate with `generate_config.py create --runtime-profile
   dpa4-alloytongqi-l20` (add `--sandbox` for the accepted OpenAPI path).
   Use the generated image-resident `.pt2` contract and audited wrappers;
   do not alter profile evidence or bypass compatibility validation.
   The exact wrappers are `/usr/local/bin/dpa4-lmp` and
   `/usr/local/bin/dpa4-phonolammps`.

The skill contains no alternate DPA model or old-model downloader. APEX infers
a zero-based, contiguous element map from the structure; do not substitute
atomic numbers or model-internal indices.
