"""Record the candidate runtime without claiming post-publication validation."""

import hashlib
import importlib.metadata
import json
import subprocess
from pathlib import Path


ROOT = Path('/opt/dpa4-runtime')
CHECKPOINT_SHA256 = 'c84b268cc6191afc72bd2d5c001cbe526a0d2e04ebf6dbd7df021306e9abe9ad'


def main():
    model_dir = ROOT / 'models/DPA4-alloytongqi'
    paths = [
        model_dir / 'model.pt',
        model_dir / 'alloytongqi.cpu-x86_64.pt2',
        model_dir / 'alloytongqi.l20-sm89.pt2',
        Path('/opt/lammps-sm89/bin/lmp'),
        Path('/opt/lammps-sm89/lib/liblammps.so.0'),
        Path('/root/Software/deepmd-kit_cpp/lib/libdeepmd_backend_ptexpt.so'),
        ROOT / 'phonolammps_native.py',
        *(Path('/usr/local/bin') / name for name in (
            'dpa4-lmp', 'dpa4-phonolammps', 'dpa4-python',
        )),
    ]
    files = [
        {
            'path': str(path),
            'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            'bytes': path.stat().st_size,
        }
        for path in paths
    ]
    packages = (
        'deepmd-kit', 'torch', 'lammps', 'phonolammps', 'phonopy', 'dpdata', 'numpy',
    )
    record = {
        'target': 'NVIDIA L20',
        'compute_capability': '8.9',
        'mpi_ranks': 1,
        'source_checkpoint_sha256': CHECKPOINT_SHA256,
        'qualification_status': 'candidate_requires_post_snapshot_benchmark',
        'base_image': 'registry.dp.tech/dptech/dp/native/prod-16664/dpa4-phonolammps:0.0.2',
        'files': files,
        'packages': {name: importlib.metadata.version(name) for name in packages},
        'gpu': subprocess.check_output([
            'nvidia-smi', '--query-gpu=name,uuid,driver_version,compute_cap',
            '--format=csv',
        ], text=True),
    }
    serialized = json.dumps(record, indent=2) + '\n'
    (ROOT / 'build-manifest.json').write_text(serialized)
    print(serialized, end='')


if __name__ == '__main__':
    main()
