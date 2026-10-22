# APEX debug guide

Start with the failing workflow step, its calculator task directory and the
original stderr. Record the workflow ID, task ID, image/digest, model hash,
actual machine, APEX version and command. Preserve successful task outputs
while repairing the failed step.

## Find the repair

| Symptom | Inspect | Repair |
|---|---|---|
| Local `apex` command missing / `ModuleNotFoundError: apex` | Agent interpreter and preflight log | Run preview and full validation in the [APEX/CPU preflight job](submission.md#preflight-in-the-apexcpu-image), collect the reports, then submit the checked inputs. |
| Missing ticket or authentication failure | Selected execution profile and `global.json` | Cloud/MM: run `refresh-global` on the Agent before packaging; use its `bohrium_config.ticket`. Installed direct mode: use `apex account`. |
| Invalid project ID | Generator validation output | Supply `BOHRIUM_PROJECT_ID` or `--project-id`; ticket-mode IDs must be integers. |
| Image pull denied / unexpected old image | Submitted `global.json`, inner-job image and project access | Regenerate with the current skill; verify access to the image in the active project. Saved jobs retain their original configuration. |
| Machine type does not exist / unexpected CPU | Inner-job receipt and the matching live machine catalog | Native L20 job: `1 * NVIDIA L20_48g`; OpenAPI sandbox: `c16_m120_1 * NVIDIA L20`. The outer client can be `c1_m2_cpu`. |
| `Unknown model type: dpa4` | Model identity and loader image | For alloytongqi, generate with `--runtime-profile dpa4-alloytongqi-l20`; use its image-resident `.pt2`. |
| Missing `monty`, `numpy` or `ruamel.yaml` | Exact Python executable used by DPDispatcher | Restore the generated `dispatcher_remote_command`; tongqi uses `/usr/local/bin/dpa4-python`. Validate dependencies in that same environment. |
| `phonolammps: command not found` | Generated `phonolammps_run_command` | Use the absolute executable and complete argument template from [Runtime images](runtime-images.md). Login shells can reset PATH. |
| Unresolved `type_map="auto"` | Submission entrypoint and property interactions | Use `python -m apex submit`; direct integrations must expand all maps using the helper described below. |
| APEX startup/version error | `ensure_apex.py` output and submission interpreter | Select the current APEX/CPU image with preinstalled APEX >= 1.3.4. |
| Props-post fails | First failed calculator task, zero-displacement reference, task status and raw output | Repair the originating calculation, then recover the affected step using [Workflow control](workflow-control.md). |
| Step remains Running | Dispatch status, log timestamps, GPU activity, iteration/force history | Distinguish resource wait, model load, active calculation and minimizer stall from observed logs. |
| Finished job but missing/invalid results | Exit code, `apex_task_status.json`, finite energies, retrieval log | Complete calculation/retrieval before reporting property success. |
| Gamma overlap or invalid direction | Preview stderr, `gamma_geometry.json`, `slab_generation.json` | Correct parent lattice, plane/direction and slab size, then validate again. |
| RSS produced zero configurations | `rss_metadata.json`, composition, interval, steps and requested count | Repair `rss.json` and rerun `apex rss`; inspect written POSCARs. |

## Submission and environment

Cloud/MM generates credentials before packaging: never refresh it in `run.sh`.
The job reuses the ticket; the Agent's AccessKey is not guaranteed to exist
inside the container. Keep credentials out of logs and committed files.
Use `create` or `refresh-global` rather than calling ticket APIs manually.

`apex submit` expands `interaction.type_map="auto"` from resolved structures.
For direct Python integrations, call
`auto_fill_type_map_from_poscar(parameter_dict, param_path)` for each parameter
file with its real path, including property-specific interactions, before
`submit_workflow`. The low-level API rejects unresolved maps.

The runtime image provides scientific dependencies. Calculator jobs must not
install or upgrade packages. A new image requires dependency checks and real
acceptance before replacing the selected profile. Restore generated wrappers
rather than changing the system Python or editing validation code.

Query failures with:

```bash
apex getsteps <workflow-id> -c global.json --phase Failed,Error
```

Preserve the submission exit code when capturing logs. Keep the submit client
alive for monitoring and retrieval. Stop the inner dflow workflow before its
outer client. Reconcile existing jobs before retrying to avoid duplicate work.

## Model and GPU compatibility

Use the generic DeePMD image for compatible TF `.pb` and PyTorch `.pth`
models on L20. Alloytongqi requires its dedicated DPA4 profile, one L20
SM 8.9 GPU and one MPI rank. CPU production, other GPU families, multi-rank
and multi-GPU execution require separate runtime evidence. Query the live machine catalog when selecting resources.
MACE, NEP, GAP, RANN and SNAP need separately validated custom images.

The bundled checkpoint `models/DPA4-alloytongqi/model.pt` is source provenance;
the runtime uses the profile's hashed image-resident `.pt2`. Preserve model
identity, hashes and validator checks during repair. Changing a model or
calculator changes the scientific calculation and needs the user's choice.

## Geometry and scientific checks

Inspect formula, atom count and lattice before expansion. Use `[1,1,1]` for an
already adequate supercell. Slab thickness and in-plane size are separate from
bulk supercell expansion. Keep `elastic.conventional` at its default unless a
conventional-cell calculation is requested.

For disordered Gamma structures, set `parent_lattice` explicitly. FCC (111)
Shockley slip uses `[1,1,-2]`, with Burgers vector `a/6[1,1,-2]`. Gamma defaults
to 20 Å vacuum. `displacement_points` must be finite, unique, in `[0,1]` and
include zero. Run the actual zero-displacement slab before a new model/geometry
scan. Resolve `Generated Gamma surface contains overlapping atoms.` before
submission; optional `--gif-view` visualizations supplement the geometry report.

A completed runtime is not proof of force convergence. Read the minimizer stop
criterion and final forces; compare tighter tolerances for small energy
differences. `linesearch alpha is zero` can precede the requested tolerance.
Use [Properties](properties.md) for finite-temperature and melting diagnostics:
`restart.coexistence.start` transports temperature-matched melting input;
`finite_t_latt` never receives this file. The generated script does not add
`read_restart`. Missing, duplicate or disagreeing replicas give `inconclusive`.

VASP requires an authorized image and POTCARs. Match MPI ranks to resources;
APEX selects `vasp_gam` for Gamma-centered 1x1x1 and `vasp_std` otherwise.
`vasp_gam` needs `KPAR=1`; `KPAR` divides ranks and `NCORE` divides ranks/KPAR.
Choose `NCORE` or `NPAR`, and initialize the image's MPI/oneAPI environment and
stack limit. See [Calculators](calculators.md) for complete inputs.

