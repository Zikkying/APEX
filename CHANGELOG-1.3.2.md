# APEX 1.3.2

Release date: 2026-10-14

- Generated cloud jobs reuse a working image-bundled APEX 1.3.2 or newer stable
  version. Only missing/older versions trigger installation of the pinned
  `apex-flow==1.3.2` package. CLI startup failures stop submission.
- Runtime checks and submission use the same Python interpreter; the packaged
  `ensure_apex.py` helper travels with `run.sh`.
- Correct the ordinary Bohrium L20 default to `1 * NVIDIA L20_48g` while retaining
  the distinct OpenAPI Sandbox SKU `c16_m120_1 * NVIDIA L20`.
- Update the outer client and make/post image to APEX 1.3.2. Preserve the
  separate CPU/GPU calculator images and the OpenAPI dispatcher image.
- Align cloud skill instructions, examples, templates, and regression coverage
  with image reuse and the separate machine catalogs.

Existing generated jobs keep their saved scripts and machine settings. Generate
a fresh job directory using the updated skill before resubmitting; preserve
existing task outputs and check the original workflow state first.
