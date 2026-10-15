#!/usr/bin/env bash
# Run in a fresh L20 sandbox based on the documented scientific base image.
# Reuses existing scientific packages; does not install Python dependencies.
set -euo pipefail
SOURCE_CHECKPOINT=${1:?usage: build-in-sandbox.sh /path/to/model.pt}
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
MODEL_DIR=/opt/dpa4-runtime/models/DPA4-alloytongqi
EXPECTED=c84b268cc6191afc72bd2d5c001cbe526a0d2e04ebf6dbd7df021306e9abe9ad
ACTUAL=$(sha256sum "$SOURCE_CHECKPOINT" | cut -d ' ' -f 1)
[[ "$ACTUAL" == "$EXPECTED" ]] || { echo 'checkpoint hash mismatch' >&2; exit 1; }
/opt/mamba/bin/python - <<'PY'
import torch
assert torch.cuda.is_available()
assert torch.cuda.device_count() == 1
assert torch.cuda.get_device_name(0) == 'NVIDIA L20'
assert torch.cuda.get_device_capability(0) == (8, 9)
PY
mkdir -p "$MODEL_DIR"
if compgen -G "$MODEL_DIR/*.pt2" >/dev/null; then
    echo 'Existing runtime artifacts found; preserve them and use a fresh build directory.' >&2
    exit 1
fi
if [[ "$(readlink -f "$SOURCE_CHECKPOINT")" != "$MODEL_DIR/model.pt" ]]; then
    install -m 644 "$SOURCE_CHECKPOINT" "$MODEL_DIR/model.pt"
fi
install -m 755 "$SCRIPT_DIR"/dpa4-* /usr/local/bin/
install -m 644 "$SCRIPT_DIR/phonolammps_native.py" /opt/dpa4-runtime/
ln -s /opt/lammps-sm89/lib/liblammps.so.0 /opt/lammps-sm89/lib/liblammps_dpa4.so
export OMP_NUM_THREADS=1 DP_INTRA_OP_PARALLELISM_THREADS=1 DP_INTER_OP_PARALLELISM_THREADS=1
export DP_COMPILE_INFER=0 DP_AMP_INFER=0 DP_TRITON_INFER=0 DP_CUTE_INFER=0 DP_TF32_INFER=0
CUDA_VISIBLE_DEVICES=0 /opt/mamba/bin/dp --pt freeze \
    -c "$MODEL_DIR/model.pt" -o "$MODEL_DIR/alloytongqi.l20-sm89.pt2" \
    > /opt/dpa4-runtime/freeze-l20.log 2>&1
CUDA_VISIBLE_DEVICES='' DEVICE=cpu /opt/mamba/bin/dp --pt freeze \
    -c "$MODEL_DIR/model.pt" -o "$MODEL_DIR/alloytongqi.cpu-x86_64.pt2" \
    > /opt/dpa4-runtime/freeze-cpu.log 2>&1
/opt/mamba/bin/python "$SCRIPT_DIR/record_runtime.py"
echo 'Candidate built. Run the full benchmark, commit the image, then rerun on a fresh exact-digest instance.'
