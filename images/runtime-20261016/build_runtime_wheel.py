"""Build a compact image-update wheel in the caller's existing Python environment.

The image provisioner verifies and restores the unchanged 30 MB source model
from its base. Normal PyPI builds still include that model.
"""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

root = Path(__file__).resolve().parents[2]
out = Path(sys.argv[1]).resolve()
out.mkdir(parents=True, exist_ok=True)
with tempfile.TemporaryDirectory(prefix='apex-runtime-wheel-') as name:
    stage = Path(name)
    shutil.copytree(root / 'apex', stage / 'apex',
                    ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '*.pt'))
    for filename in ['setup.py', 'MANIFEST.in', 'README.md', 'LICENSE']:
        if (root / filename).exists():
            shutil.copy2(root / filename, stage / filename)
    subprocess.run([sys.executable, 'setup.py', 'bdist_wheel'], cwd=stage, check=True)
    for wheel in (stage / 'dist').glob('*.whl'):
        shutil.copy2(wheel, out / wheel.name)
        print(out / wheel.name)

# Download exact small companion wheels; installation happens only in the image venv.
import hashlib
import json
from urllib.request import urlopen
for package, version, filename in [
    ("phonolammps", "0.10.1", "phonolammps-0.10.1-py3-none-any.whl"),
    ("dynaphopy", "1.18.0", "dynaphopy-1.18.0-cp310-cp310-manylinux_2_17_x86_64.manylinux2014_x86_64.whl"),
]:
    with urlopen(f"https://pypi.org/pypi/{package}/{version}/json", timeout=30) as response:
        metadata = json.load(response)
    artifact = next(item for item in metadata["urls"] if item["filename"] == filename)
    with urlopen(artifact["url"], timeout=60) as response:
        contents = response.read()
    assert hashlib.sha256(contents).hexdigest() == artifact["digests"]["sha256"]
    (out / filename).write_bytes(contents)
