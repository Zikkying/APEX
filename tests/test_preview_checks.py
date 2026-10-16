"""Scientific counterexamples for Gamma preview validation."""
import json
import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
import pytest
from monty.serialization import dumpfn
from pymatgen.core import Lattice, Structure

from apex.preview import preview_parameter_file, _validate_check_options
from apex.preview_checks import gamma_report, save_report


def fixture_tasks(root, ti_at_interface=True):
    # Same whole-cell composition, but different chemistry at the fault.
    species = ["V", "Ti", "Ti", "V"] if ti_at_interface else ["Ti", "V", "V", "Ti"]
    initial = Structure(Lattice.orthorhombic(4, 4, 28), species,
                        [[0, 0, 10], [2, 0, 12], [0, 2, 14], [2, 2, 16]], coords_are_cartesian=True)
    source = root / "POSCAR"
    initial.to(filename=source, fmt="poscar")
    tasks = []
    for index, u in enumerate([0., .5, 1.]):
        task = root / f"task.{index:06d}"; task.mkdir()
        frame = initial.copy()
        frame.translate_sites([2, 3], [4 * u, 0, 0], frac_coords=False, to_unit_cell=True)
        frame.to(filename=task / "POSCAR.tmp", fmt="poscar")
        frame.get_sorted_structure().to(filename=task / "POSCAR", fmt="poscar")
        dumpfn(u, task / "normalized_displacement.json")
        dumpfn(4., task / "slip_length.json")
        tasks.append(str(task))
    prop = SimpleNamespace(parameter={"type": "gamma", "cal_type": "relaxation"},
        cal_setting={"relax_pos": True, "relax_shape": False, "relax_vol": False},
        add_fix=["true", "true", "false"], min_distance=.2, vacuum_size=20,
        require_orthogonal_cell=False,
        gamma_geometry={"slab_geometry": {"upper_indices": [2, 3], "interface_count": 1, "material_height_angstrom": 8}})
    return prop, tasks, source


def test_interface_composition_not_whole_cell_and_sorting(tmp_path):
    reports = []
    for index, at_interface in enumerate([True, False]):
        root = tmp_path / str(index); root.mkdir()
        prop, tasks, source = fixture_tasks(root, at_interface)
        report = gamma_report(prop, tasks, source, interface_layers=1, interface_target={"Ti": 1.})
        reports.append(report)
        assert all(c["status"] == "pass" for c in report["checks"] if c["code"] == "rigid_displacement")
        # u=1 wraps to its starting position; the declared displacement survives.
        assert report["frames"][-1]["displacement"]["disp_cart"] == [4., 0., 0.]
    assert reports[0]["whole_cell_composition"]["fractions"] == reports[1]["whole_cell_composition"]["fractions"]
    assert reports[0]["interface"]["combined"]["fractions"] == {"Ti": 1.}
    assert reports[1]["interface"]["combined"]["fractions"] == {"V": 1.}
    assert any(c["code"] == "interface_target" and c["status"] == "fail" for c in reports[1]["checks"])


def test_fraction_not_silently_rounded_and_unknown_window(tmp_path):
    prop, tasks, source = fixture_tasks(tmp_path)
    report = gamma_report(prop, tasks, source, interface_layers=1, interface_target={"Ti": .1})
    target = next(c for c in report["checks"] if c["code"] == "interface_target")
    assert target["status"] == "fail"
    assert target["attainable_neighbours"] == [0., .5]
    unknown = gamma_report(prop, tasks, source)
    assert any(c["code"] == "interface_composition" and c["status"] == "unknown" for c in unknown["checks"])


@pytest.mark.parametrize("change", ["box", "xy", "static", "no_relax"])
def test_gamma_fix_xy_protocol(tmp_path, change):
    prop, tasks, source = fixture_tasks(tmp_path)
    if change == "box": prop.cal_setting["relax_shape"] = True
    elif change == "xy": prop.add_fix = ["false", "false", "false"]
    elif change == "static": prop.parameter["cal_type"] = "static"
    else: prop.cal_setting["relax_pos"] = False
    report = gamma_report(prop, tasks, source)
    assert next(c for c in report["checks"] if c["code"] == "gamma_fix_xy")["status"] == "fail"
    assert not report["constraints"]["execution_verified"]


def test_middle_frame_corruption_detected(tmp_path):
    prop, tasks, source = fixture_tasks(tmp_path)
    middle = Path(tasks[1]) / "POSCAR"
    structure = Structure.from_file(middle)
    structure.translate_sites([0], [.3, 0, 0], frac_coords=False)
    structure.to(filename=middle, fmt="poscar")
    report = gamma_report(prop, tasks, source)
    bad = [c for c in report["checks"] if c["code"] == "rigid_displacement" and c["status"] == "fail"]
    assert len(bad) == 1 and bad[0]["frame_id"] == "task.000001"


def make_parameter(root, kind="gamma", parent=False):
    for branch in ("a", "b"):
        directory = root / branch / "bcc"; directory.mkdir(parents=True)
        structure = Structure(Lattice.cubic(3.2), ["V", "V"], [[0, 0, 0], [.5, .5, .5]])
        if parent:
            structure.make_supercell([2, 2, 2])
            structure[0] = "Ti"
        structure.to(filename=directory / "POSCAR", fmt="poscar")
    prop = {"type": kind, "plane_miller": [1, 1, 0], "slip_direction": [-1, 1, 1],
            "supercell_size": [1, 1, 2], "n_steps": 2}
    if parent: prop["parent_lattice"] = "bcc"
    if kind == "gamma_surface": prop.update(n_steps_x=2, n_steps_y=2)
    payload = {"structures": ["*/bcc"], "interaction": {"type": "vasp"}, "properties": [prop]}
    path = root / "param.json"; dumpfn(payload, path)
    return path, payload


@pytest.mark.parametrize("kind,parent", [("gamma", False), ("gamma", True), ("gamma_surface", True)])
def test_real_generation_batch_reports_exports(tmp_path, kind, parent):
    path, _ = make_parameter(tmp_path, kind, parent)
    with patch("apex.preview._write_gif", side_effect=AssertionError("check-only must not render")):
        outputs = preview_parameter_file(str(path), check_only=True, interface_layers=1,
                                         export_structures=True)
    reports = [json.loads(Path(p).read_text()) for p in outputs if p.endswith(".json")]
    assert len(reports) == 2
    assert len(set(outputs)) == 4
    for report in reports:
        assert not [c for c in report["checks"] if c["status"] == "fail"]
        assert len(report["frames"]) == (9 if kind == "gamma_surface" else 3)
        assert len(list(Path(report["export_directory"]).glob("task.*/POSCAR"))) == len(report["frames"])
        assert report["source"]["path"].endswith("bcc/POSCAR")
        assert report["interface"]["combined"]["atom_count"] > 0


def test_failure_report_preserved_and_cwd_restored(tmp_path):
    path, payload = make_parameter(tmp_path)
    payload["properties"][0]["max_atoms"] = 1
    dumpfn(payload, path)
    before = os.getcwd()
    with pytest.raises(RuntimeError, match="reports:"):
        preview_parameter_file(str(path), check_only=True)
    assert os.getcwd() == before
    reports = list(tmp_path.glob("*.preview.json"))
    assert len(reports) == 2
    assert all(json.loads(p.read_text())["status"] == "fail" for p in reports)


def test_strict_requires_interface_definition(tmp_path):
    path, _ = make_parameter(tmp_path)
    with pytest.raises(RuntimeError, match="reports:"):
        preview_parameter_file(str(path), check_only=True, strict=True)
    assert len(list(tmp_path.glob("*.preview.json"))) == 2


@pytest.mark.parametrize("layers,targets,tol,width", [(0, {}, 0., .2), (None, {"Ti": .1}, 0., .2),
    (1, {"Ti": float("nan")}, 0., .2), (1, {"Ti": .6, "V": .6}, 0., .2), (1, {}, -1., .2), (1, {}, 0., 0.)])
def test_invalid_options(layers, targets, tol, width):
    with pytest.raises(ValueError): _validate_check_options(layers, targets, tol, width)


def test_middle_frame_overlap_and_missing_layers(tmp_path):
    prop, tasks, source = fixture_tasks(tmp_path)
    middle = Path(tasks[1]) / "POSCAR"
    structure = Structure.from_file(middle)
    structure.replace(0, structure[0].specie, coords=structure[1].frac_coords)
    structure.to(filename=middle, fmt="poscar")
    report = gamma_report(prop, tasks, source, interface_layers=3)
    assert any(c["code"] == "minimum_distance" and c["status"] == "fail" and c["frame_id"] == "task.000001" for c in report["checks"])
    assert any(c["code"] == "interface_composition" and c["status"] == "fail" for c in report["checks"])


def test_strict_bulk_geometry_and_report_serialization(tmp_path):
    prop, tasks, source = fixture_tasks(tmp_path)
    bulk = Structure.from_file(source)
    matrix = bulk.lattice.matrix.copy(); matrix[0, 1] = .5
    Structure(matrix, bulk.species, bulk.frac_coords).to(filename=source, fmt="poscar")
    prop.require_orthogonal_cell = True
    report = gamma_report(prop, tasks, source, interface_layers=1)
    assert next(c for c in report["checks"] if c["code"] == "bulk_orthogonal")["status"] == "fail"
    paths = save_report(report, tmp_path / "report.json")
    assert json.loads(Path(paths[0]).read_text())["status"] == "fail"
    assert "Layer compositions" in Path(paths[1]).read_text()


def test_preview_cli_flags_both_parsers():
    import sys
    from apex.preview import build_parser
    from apex.main import parse_args
    flags = ["param.json", "--check-only", "--strict", "--interface-layers", "2", "--interface-target", "Ti=0.25", "--export-structures"]
    direct = build_parser().parse_args(flags)
    with patch.object(sys, "argv", ["apex", "preview"] + flags):
        _, cli = parse_args()
    for name in ("check_only", "strict", "interface_layers", "interface_target", "export_structures"):
        assert getattr(direct, name) == getattr(cli, name)


def test_closed_surface_and_identity_mapping(tmp_path):
    path, payload = make_parameter(tmp_path, "gamma_surface", parent=True)
    payload["properties"][0]["closed_loop"] = True
    dumpfn(payload, path)
    paths = preview_parameter_file(str(path), check_only=True, interface_layers=1)
    for report_path in paths:
        if report_path.endswith(".json"):
            report = json.loads(Path(report_path).read_text())
            assert not any(c["status"] == "fail" for c in report["checks"])
