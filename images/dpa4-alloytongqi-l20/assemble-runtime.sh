#!/usr/bin/env bash
# Assemble a candidate on the same scientific base image using preserved
# artifacts from an already tested L20 build. This does not qualify the image.
set -euo pipefail
PAYLOAD=${1:?usage: assemble-runtime.sh runtime-payload.tgz}
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
[[ ! -e /opt/dpa4-runtime ]] || { echo 'Use a fresh build sandbox' >&2; exit 1; }
mkdir /opt/dpa4-runtime
tar -xzf "$PAYLOAD" -C /opt/dpa4-runtime
install -m 755 "$SCRIPT_DIR"/dpa4-* /usr/local/bin/
ln -s /opt/lammps-sm89/lib/liblammps.so.0 /opt/lammps-sm89/lib/liblammps_dpa4.so
/opt/mamba/bin/python - <<'PY'
import hashlib
import importlib.metadata
import json
from pathlib import Path

root = Path('/opt/dpa4-runtime')
manifest = json.loads((root / 'build-manifest.json').read_text())
for item in manifest['files']:
    path = Path(item['path'])
    assert path.stat().st_size == item['bytes'], path
    assert hashlib.sha256(path.read_bytes()).hexdigest() == item['sha256'], path
for name, version in manifest['packages'].items():
    assert importlib.metadata.version(name) == version, name
print('Source runtime files and package versions match; image qualification is still required.')
PY
