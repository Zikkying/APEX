import importlib.util
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "apex/skills/apex-flow/scripts/ensure_apex.py"
spec = importlib.util.spec_from_file_location("ensure_apex", SCRIPT)
bootstrap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bootstrap)


class TestImageRuntimeBootstrap(unittest.TestCase):
    def test_usable_current_or_newer_image_does_not_install(self):
        for version in ("1.3.2", "1.3.2.post1", "1.4.0"):
            with self.subTest(version=version), patch.object(
                bootstrap.metadata, "version", return_value=version
            ), patch.object(bootstrap.subprocess, "run") as run:
                bootstrap.ensure_apex()
                commands = [call.args[0] for call in run.call_args_list]
                self.assertFalse(any("pip" in cmd for cmd in commands))
                self.assertIn([sys.executable, "-m", "apex", "--help"], commands)
                self.assertTrue(all(cmd[0] == sys.executable for cmd in commands))

    def test_missing_old_or_prerelease_installs_only_pinned_release(self):
        for version in (None, "1.3.1", "1.3.2rc1"):
            with self.subTest(version=version), patch.object(
                bootstrap.metadata, "version", return_value=version,
                side_effect=bootstrap.metadata.PackageNotFoundError if version is None else None,
            ), patch.object(bootstrap.subprocess, "run") as run:
                bootstrap.ensure_apex()
                install = run.call_args_list[0].args[0]
                self.assertEqual(install[:4], [sys.executable, "-m", "pip", "install"])
                self.assertIn("apex-flow==1.3.2", install)
                self.assertNotIn("--upgrade", install)

    def test_broken_cli_fails_without_silent_reinstallation(self):
        with patch.object(bootstrap.metadata, "version", return_value="1.3.2"), patch.object(
            bootstrap.subprocess, "run", side_effect=[
                subprocess.CompletedProcess([], 0), subprocess.CalledProcessError(1, "apex")
            ]
        ) as run:
            with self.assertRaises(subprocess.CalledProcessError):
                bootstrap.ensure_apex()
            self.assertEqual(run.call_count, 2)

    def test_failed_bootstrap_does_not_continue_to_submit(self):
        with patch.object(bootstrap.metadata, "version", return_value="1.3.1"), patch.object(
            bootstrap.subprocess, "run", side_effect=subprocess.CalledProcessError(1, "pip")
        ) as run:
            with self.assertRaises(subprocess.CalledProcessError):
                bootstrap.ensure_apex()
            self.assertEqual(run.call_count, 1)
