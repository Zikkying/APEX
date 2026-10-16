# Native science execution (development)

APEX preparation, preview and postprocessing do not require dflow, DPDispatcher,
workflow configuration or cloud credentials. Install the `workflow` extra for
legacy submit/run adapters. `apex do` make/post remains compatible.

`apex native prepare PARAM --stage relax|props --runtime RUNTIME --output TASKS`
creates scientific input files and a portable task manifest. Manifest paths are
relative to PARAM's directory. Runtime specifies calculator command, image and
Python environment. Use `export` for already prepared files, `pack` to materialize
symlinks, `run --task ID --result REPORT` to execute, `check --task ID` to inspect,
and `post PARAM TASKS` to aggregate validated results. These CLI commands share
`apex.native` Python functions and use exit 0 for success, 1 for failure.

Relaxation must be calculated and postprocessed before preparing dependent
properties. Each task revision binds commands, runtime, inputs and dependency
hashes. Gamma reports check actual generated structures and enter the dependency
hashes. Phonon/Grüneisen preserve original POSCAR alongside derived input hashes.
A changed input cannot reuse a successful receipt. Interrupted locks require
reconciliation and a fresh attempt workspace; do not remove them blindly.

MatMaster owns sandbox lifecycle through ManagedSandbox. APEX owns no cloud
credentials or resources. Packaged input snapshots must not include credentials.
The dflow RunLAMMPS OP delegates to the same standalone LammpsRunner.

## Validation status

Development work, not a released package/image. CPU EAM relaxation and all 15
properties ran in real bohr sandboxes; phonon/Grüneisen were rerun after preserving
mutable inputs. These are short transport/execution smoke cases, not convergence
studies. General DeePMD GPU and alloytongqi L20 relaxation plus all 15 properties also
ran and were postprocessed. An earlier GPU launch failed on DNS and expired;
the subsequent new-resource retry passed. Runtime source overlays were used;
this does not qualify a newly published image.

Unit/regression evidence and per-property runtime receipts are recorded by the
cross-repository delivery report. MatMaster Test deployment, real Agent evaluation
and platform acceptance remain prerequisites to promotion.
