# APEX 1.3.1 Changelog

Release date: 2026-10-13

APEX 1.3.1 consolidates workflow, runtime, and validation improvements made
after `1.3.0.post5`. It adds two-phase melting-point calculations, restores
finite-temperature VASP execution, expands cloud execution support, and
hardens LAMMPS, phonon, Gamma, and agent-assisted workflows.

## Highlights

- Added a LAMMPS two-phase coexistence melting-point workflow with restart
  transport, replica diagnostics, post-processing, reporting, and bracket
  determination.
- Added OpenAPI Sandbox execution support alongside Bohrium and local paths.
- Restored finite-temperature VASP workflows with stage-aware execution,
  output validation, failure evidence, and automatic `vasp_gam`/`vasp_std`
  selection from generated k-points.
- Integrated the validated DPA4 phonoLAMMPS runtime for GPU workflows while
  retaining CPU-safe image routing for CPU potentials.
- Added the bundled single-task DPA4 alloytongqi checkpoint and a fail-closed
  immutable PT2 runtime contract with image wrappers and qualification tools.
- Strengthened Gamma and GammaSurface generation, validation, and preview for
  difficult and disordered parent structures.
- Expanded the bundled `apex-flow` agent skill with safer preflight checks,
  execution profiles, and configuration generation.

## Workflow and Runtime Updates

- Added configurable preparation, conditioning, production, restart, and
  replica controls for `melting_point`.
- Added solid-fraction analysis, tidy CSV/JSON outputs, trajectory plots,
  task-status evidence, and periodic restart files.
- Updated phonon processing for Phonopy 4 while retaining compatibility with
  older force-constant generation paths.
- Removed obsolete explicit `plugin load libdeepmd_lmp.so` commands for the
  integrated USER-DEEPMD runtime.
- Added primitive-axis propagation and phonoLAMMPS command improvements.
- Added DeepMD atom maps where required by the DPA4 PT2 runtime.
- Added retries and per-attempt evidence for transient LAMMPS termination,
  timeout, and signal-like failures.

## Validation and Configuration

- Added shared Gamma/GammaSurface geometry and parent-lattice mapping helpers.
- Added overlap, atom-count, and geometry guards before Gamma/GammaSurface
  submission and preview generation.
- Added multi-structure `type_map` inference and validation, including property
  overwrite interactions.
- Added image/machine compatibility checks, CPU/GPU image routing, confirmed
  property profiles, image overrides, and model staging validation.
- Added adaptive DFT k-spacing and stronger VASP/ABACUS input preflight checks.
- Corrected Bohrium ticket expiration handling to use hours.

## Compatibility

- Supported Python versions remain 3.10 through 3.12.
- Existing 1.3.0 parameter files remain supported; new workflow and runtime
  controls are opt-in unless selected for a validated backend.
- Package and container release version: `1.3.1`.
