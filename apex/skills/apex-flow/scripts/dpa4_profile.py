"""Load and validate the skill's immutable DPA4 alloytongqi L20 profile."""

from __future__ import annotations

import json
import re
from pathlib import Path


DPA4_PROFILE_ID = "dpa4-alloytongqi-l20"
DPA4_PROFILE_PATH = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "dpa4_alloytongqi_l20_profile.json"
)
DPA4_IMAGE_REF_PLACEHOLDER = "__DPA4_IMAGE_REF__"
DPA4_IMAGE_DIGEST_PLACEHOLDER = "__DPA4_IMAGE_DIGEST__"
DPA4_LAMMPS_RUN_COMMAND = "/usr/local/bin/dpa4-lmp -in in.lammps"
DPA4_PHONOLAMMPS_RUN_COMMAND = (
    "/usr/local/bin/dpa4-phonolammps {input_file} -c {poscar} "
    "--dim {dim} {primitive_axes}"
)
DPA4_RUNTIME_MODEL_PATH = (
    "/opt/dpa4-runtime/models/DPA4-alloytongqi/"
    "alloytongqi.l20-sm89.pt2"
)
DPA4_RUNTIME_MODEL_SHA256 = (
    "fd837257a08121bf56f739dff6353dbbc6b06cbd2db05125211face96bcb5369"
)
DPA4_SOURCE_CHECKPOINT_PATH = (
    "/opt/dpa4-runtime/models/DPA4-alloytongqi/model.pt"
)
DPA4_SOURCE_CHECKPOINT_SHA256 = (
    "c84b268cc6191afc72bd2d5c001cbe526a0d2e04ebf6dbd7df021306e9abe9ad"
)
_IMAGE_DIGEST_RE = re.compile(r"sha256:[0-9a-f]{64}")


def load_dpa4_profile(
    *,
    require_published: bool = True,
    path: Path | str | None = None,
) -> dict:
    """Return the audited profile; reject missing or unpublished identity."""
    profile_path = Path(path) if path is not None else DPA4_PROFILE_PATH
    try:
        profile = json.loads(profile_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Cannot load DPA4 runtime profile: {profile_path}") from exc

    return validate_dpa4_profile(
        profile,
        require_published=require_published,
    )


def validate_dpa4_profile(
    profile: dict,
    *,
    require_published: bool = True,
) -> dict:
    """Validate an in-memory profile and return a shallow annotated copy."""
    if not isinstance(profile, dict):
        raise RuntimeError("DPA4 runtime profile must contain a JSON object")
    profile = dict(profile)

    if profile.get("profile_id") != DPA4_PROFILE_ID:
        raise RuntimeError(
            f"DPA4 runtime profile_id must be {DPA4_PROFILE_ID!r}"
        )
    image = profile.get("image")
    if not isinstance(image, dict):
        raise RuntimeError("DPA4 runtime profile must contain an image object")
    image_ref = str(image.get("ref", "")).strip()
    image_digest = str(image.get("digest", "")).strip().lower()
    identity_finalized = (
        bool(image_ref)
        and image_ref != DPA4_IMAGE_REF_PLACEHOLDER
        and "@" not in image_ref
        and image_digest != DPA4_IMAGE_DIGEST_PLACEHOLDER.lower()
        and _IMAGE_DIGEST_RE.fullmatch(image_digest) is not None
        and image_digest != "sha256:" + "0" * 64
    )
    qualification_status = str(profile.get("qualification_status", "")).strip()
    qualified = qualification_status == "post_snapshot_passed"
    enabled = profile.get("release_status") in ("enabled", "enabled_pending_e2e")
    published = identity_finalized and (qualified or enabled)
    profile["enabled_pending_e2e"] = enabled and not qualified and profile.get("openapi_qualification", {}).get("status") != "passed"
    profile["identity_finalized"] = identity_finalized
    profile["qualified"] = qualified
    profile["published"] = published
    if require_published and not published:
        missing = []
        if not identity_finalized:
            missing.append(
                "the released image identity is unavailable"
            )
        if not qualified:
            missing.append(
                "the exact image has no completed post-snapshot qualification"
            )
        raise RuntimeError(
            "DPA4 production profile is not published: "
            + "; ".join(missing)
            + ". A qualified release from the runtime maintainer is required. "
            "Do not edit the profile status or digest, remove validation, or "
            "substitute another potential to bypass this error."
        )

    calculator = profile.get("calculator")
    runtime = profile.get("runtime")
    compatibility = profile.get("machine_compatibility")
    if not all(isinstance(item, dict) for item in (
        calculator, runtime, compatibility
    )):
        raise RuntimeError(
            "DPA4 runtime profile is missing calculator/runtime/machine fields"
        )
    recommended = compatibility.get("recommended")
    if not isinstance(recommended, list) or len(recommended) != 1:
        raise RuntimeError("DPA4 profile must define exactly one recommended combo")
    combo = recommended[0]
    if (
        not isinstance(combo, dict)
        or combo.get("scass_type") != "1 * NVIDIA L20_48g"
        or combo.get("mpi_ranks") != 1
        or combo.get("gpu_count") != 1
    ):
        raise RuntimeError(
            "DPA4 production profile must remain one rank on one "
            "NVIDIA L20_48g"
        )
    if calculator.get("backend") != "lammps" or calculator.get("potential") != "deepmd":
        raise RuntimeError("DPA4 profile must use the LAMMPS + DeePMD calculator")
    if calculator.get("run_command") != DPA4_LAMMPS_RUN_COMMAND:
        raise RuntimeError("DPA4 profile must use the audited dpa4-lmp wrapper")
    if (
        calculator.get("phonolammps_command")
        != DPA4_PHONOLAMMPS_RUN_COMMAND
    ):
        raise RuntimeError(
            "DPA4 profile must use the audited dpa4-phonolammps wrapper template"
        )
    expected_runtime = {
        "kind": "dpa4_pt2",
        "model_in_image": True,
        "model_path": DPA4_RUNTIME_MODEL_PATH,
        "model_sha256": DPA4_RUNTIME_MODEL_SHA256,
        "source_checkpoint_path": DPA4_SOURCE_CHECKPOINT_PATH,
        "source_checkpoint_sha256": DPA4_SOURCE_CHECKPOINT_SHA256,
        "type_map": "auto",
    }
    for key, expected in expected_runtime.items():
        if runtime.get(key) != expected:
            raise RuntimeError(
                f"DPA4 profile runtime.{key} must equal {expected!r}"
            )
    return profile


def dpa4_image_name(profile: dict) -> str:
    """Return ``ref@sha256:digest`` from a published validated profile."""
    if not profile.get("published"):
        raise RuntimeError("DPA4 runtime profile image is unpublished")
    image = profile["image"]
    return f"{image['ref']}@{str(image['digest']).lower()}"


def dpa4_interaction(profile: dict) -> dict:
    """Build the exact image-resident interaction contract."""
    if not profile.get("published"):
        raise RuntimeError("DPA4 runtime profile is unpublished")
    runtime = profile["runtime"]
    return {
        "type": "deepmd",
        "deepmd_runtime": runtime["kind"],
        "model_in_image": runtime["model_in_image"],
        "model": runtime["model_path"],
        "runtime_model_sha256": runtime["model_sha256"],
        "source_checkpoint": runtime["source_checkpoint_path"],
        "source_checkpoint_sha256": runtime["source_checkpoint_sha256"],
        "type_map": runtime["type_map"],
    }


def dpa4_recommended_combo(profile: dict) -> dict:
    """Return a copy of the one audited machine contract."""
    if not profile.get("published"):
        raise RuntimeError("DPA4 runtime profile is unpublished")
    return dict(profile["machine_compatibility"]["recommended"][0])
