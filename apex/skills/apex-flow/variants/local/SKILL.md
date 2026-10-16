---
name: apex-flow
description: Run locally installed APEX relaxation and 15-property workflows through Bohrium direct, local debug, or Slurm/PBS with VASP, ABACUS, or LAMMPS. Includes parent-aware Gamma line/surface and diagnostic views, finite-temperature and two-phase melting-point workflows, restart transport, RSS/high-entropy generation, monitoring, reporting, and result extraction.
---

# APEX Flow — Local Agent Edition

Use APEX for automated relaxation and batch property workflows. This edition is
installed on the same machine as the Agent and must contain
`reference/execution-profile.md`, selected during installation.

## Start Here

1. Read `reference/execution-profile.md`. If it is missing, stop and ask the
   user to reinstall with `apex skill`.
2. Follow that profile's authentication, global configuration, and submit
   command. Do not mix commands from another profile.
3. Confirm the calculator backend: LAMMPS, ABACUS, or VASP.
4. Read the input structure and report formula, atom count, lattice lengths,
   and whether it is already a supercell.
5. Present the complete property JSON and wait for user approval.

## Execution Profiles

- **Bohrium cloud (direct)**: use `apex account`; run `apex submit` directly
  from this machine. A saved AccessKey is exchanged by dflow for a short-lived
  ticket, but no ticket is serialized into `global.json` and no outer Bohrium
  submission job is created.
- **local**: use `apex submit -d` with Local/Shell configuration. No Bohrium
  login, ticket, cloud image, or Argo server is required.
- **local cluster**: use `apex submit -d` and DPDispatcher with Local +
  Slurm/PBS from a login node. Confirm scheduler resources and modules first.

The exact installed choice is in `reference/execution-profile.md`.

## Workflow

1. Prepare structures, calculator inputs, models/potentials, `param.json`, and
   the profile-specific `global.json`.
2. Validate inside the job directory:

   ```bash
   python <skill-root>/scripts/validate_inputs.py \
     --param param.json --global global.json
   ```

   For Gamma properties, read the printed representative-slab report and stop
   on atom-limit, thickness, distance, or KPOINTS errors. Missing
   `min_slab_height`/`max_atoms` is a compatibility warning that requires
   manual confirmation.
3. For `gamma_surface`, run `apex preview param.json` and stop if stderr
   contains `Generated Gamma surface contains overlapping atoms.`
   The default `--gif-view auto` writes both Gamma/GammaSurface projections;
   human-requested diagnostics can select `default`, `slip-plane`, `parent-bc`,
   or `both`. Agents still decide safety from text validation and the overlap
   warning, not by opening the GIF.
4. Run the submit command from the installed execution profile without `-s`
   unless the user explicitly requests submit-only lifecycle management.
5. Preserve the workflow ID, monitor it when applicable, and verify result
   retrieval.
6. Read `confs/<structure>/<property>_00/result.json`. Use
   `scripts/parse_results.py` for multi-result summaries. Use `apex archive`
   only when a consolidated `all_result.json`, database storage, or
   `apex report` is required.

## Calculation setup

Use the selected model and backend with [Runtime images](reference/runtime-images.md).
For tongqi, select `dpa4-alloytongqi-l20` and its image-resident model contract.
For VASP, use the user's licensed image/executable and verified POTCARs.
Set DFT k-spacing using [Calculators](reference/calculators.md).

Read [Properties](reference/properties.md) for property settings, supported
backends, supercell sizes, Gamma geometry and melting replicas. Inspect the
input atom count and the final generated size before submission.

For random solid solutions, follow [RSS](reference/rss_workflow.md), set
`"show_progress": false`, and inspect output POSCARs plus `rss_metadata.json`.

Use [Debug](reference/debug.md) for validation failures, runtime issues and
result recovery. Keep credentials in the selected profile's credential store.
