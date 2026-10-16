---
name: apex-flow
description: "Prepare, check and analyze APEX relaxation and 15-property LAMMPS tasks: Gamma, phonons, Grüneisen, defects, finite-temperature, annealing and melting. Use ManagedSandbox in MatMaster; retain optional VASP/ABACUS workflows."
---

# APEX Flow

APEX provides 15-property workflows and prepares structures and calculator inputs, checks results and computes
properties. In MatMaster, use `ManagedSandbox` for bohr compute resources and
execution. Use the matching APEX package and [runtime image](reference/runtime-images.md).

## Prepare

Read the structure's composition, lattice, atom count and existing supercell.
Choose the user's model and property settings; show effective parameters and
separate a small smoke test from a converged scientific calculation.

From this skill directory:

```bash
python scripts/generate_config.py create --help
python scripts/generate_config.py describe-parameters
```

For LAMMPS use `create --execution native` with structures, potential/model and
property options. It writes `param.json`, `runtime.json` and `tasks.json`.
Native preparation needs no cloud credentials or `global.json`. `"type_map": "auto"`
is normalized in the shared preparation layer. For alloytongqi select
`--runtime-profile dpa4-alloytongqi-l20`; preserve its pinned model and environment.
`models/DPA4-alloytongqi/model.pt` records source provenance.

Run relaxation first. Download its outputs and run `apex native post param.json
tasks.json` before preparing properties that depend on the relaxed structure.
Use `apex native prepare param.json --stage props --runtime runtime.json` for the
next stage. Commands can be inspected with `apex native --help`.

For Gamma, run `apex preview param.json --check-only` and inspect composition,
parent mapping, slip groups, frame displacement, overlap and vacuum diagnostics.
Gamma line requires fixed in-plane positions, normal relaxation and a fixed cell.
Native manifests also bind checks of the actual task structures by digest.
Resolve failed checks and explain unknown checks before calculation.

## Compute in MatMaster

1. `ManagedSandbox(action="create", request_id=..., image=..., cpu=... or gpu=...)`.
   Reuse a ready resource with the same runtime within the run.
2. `upload` the workspace-relative `tasks.json` with its `resource_id`.
3. `execute` each manifest `task_id` with a stable `request_id`. Execution returns
   immediately; serial execution on each resource is the default.
4. Query `status` and `logs`; after a terminal state, `download` to a workspace
   result directory. A live sandbox or vanished PID is not calculation success.
5. Run `apex native check` and `post` on collected files, then analyze results.
6. `stop` targets an execution; `delete` reclaims the resource after collecting
   outputs and diagnostics. Confirm deletion through `status`.

If a response is lost, repeat the same operation ID or query status. Never invent
another ID to retry an uncertain start. If ManagedSandbox is unavailable, report
that integration dependency; do not bypass tracked lifecycle controls with Bash.
Parameter/input changes require a new manifest revision and new computation.

## Analyze

Check calculator exit status, input revision, required outputs and finite values.
Preserve task-level failures, inconclusive melting classifications and diagnostic
logs. Explain observed values with units and sampling/convergence limits.
Do not interpret a short smoke run as converged scientific evidence.

## Standalone and legacy

Standalone `apex native pack/run/check/post` uses the same implementation as MM.
`apex do ... make_relax/post_relax/make_props/post_props` remains available.
VASP/ABACUS and legacy submission use `pip install apex-flow[workflow]` in an
appropriate environment and the [legacy submission guide](reference/submission.md).
Legacy cloud configuration uses `BOHRIUM_PROJECT_ID` and the image/machine
validator `scripts/validate_apex_combo.py`. Credentials stay in runtime configuration.
Runtime details and recovery procedures are in [Debug](reference/debug.md).
