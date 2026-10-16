# APEX 1.3.4

- Use the updated APEX/CPU image for workflow preparation, post-processing and classical LAMMPS, and a separate general DeePMD/L20 image for compatible TensorFlow and PyTorch models.
- Preserve the configured calculator image for phonon and Grüneisen tasks. The dedicated alloytongqi PT2 contract still selects its pinned image and wrappers.
- Validate the preinstalled APEX runtime instead of downloading or upgrading packages at job startup. Regenerate configuration for existing jobs to select the new image.
- Synchronize skill templates, examples, interpreter paths and machine recommendations. MACE, NEP, GAP, RANN and SNAP require an explicit compatible custom image.
- Fix the skill YAML frontmatter so MatMaster can load the updated instructions.

Runtime validation and scientific scope are recorded in `images/runtime-20261016/qualification.json`. Runtime success does not establish convergence or compatibility with every model and GPU.

- Use absolute phonoLAMMPS executable paths for the new images so sandbox login-shell PATH resets cannot break phonon/Gruneisen submission.
