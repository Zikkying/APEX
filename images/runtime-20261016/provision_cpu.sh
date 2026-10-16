#!/bin/bash
# Run inside the existing APEX image's build sandbox after uploading the wheel.
set -euo pipefail
PY=/opt/apex-venv/bin/python
"$PY" -c 'from apex.skills import get_skill_root; import hashlib,shutil; p=get_skill_root()/"models/DPA4-alloytongqi/model.pt"; assert hashlib.sha256(p.read_bytes()).hexdigest()=="c84b268cc6191afc72bd2d5c001cbe526a0d2e04ebf6dbd7df021306e9abe9ad"; shutil.copy2(p,"/tmp/apex-model.pt")'
"$PY" -m pip install --force-reinstall --no-index --no-deps /tmp/apex_flow-1.3.4-py3-none-any.whl /tmp/phonolammps-0.10.1-py3-none-any.whl /tmp/dynaphopy-1.18.0-cp310-cp310-manylinux_2_17_x86_64.manylinux2014_x86_64.whl
"$PY" -c 'from apex.skills import get_skill_root; import shutil; p=get_skill_root()/"models/DPA4-alloytongqi/model.pt"; p.parent.mkdir(parents=True,exist_ok=True); shutil.move("/tmp/apex-model.pt",p); import apex; from importlib.metadata import version; assert apex.__version__==version("apex-flow")=="1.3.4"'
printf '%s\n' 'deb https://mirrors.aliyun.com/debian trixie main' 'deb https://mirrors.aliyun.com/debian trixie-updates main' 'deb https://mirrors.aliyun.com/debian-security trixie-security main' > /tmp/apex-sources.list
apt-get -o Dir::Etc::sourcelist=/tmp/apex-sources.list -o Dir::Etc::sourceparts=- -o Acquire::http::Timeout=30 -o Acquire::Retries=1 update
apt-get -o Dir::Etc::sourcelist=/tmp/apex-sources.list -o Dir::Etc::sourceparts=- -o Acquire::http::Timeout=30 -o Acquire::Retries=1 install -y --no-install-recommends lammps python3-lammps liblammps-dev
"$PY" -c 'import shutil,sysconfig; from pathlib import Path; shutil.copytree("/usr/lib/python3/dist-packages/lammps",Path(sysconfig.get_paths()["purelib"])/"lammps",dirs_exist_ok=True); import phonolammps; from lammps import lammps; l=lammps(cmdargs=["-screen","none","-log","none"]); print(phonolammps.__version__,l.version()); l.close()'
/opt/apex-venv/bin/phonolammps --help >/dev/null
/usr/bin/lmp -h | grep -q 'eam/alloy'
"$PY" -m apex --help >/dev/null
"$PY" -c 'import numpy,monty,pymatgen,dpdata,dflow,dpdispatcher'
rm -rf /var/lib/apt/lists/* /var/cache/apt/archives/*.deb /root/.cache/pip
rm /tmp/apex_flow-1.3.4-py3-none-any.whl /tmp/phonolammps-0.10.1-py3-none-any.whl /tmp/dynaphopy-1.18.0-cp310-cp310-manylinux_2_17_x86_64.manylinux2014_x86_64.whl
echo CPU_RUNTIME_PROVISIONED
