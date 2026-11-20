# Execution profile: MatMaster / Bohrium Cloud

This ZIP runs through a Bohrium outer submission job.

1. Prepare inputs with `scripts/generate_config.py create`, using the Agent's
   `BOHRIUM_ACCESS_KEY` and `BOHRIUM_PROJECT_ID` (or `--project-id`).
2. Use the APEX/CPU image for preflight, previews and the outer submit client.
   The Agent can prepare files without a local APEX installation.
3. Run the validated job through `python -m apex submit`. dflow dispatches the
   calculator to the image and machine selected by the generated configuration.
4. Keep the client active for monitoring and automatic result retrieval.

Follow [Submission](submission.md) for staging and the run script,
[Runtime images](runtime-images.md) for executable paths, and
[Debug](debug.md) for troubleshooting.
