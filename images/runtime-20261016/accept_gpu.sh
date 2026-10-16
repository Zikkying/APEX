#!/bin/bash
set -euo pipefail
nvidia-smi
/usr/local/bin/apex-calculator-python -c 'import numpy,monty,ruamel.yaml,deepmd,torch,tensorflow,phonolammps; print(deepmd.__version__,torch.__version__,tensorflow.__version__)'
for name in deepmd_tf deepmd_pt ni540; do
 /usr/local/bin/apex-lmp -nonbuf -in "$name.in" > "$name.full.log" 2>&1
 echo "$name EXIT=0"
 tail -45 "$name.full.log"
done
echo RUNTIME_ACCEPTANCE_PASSED
