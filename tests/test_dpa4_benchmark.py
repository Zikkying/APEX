import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path


BENCHMARK_DIR = (
    Path(__file__).resolve().parents[1]
    / "apex"
    / "skills"
    / "apex-flow"
    / "benchmarks"
    / "dpa4-alloytongqi"
)
sys.path.insert(0, str(BENCHMARK_DIR))

from run_phonolammps_smoke import (  # noqa: E402
    _poscar_atom_count,
    validate_force_constants,
)
from benchmark_lib import normalize_image_identity, l20_environment_reasons, probe_builtin_lammps  # noqa: E402


class TestImageIdentity(unittest.TestCase):
    def test_builtin_requires_actual_library_link(self):
        with tempfile.TemporaryDirectory() as directory:
            binary = Path(directory) / "lmp"
            library = Path(directory) / "liblammps.so.0"
            binary.write_bytes(b"binary")
            library.write_bytes(b"library")
            help_result = {"exit_code": 0, "stdout": "deepmd deepmd/kk", "stderr": ""}
            link_result = {"exit_code": 0, "stdout": str(library.resolve()), "stderr": ""}
            with patch("benchmark_lib._run_probe", side_effect=[help_result, link_result]):
                evidence, reasons = probe_builtin_lammps(str(binary), str(library))
            self.assertTrue(evidence["verified"])
            self.assertEqual(reasons, [])
            link_result["stdout"] = "/wrong/liblammps.so.0"
            with patch("benchmark_lib._run_probe", side_effect=[help_result, link_result]):
                _, reasons = probe_builtin_lammps(str(binary), str(library))
            self.assertIn("LAMMPS_BUILTIN_LIBRARY_NOT_LINKED", reasons)
            link_result["stdout"] = f"liblammps.so.0 => {library.resolve()}.other (0x1234)"
            with patch("benchmark_lib._run_probe", side_effect=[help_result, link_result]):
                _, reasons = probe_builtin_lammps(str(binary), str(library))
            self.assertIn("LAMMPS_BUILTIN_LIBRARY_NOT_LINKED", reasons)

    def test_l20_architecture_must_match(self):
        gpu = dict(index="0", name="NVIDIA L20", uuid="GPU-test", driver_version="580", compute_capability="8.9", memory_mib=46068)
        self.assertEqual(l20_environment_reasons({"gpu_inventory": [gpu]}, "0"), [])
        gpu["compute_capability"] = "7.5"
        self.assertIn("L20_COMPUTE_CAPABILITY_NOT_8_9", l20_environment_reasons({"gpu_inventory": [gpu]}, "0"))
        gpu["name"] = "NVIDIA RTX 4090"
        gpu["compute_capability"] = "8.9"
        self.assertTrue(l20_environment_reasons({"gpu_inventory": [gpu]}, "0"))

    def test_zero_digest_cannot_qualify_image(self):
        _, reasons = normalize_image_identity("registry.example/runtime:tag", "sha256:" + "0" * 64)
        self.assertIn("IMAGE_DIGEST_MISSING_OR_INVALID", reasons)

    def test_conflicting_digest_is_rejected(self):
        _, reasons = normalize_image_identity("registry.example/runtime@sha256:" + "a" * 64, "sha256:" + "b" * 64)
        self.assertIn("IMAGE_DIGEST_CONFLICT", reasons)


def _force_constants_text(atom_count: int = 2) -> str:
    lines = [str(atom_count)]
    for first in range(1, atom_count + 1):
        for second in range(1, atom_count + 1):
            lines.extend(
                (
                    "",
                    f"{first} {second}",
                    "1.0 0.0 0.0",
                    "0.0 1.0 0.0",
                    "0.0 0.0 1.0",
                )
            )
    return "\n".join(lines) + "\n"


class TestDPA4ForceConstantsValidation(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)

    def tearDown(self):
        self.tempdir.cleanup()

    def _write(self, text: str) -> Path:
        path = self.root / "FORCE_CONSTANTS"
        path.write_text(text, encoding="utf-8")
        return path

    def test_complete_finite_force_constants_pass(self):
        result = validate_force_constants(self._write(_force_constants_text()), 2)
        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["atom_count"], 2)
        self.assertEqual(result["matrix_blocks"], 4)
        self.assertEqual(result["finite_values"], 36)
        self.assertIsNone(result["error"])

    def test_atom_count_mismatch_fails(self):
        with self.assertRaisesRegex(ValueError, "atom count 2 != expected 3"):
            validate_force_constants(self._write(_force_constants_text()), 3)

    def test_phonopy_two_count_full_header_passes(self):
        text = _force_constants_text().replace("2\n", "2 2\n", 1)
        self.assertEqual(validate_force_constants(self._write(text), 2)["matrix_blocks"], 4)

    def test_compact_force_constants_rejected(self):
        text = _force_constants_text().replace("2\n", "2 16\n", 1)
        with self.assertRaisesRegex(ValueError, "not a full square matrix"):
            validate_force_constants(self._write(text), 2)

    def test_truncated_matrix_fails(self):
        text = _force_constants_text().rsplit("0.0 0.0 1.0", 1)[0]
        with self.assertRaisesRegex(ValueError, "truncated in matrix block"):
            validate_force_constants(self._write(text), 2)

    def test_non_finite_matrix_fails(self):
        text = _force_constants_text().replace("1.0 0.0 0.0", "nan 0.0 0.0", 1)
        with self.assertRaisesRegex(ValueError, "non-finite value"):
            validate_force_constants(self._write(text), 2)

    def test_trailing_data_fails(self):
        with self.assertRaisesRegex(ValueError, "trailing non-empty data"):
            validate_force_constants(
                self._write(_force_constants_text() + "unexpected\n"), 2
            )

    def test_poscar_atom_count_vasp5(self):
        poscar = self.root / "POSCAR"
        poscar.write_text(
            "TiV\n1.0\n1 0 0\n0 1 0\n0 0 1\nTi V\n1 2\nDirect\n"
            "0 0 0\n0.5 0.5 0.5\n0.25 0.25 0.25\n",
            encoding="utf-8",
        )
        self.assertEqual(_poscar_atom_count(poscar), 3)


if __name__ == "__main__":
    unittest.main()
