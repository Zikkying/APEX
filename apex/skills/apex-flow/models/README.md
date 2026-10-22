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

## Run the model

Select `--runtime-profile dpa4-alloytongqi-l20` with `generate_config.py create`.
The profile provides the pinned image, image-resident `.pt2`, model hashes,
L20 machine and absolute executable paths. Add `--sandbox` for inner OpenAPI
execution. Submit through `apex submit` to expand `type_map: "auto"`.

See [Runtime images](../reference/runtime-images.md) for image selection and
[Debug](../reference/debug.md) for compatibility diagnostics.
