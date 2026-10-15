#!/usr/bin/env bash
# Run on a NEW L20 sandbox created from IMAGE_REF@IMAGE_DIGEST.
# Only the benchmark harness is uploaded; runtime files must remain untouched.
set -euo pipefail
BENCH_ROOT=${1:?usage: qualify-image.sh BENCH_ROOT NEW_WORKSPACE IMAGE_REF IMAGE_DIGEST}
WORKSPACE=${2:?new workspace required}
IMAGE_REF=${3:?registry image reference required}
IMAGE_DIGEST=${4:?registry-resolved digest required}
[[ "$IMAGE_DIGEST" =~ ^sha256:[0-9a-f]{64}$ ]] || exit 2
[[ "$IMAGE_DIGEST" != "sha256:$(printf '%064d' 0)" ]] || exit 2
[[ ! -e "$WORKSPACE" ]] || { echo 'Workspace already exists' >&2; exit 2; }
export PATH=/usr/local/bin:/opt/mamba/bin:$PATH
PYTHON=/usr/local/bin/dpa4-python
MODEL_DIR=/opt/dpa4-runtime/models/DPA4-alloytongqi
"$PYTHON" - <<'PY'
import numpy, monty, ruamel.yaml
import hashlib, json
from pathlib import Path
manifest = json.loads(Path('/opt/dpa4-runtime/build-manifest.json').read_text())
for item in manifest['files']:
    path = Path(item['path'])
    assert path.stat().st_size == item['bytes'], path
    assert hashlib.sha256(path.read_bytes()).hexdigest() == item['sha256'], path
print('All runtime files match the source build manifest.')
PY
"$PYTHON" "$BENCH_ROOT/generate_cases.py" --output "$WORKSPACE/cases"
common=(--checkpoint "$MODEL_DIR/model.pt" --image-ref "$IMAGE_REF"
        --image-digest "$IMAGE_DIGEST" --lammps-builtin-binary /opt/lammps-sm89/bin/lmp
        --lammps-builtin-library /opt/lammps-sm89/lib/liblammps.so.0)
for case in Ti_hcp V_bcc TiV_B2; do
    for device in cpu gpu; do
        runtime_model="$MODEL_DIR/alloytongqi.l20-sm89.pt2"
        if [[ "$device" == cpu ]]; then
            runtime_model="$MODEL_DIR/alloytongqi.cpu-x86_64.pt2"
        fi
        for mode in run0 md; do
            "$PYTHON" "$BENCH_ROOT/run_lammps_case.py" "${common[@]}" \
                --case-dir "$WORKSPACE/cases/$case" --runtime-model "$runtime_model" \
                --device "$device" --mode "$mode" --output "$WORKSPACE/runs/$case/$device/$mode" \
                --command-json '["/usr/local/bin/dpa4-lmp"]'
        done
    done
    for mode in run0 md; do
        "$PYTHON" "$BENCH_ROOT/compare_parity.py" \
            --cpu "$WORKSPACE/runs/$case/cpu/$mode/result.json" \
            --gpu "$WORKSPACE/runs/$case/gpu/$mode/result.json" \
            --output "$WORKSPACE/parity/$case/$mode.json"
    done
done
"$PYTHON" "$BENCH_ROOT/run_phonolammps_smoke.py" "${common[@]}" \
    --case-dir "$WORKSPACE/cases/Ti_hcp" --runtime-model "$MODEL_DIR/alloytongqi.l20-sm89.pt2" \
    --device gpu --output "$WORKSPACE/phonolammps/Ti_hcp/gpu" \
    --command-json '["/usr/local/bin/dpa4-phonolammps"]'
"$PYTHON" "$BENCH_ROOT/build_manifest.py" --workspace "$WORKSPACE" \
    --checkpoint "$MODEL_DIR/model.pt" --image-ref "$IMAGE_REF" --image-digest "$IMAGE_DIGEST" \
    --output "$WORKSPACE/manifest.json"
"$PYTHON" "$BENCH_ROOT/verify_manifest.py" "$WORKSPACE/manifest.json" --root "$WORKSPACE"
