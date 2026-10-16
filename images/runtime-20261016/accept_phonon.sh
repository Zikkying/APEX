#!/bin/bash
# Run after accept_cpu.sh in the same clean acceptance work directory.
set -euo pipefail
export OMP_NUM_THREADS=1
PY=/opt/apex-venv/bin/python
"$PY" -m apex do param-phonon.json make_props
(cd confs/Al/phonon_00/task.000000 && /opt/apex-venv/bin/phonolammps in.lammps -c POSCAR --dim 1 1 1 --logshow -pa 1 0 0 0 1 0 0 0 1)
"$PY" -m apex do param-phonon.json post_props
"$PY" - <<'PY'
import json, math
result = json.load(open('confs/Al/phonon_00/result.json'))
assert result['band']
def check(value):
    if isinstance(value, dict):
        for item in value.values(): check(item)
    elif isinstance(value, list):
        for item in value: check(item)
    elif isinstance(value, (int, float)):
        assert math.isfinite(value)
check(result)
PY
echo CPU_PHONON_ACCEPTANCE_PASSED
