#!/usr/bin/env python3
"""Validate the preinstalled image runtime without modifying its environment."""

import re
import subprocess
import sys
from importlib import metadata


REQUIRED_VERSION = "1.3.4"


def release_version(value):
    """Accept stable releases (including post releases), not unqualified RCs."""
    match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)(?:\.post\d+)?", value)
    return tuple(map(int, match.groups())) if match else None


def ensure_apex():
    try:
        installed = metadata.version("apex-flow")
    except metadata.PackageNotFoundError:
        installed = None
    version = release_version(installed) if installed else None
    if version is None or version < release_version(REQUIRED_VERSION):
        raise RuntimeError(
            f"APEX {installed or 'missing'}: require a prebuilt APEX >= {REQUIRED_VERSION} "
            "image. Regenerate the configuration and replace the outer/make-post image; "
            "do not install packages during job startup."
        )
    else:
        print(f"Reusing image APEX {installed}; no package installation.", flush=True)

    # Use the same interpreter as submission. Import-only checks miss broken
    # CLI dependencies; a stale `apex` executable elsewhere on PATH is ignored.
    probe = subprocess.run(
        [sys.executable, "-c",
         "import apex; from importlib.metadata import version; "
         "assert apex.__version__ == version('apex-flow'), 'APEX module/distribution mismatch'; "
         "print('APEX version:', apex.__version__); "
         "print('APEX source:', apex.__file__)"],
        check=True,
    )
    subprocess.run([sys.executable, "-m", "apex", "--help"], check=True,
                   stdout=subprocess.DEVNULL)
    return probe.returncode


if __name__ == "__main__":
    try:
        sys.exit(ensure_apex())
    except (subprocess.CalledProcessError, OSError, RuntimeError) as exc:
        print(f"APEX runtime is unusable: {exc}", file=sys.stderr)
        sys.exit(1)
