# Runtime images, 2026-10-16

- APEX/CPU: `registry.dp.tech/dptech/dp/native/prod-397953/397637/apex-flow-cpu:1.3.4-20261016-offline`
- General DeePMD/L20: `registry.dp.tech/dptech/dp/native/prod-397953/397637/apex-deepmd-gpu:3.1.3-20261016`
- Alloytongqi remains on its separate pinned profile. The general DeePMD 3.1.3 loader does not support that DPA4 architecture.

The GPU image is built with `Dockerfile.deepmd-gpu`. Runtime entrypoints are `/usr/local/bin/apex-lmp` and `/usr/local/bin/apex-calculator-python`; qualification covers L20 only.

The APEX/CPU build uses an existing `/opt/apex-venv`, with no Python dependency installation or new environment. Build a compact wheel using the project's existing environment:

```sh
python images/runtime-20261016/build_runtime_wheel.py /tmp/apex-runtime-dist
```

Create a build sandbox from the pinned APEX 1.3.2-post1 base in `Dockerfile.apex-cpu`, upload the wheel and `provision_cpu.sh` into `/tmp`, and run the provisioner. It verifies and retains the unchanged bundled source model by SHA256, installs APEX 1.3.4 offline, and installs Debian CPU LAMMPS, its matching Python bindings, phonoLAMMPS 0.10.1 and dynaphopy 1.18.0. After verifying the runtime, clean temporary build/test files and commit the sandbox using `bohr image commit`. Then validate a fresh sandbox from the published image. The portable Dockerfile also supports a normal Docker build with those two files in its build context.

This path avoids two observed Bohrium build limitations: external source downloads failed with SSL EOF errors, and the context-free Dockerfile API rejects inputs larger than 64 KiB. Failed build receipts were retained locally; they are not acceptance evidence.

Scientific boundaries: runtime success is not convergence. The 540-atom Ni test exits normally with finite energy but stops on zero line-search alpha; its force criterion is not satisfied. Other GPUs, arbitrary model formats, MACE/NEP/GAP/RANN/SNAP and broader phonon/MD workflows require their own validation.
