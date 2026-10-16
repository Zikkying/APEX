---
name: apex-flow
description: Run APEX 15-property materials workflows with LAMMPS, ABACUS or VASP, including relaxation, elastic constants, EOS, defects, stacking faults, phonons, finite-temperature properties and RSS structures.
---

# APEX Flow

Use APEX for automated structure preparation, relaxation, property calculations
and result collection. Follow the workflow below; consult the linked reference
for the selected property or calculator.

## 1. Select the calculation

Use the user's selected backend, model and property parameters. Clarify missing
scientific choices and show the effective property JSON before submission.
Read the structure's formula, atom count, lattice and existing supercell size;
choose the final size required by the property.

| Calculation | Runtime choice |
|---|---|
| Classical EAM/MEAM | CPU runtime |
| Compatible DeePMD TensorFlow/PyTorch model | General DeePMD GPU runtime on L20 |
| DPA4-alloytongqi | `--runtime-profile dpa4-alloytongqi-l20` |
| ABACUS | ABACUS backend with pseudopotentials/orbitals |
| VASP | User-authorized licensed image and POTCARs |

[Runtime images](reference/runtime-images.md) lists exact images and commands.
For tongqi, the profile supplies its image-resident `.pt2`; the bundled
`models/DPA4-alloytongqi/model.pt` records source provenance.

## 2. Generate the job

Cloud/MatMaster uses `BOHRIUM_ACCESS_KEY` and `BOHRIUM_PROJECT_ID` (or
`--project-id`). From the skill root, inspect supported arguments:

```bash
python scripts/generate_config.py create --help
python scripts/generate_config.py describe-parameters
```

Use `create` with the selected backend, structures, model and property JSON.
It stages inputs and writes `param.json` and `global.json`, including
`bohrium_config.ticket`. Set `"type_map": "auto"`; `apex submit` expands it.
For a saved task, `refresh-global --global global.json` refreshes credentials
while preserving the property parameters. Generate the ticket before packaging.

Choose LAMMPS accuracy with `--accuracy screening`, `balanced`, or `precise`
(default). Review the generator's effective settings and expected task count.
For tongqi OpenAPI, select `--runtime-profile dpa4-alloytongqi-l20 --sandbox`.
The generator supplies the matching machine, model hashes and absolute commands.

## 3. Validate and submit

Use an environment with APEX and its scientific dependencies. If the MM Agent
environment lacks APEX, stage the task and skill helpers in the APEX/CPU image
and run the [preflight procedure](reference/submission.md#preflight-in-the-apexcpu-image)
there. Run in the generated job directory:

```bash
python <skill-root>/scripts/validate_inputs.py --param param.json --global global.json
```

Proceed after `Validation PASSED`. Check the image/machine pairing with
`scripts/validate_apex_combo.py check` using the generated values and profile.
For Gamma preview requests and `gamma_surface`, run `apex preview param.json`
in that same environment and review the geometry report.

Cloud/MatMaster submits an outer Bohrium job on `c1_m2_cpu` using the APEX/CPU
image. Its client validates preinstalled APEX >= 1.3.4 with `ensure_apex.py`,
then runs `python -m apex submit param.json -c global.json`. Keep the client
running for monitoring and automatic retrieval. The `--sandbox` option selects
the inner OpenAPI calculator backend. Use the complete run script in
[Submission](reference/submission.md).

Installed local editions read `reference/execution-profile.md` and use its
Bohrium-direct, local-debug or Slurm/PBS submission procedure.

## 4. Monitor and collect

Save the inner dflow workflow ID and, for Cloud/MatMaster, the outer job ID.
Use [Workflow control](reference/workflow-control.md) for status and retrieval.
Report success after workflow completion, result download, successful
`apex_task_status.json` records and finite property outputs. Report convergence
from the calculator log and the requested scientific tolerance.

To stop a cloud run, terminate the inner workflow first. For a failure or stalled
step, use [Debug](reference/debug.md) to inspect the original error and recover.

## Property preparation

- Prefer joint relaxation + properties for a new structure.
- For RSS/high-entropy structures, follow [RSS](reference/rss_workflow.md), use
  `"show_progress": false`, and inspect `rss_metadata.json` and output POSCARs.
- For Gamma, choose the parent crystal and slip system from
  [Properties](reference/properties.md). FCC (111) Shockley uses `[1,1,-2]`.
  Inspect the generated slab report before running the full scan.
- For DFT, select k-spacing, pseudopotentials and the executable using
  [Calculators](reference/calculators.md).
- For finite-temperature and melting calculations, use the backend and replica
  requirements in [Properties](reference/properties.md).

## References

| Read when | Document |
|---|---|
| Selecting images and executable paths | [Runtime images](reference/runtime-images.md) |
| Packaging and submitting | [Submission](reference/submission.md) |
| Querying, retrieving or stopping jobs | [Workflow control](reference/workflow-control.md) |
| Setting property parameters | [Properties](reference/properties.md) |
| Preparing calculator inputs | [Calculators](reference/calculators.md) |
| Choosing a LAMMPS potential | [Potentials](reference/lammps_potentials.md) |
| Generating random solid solutions | [RSS](reference/rss_workflow.md) |
| Following worked examples | [Examples](reference/examples.md) |
| Diagnosing a failure | [Debug](reference/debug.md) |
