#!/usr/bin/env python3
"""Run the supplied APEX wheel with the image's existing dependencies."""

import argparse
import os
from pathlib import Path
import subprocess
import sys
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wheel", type=Path, help="Path to the staged APEX wheel")
    parser.add_argument("apex_args", nargs=argparse.REMAINDER, help="Arguments for apex")
    args = parser.parse_args()
    wheel = args.wheel.resolve(strict=True)
    with tempfile.TemporaryDirectory(prefix="apex-wheel-") as target:
        subprocess.run(
            [
                sys.executable, "-m", "pip", "install", "--no-index", "--no-deps",
                "--ignore-installed", "--target", target, str(wheel),
            ],
            check=True,
        )
        env = os.environ.copy()
        python_path = env.get("PYTHONPATH")
        env["PYTHONPATH"] = os.pathsep.join(filter(None, (target, python_path)))
        return subprocess.call(
            [
                sys.executable, "-c",
                "import runpy, sys; "
                "sys.path.insert(0, sys.argv.pop(1)); "
                "import apex; "
                "print('APEX wheel source:', apex.__file__, flush=True); "
                "runpy.run_module('apex', run_name='__main__', alter_sys=True)",
                target, *args.apex_args,
            ],
            env=env,
        )


if __name__ == "__main__":
    sys.exit(main())
