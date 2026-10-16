#!/bin/bash
set -euo pipefail
export OMP_NUM_THREADS=1
PY=/opt/apex-venv/bin/python
"$PY" -m apex do param.json make_relax
for input in confs/Al/relaxation/relax_task/in.lammps; do
 (cd "$(dirname "$input")" && /usr/bin/lmp -in in.lammps > log.lammps 2>&1)
done
"$PY" -m apex do param.json post_relax
"$PY" -m apex do param.json make_props
for input in confs/Al/gamma_00/task.*/in.lammps; do
 (cd "$(dirname "$input")" && /usr/bin/lmp -in in.lammps > log.lammps 2>&1)
done
"$PY" -m apex do param.json post_props
"$PY" -c 'import json,math; p="confs/Al/gamma_00/result.json"; d=json.load(open(p)); print(json.dumps(d)); assert len(d)==4; assert all(math.isfinite(float(x)) for v in d.values() for x in v)'
echo CPU_APEX_GAMMA_ACCEPTANCE_PASSED
