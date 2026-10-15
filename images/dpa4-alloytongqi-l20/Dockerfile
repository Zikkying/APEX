# Flatten the scientific base to avoid republishing its large historical layers.
# Supply a URL serving the preserved, validated L20 runtime payload.
FROM registry.dp.tech/dptech/dp/native/prod-16664/dpa4-phonolammps@sha256:d5ce2f3a7b302a6f44faf97621e51b751fb9af53529ffc42687effb559992b3b AS assembled
ARG RUNTIME_PAYLOAD_URL
ADD ${RUNTIME_PAYLOAD_URL} /tmp/runtime-build-payload.tgz
RUN echo 'c908437b8683180e7ee98a85a04f9457998017a943deef075b71d4910a39384c  /tmp/runtime-build-payload.tgz' | sha256sum -c - \
    && tar -xzf /tmp/runtime-build-payload.tgz -C / \
    && rm /tmp/runtime-build-payload.tgz \
    && ln -sf /opt/lammps-sm89/lib/liblammps.so.0 /opt/lammps-sm89/lib/liblammps_dpa4.so
# Remove development environments, failed-job artifacts and caches, preserving
# the editable DeepMD source, native libraries, Mamba runtime and CUDA toolkit.
RUN rm -rf /root/miniconda3 /root/apex_dpa4_cu_test /root/cmake-4.0.0 \
    /root/.pixi /root/.cache /root/.triton /root/Software/k_SRME \
    /root/Software/lammps /opt/lammps-sm120 /opt/lammps-sm89/share \
    /opt/mamba/pkgs /tmp/* /var/cache/apt/archives/* \
    && bytes=$(du --apparent-size -s -B1 --exclude=/proc --exclude=/sys --exclude=/dev / | cut -f1) \
    && echo "Final runtime filesystem bytes: $bytes (limit 35000000000)" \
    && test "$bytes" -lt 35000000000
RUN /opt/mamba/bin/python -c 'import hashlib,importlib.metadata,json,pathlib; m=json.loads(pathlib.Path("/opt/dpa4-runtime/build-manifest.json").read_text()); assert all(pathlib.Path(f["path"]).stat().st_size == f["bytes"] and hashlib.sha256(pathlib.Path(f["path"]).read_bytes()).hexdigest() == f["sha256"] for f in m["files"]); assert all(importlib.metadata.version(k)==v for k,v in m["packages"].items()); print("Runtime file hashes and package versions verified")'
FROM scratch
COPY --from=assembled / /
ENV PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/opt/mamba/bin \
    HOME=/root LANG=C.UTF-8 NVIDIA_VISIBLE_DEVICES=all NVIDIA_DRIVER_CAPABILITIES=compute,utility
WORKDIR /root
CMD ["/bin/bash"]
