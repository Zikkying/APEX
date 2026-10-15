# DPA4-alloytongqi L20 runtime candidate

Work in progress: not qualified for production until the published image digest
passes the L20 v3 benchmark. Do not change the production profile based on a
successful source-sandbox run alone.

Publication is blocked as of 2026-10-15: Bohrium snapshots 178312 and 178321
(L20 source sandbox) and 178333 (clean CPU assembly) returned status 3 with
empty build logs. No immutable image digest or fresh-image acceptance was
obtained. The profile remains locked; these changes are not a production
runtime release.

Base: `registry.dp.tech/dptech/dp/native/prod-16664/dpa4-phonolammps:0.0.2`.
Target: single NVIDIA L20, compute capability 8.9, one MPI rank.
Source checkpoint SHA-256:
`c84b268cc6191afc72bd2d5c001cbe526a0d2e04ebf6dbd7df021306e9abe9ad`.

The base contains a native DeepMD LAMMPS build at `/opt/lammps-sm89` and
DeepMD shared libraries at `/root/Software/deepmd-kit_cpp/lib`. The runtime
uses the existing `/opt/mamba` environment; the wrappers install no packages.

Freeze with the PyTorch backend (`dp --pt freeze`), not `--pt-expt`: the latter
rejects this checkpoint's `dim_case_embd=23`. Set the same inference flags as
the wrappers before freezing. Compile CPU and GPU artifacts independently.
Wait for exit zero before consuming the output: the initial `.pt2` appears
before the second compilation and metadata packaging have completed.

Initial measurements and raw receipts are under
`output/dpa4-l20-20261015/`. These source-sandbox observations are preliminary.
`pre-snapshot-evidence.json` preserves the measured timings, CPU/GPU numerical
differences, runtime file hashes and scope. It is not a passed image manifest.

`build-in-sandbox.sh /path/to/model.pt` reproduces the preparation in a fresh
L20 instance with the existing packages. Upload this directory and the exact
checkpoint first. The script checks GPU identity and checkpoint hash, refuses
to overwrite runtime artifacts, and records a build manifest. Compilation
hashes can differ between builds; every new artifact needs a new benchmark.

For a clean image assembly, archive `/opt/dpa4-runtime` from the tested build,
start a CPU sandbox with the same base, and run
`assemble-runtime.sh runtime-payload.tgz`. It restores the preserved artifacts
and checks every recorded runtime file and package version. Remove the uploaded
archive before committing. GPU driver libraries may be placeholders on the CPU
builder; do not run or qualify the GPU binary there. After publication, start a
new L20 sandbox from the registry-resolved digest and upload the current
benchmark harness. Run `qualify-image.sh BENCH_ROOT NEW_WORKSPACE REF DIGEST`.
This checks the restored files and executes the complete qualification matrix.

`dpa4-python quick-checkpoint-benchmark.py` reproduces the preliminary FeCoNi
FCC 4/32/108-atom timing probe (one cold and five warm calls). It measures raw
checkpoint inference only. Do not use it to qualify another GPU's `.pt2` or to
infer large-system throughput or scientific accuracy.

This is the calculator image. APEX orchestration uses its separate APEX image
and dedicated `/opt/apex-venv`; scientific package installation is unnecessary
in production jobs. Do not substitute the deprecated `pt-expt` export path
merely to suppress the native backend's deprecation message.

## Dockerfile publication fallback

`Dockerfile` pins the scientific base digest, restores the preserved runtime
payload, removes redundant environments and development artifacts, verifies all
runtime hashes and package versions, and copies the final
filesystem into a single-stage image. This removes inherited layer history;
it does not change or qualify the scientific runtime. The final image must still
pass `qualify-image.sh` in a fresh L20 sandbox.

The payload is a gzip tar archive rooted at `/` containing only
`opt/dpa4-runtime/` and the three `usr/local/bin/dpa4-*` wrappers listed in the
build manifest. Supply `RUNTIME_PAYLOAD_URL` to the builder. Its bytes must match
the SHA-256 pinned in the Dockerfile. For Bohrium builders without build-argument
support, render a temporary Dockerfile with that URL as the ARG default.
The download endpoint may be removed once the ADD step completes; it must not
serve credentials or unrelated workspace files.

Diagnostic build 178341 and untrimmed candidate 178347 were superseded and
deleted. Initial trimmed candidate 178354 was also withdrawn after dependency review.
Revised candidate 178359 was submitted on 2026-10-15. Receipts and
logs are stored in `output/dpa4-l20-20261015/`.
The diagnostic log confirms successful base-registry authentication and large
historical image layers (49.41 GB of compressed layer sizes visible in the log).
This does not establish the cause of the earlier
empty-log snapshot failures.

The publication limit is 40 GB. The Dockerfile fails if the final filesystem is
35,000,000,000 bytes or larger before flattening. An initial CPU audit measured
26,901,603,302 bytes, but missed native dependencies in Miniconda. The corrected
recipe preserves `/root/miniconda3/lib/lib*.so*` (157,705,560 bytes), including
LAMMPS dependencies JPEG, PNG, FFTW and zlib. A real L20 sandbox measured
27,938,301,086 bytes with models and passed the 108-atom FeCoNi single-point
run with matching runtime hashes. This remains source-sandbox evidence. Retained
components include `/opt/mamba`, CUDA 12.8, `/opt/lammps-sm89`, editable DeepMD
source and its native libraries. Removed components include the separate
Python/development content of the 7.84 GB Miniconda environment, 4.21 GB APEX development/test tree, CMake test
sources, unrelated LAMMPS build sources/SM120 installation and compiler caches.
A sandbox filesystem audit must not use `du -x`: Bohrium's lazy image files can
have a different filesystem device ID and would be skipped. Use apparent sizes
with `/proc`, `/sys` and `/dev` excluded. Final registry size and fresh-image GPU
qualification remain required.
