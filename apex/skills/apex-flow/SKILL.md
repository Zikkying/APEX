---
name: apex-flow
description: "Run APEX 15-property materials workflows with LAMMPS, ABACUS or VASP: relaxation, elastic constants, EOS, defects, stacking faults, phonons, finite-temperature properties and RSS structures."
---

# APEX Flow

## 1. Prepare

Use the user's backend, model and parameters; ask only for missing choices.
Prefer joint relaxation + properties. Choose supercell size from the input
atom count and the requested property.

| Calculation | Runtime |
|---|---|
| EAM/MEAM | APEX/CPU |
| Compatible DeePMD TF/PyTorch | General DeePMD GPU on L20 |
| DPA4-alloytongqi | `--runtime-profile dpa4-alloytongqi-l20` |
| ABACUS / VASP | ABACUS inputs / user-authorized VASP image and POTCARs |

Use [Runtime images](reference/runtime-images.md) for exact paths.
`models/DPA4-alloytongqi/model.pt` records source provenance; the tongqi
profile supplies the executable image-resident model. For this selection, use
`--backend lammps --potential deepmd --runtime-profile dpa4-alloytongqi-l20`;
the profile sets the model path. See the [118-element list](models/DPA4-alloytongqi/README.md#elements).

Generate with `scripts/generate_config.py create` using the approved inputs.
Cloud/MM uses `BOHRIUM_ACCESS_KEY` and `BOHRIUM_PROJECT_ID` (or `--project-id`);
the generator writes `param.json`, `global.json` and `bohrium_config.ticket`.
Set `"type_map": "auto"`. Add `--sandbox` for inner OpenAPI execution.
Consult `create --help` or `describe-parameters` when needed.

## 2. Check once and submit

Run `validate_inputs.py --param param.json --global global.json` once on the
final inputs, then submit after `Validation PASSED`. Use the
[submission script](reference/submission.md) to combine this check with
`python -m apex submit param.json -c global.json`.

If MM lacks local APEX, run the check in the APEX/CPU image as part of the
outer Bohrium job. For a requested preview or `gamma_surface`, run
`apex preview param.json` there first; use a separate CPU preflight job when
the preview needs user review. The [preflight procedure](reference/submission.md#preflight-in-the-apexcpu-image)
contains the staging and commands. Repeat checks when inputs change.

Keep the submit client running for automatic result retrieval.
[Execution profile](reference/execution-profile.md) describes this edition.

## 3. Collect

Save the inner workflow ID and outer job ID. Confirm completion and retrieved
property results, then report values with units and convergence status.
Use [Workflow control](reference/workflow-control.md) for monitoring/stopping
and [Debug](reference/debug.md) when execution or results need investigation.

## Read as needed

- [Properties](reference/properties.md): parameters, cell sizes, Gamma and finite-T.
  FCC (111) Shockley direction is `[1,1,-2]`.
- [Calculators](reference/calculators.md) / [Potentials](reference/lammps_potentials.md): engine inputs and models.
- [RSS](reference/rss_workflow.md): structure generation with `"show_progress": false`.
- [Examples](reference/examples.md): complete jobs.
- Custom image/machine: `validate_apex_combo.py` and [Runtime images](reference/runtime-images.md).
