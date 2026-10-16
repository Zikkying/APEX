"""Read-only diagnostics for generated Gamma geometries (no calculator execution)."""
from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path

import numpy as np
from monty.serialization import loadfn
from pymatgen.core import Structure
from scipy.optimize import linear_sum_assignment

from apex.core.property.gamma_geometry import validate_gamma_cell_geometry
from apex.core.property.gamma_slab import minimum_pair_distance


def source_record(path):
    path = Path(path)
    return {"path": str(path.resolve()), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def add_check(report, code, status, message, **details):
    report["checks"].append(dict(code=code, status=status, message=message, **details))


def composition(structure, indices):
    indices = list(map(int, indices))
    counts = dict(sorted(Counter(str(structure[i].specie) for i in indices).items()))
    return {"atom_ids": [i + 1 for i in indices], "atom_count": len(indices),
            "counts": counts, "fractions": {e: n / len(indices) for e, n in counts.items()}}


def sorted_upper_indices(task, structure, metadata):
    """Map generator IDs to final POSCAR order, never assume sorting kept IDs."""
    original = Structure.from_file(Path(task) / "POSCAR.tmp")
    upper = metadata.get("upper_indices")
    if upper is None:
        # The legacy generators use precisely this fractional-z selection.
        upper = np.where(original.frac_coords[:, 2] > 0.5)[0].tolist()
    if len(original) != len(structure):
        raise ValueError("POSCAR sorting changed atom count")
    distances = structure.lattice.get_all_distances(original.frac_coords, structure.frac_coords)
    species_match = np.array([[a.specie == b.specie for b in structure] for a in original])
    rows, cols = linear_sum_assignment(np.where(species_match, distances, 1.e12))
    if not species_match[rows, cols].all() or np.max(distances[rows, cols]) > 1.e-6:
        raise ValueError("Cannot map generator atom IDs to sorted POSCAR")
    mapping = dict(zip(rows.tolist(), cols.tolist()))
    return sorted(mapping[int(i)] for i in upper)


def layer_compositions(structure, indices, normal, tolerance):
    """Group by total layer width, avoiding chained clustering across a slab."""
    heights = structure.cart_coords @ normal
    groups = []
    for i in sorted(indices, key=lambda i: heights[i]):
        if not groups or heights[i] - heights[groups[-1][0]] > tolerance:
            groups.append([i])
        else:
            groups[-1].append(i)
    return [dict(composition(structure, group), height_angstrom=float(np.mean(heights[group])))
            for group in groups]


def constraint_check(report, prop_obj):
    parameter = prop_obj.parameter
    settings = prop_obj.cal_setting
    fixes = getattr(prop_obj, "add_fix", None)
    report["constraints"] = {"evidence": "resolved_configuration_only",
        "add_fix": fixes, "cal_type": parameter.get("cal_type"), "cal_setting": settings,
        "calculator_input_verified": False, "execution_verified": False}
    if parameter.get("type") != "gamma":
        return
    fixed = list(fixes) == ["true", "true", "false"] if isinstance(fixes, (list, tuple)) else False
    valid = (parameter.get("cal_type") == "relaxation" and fixed
             and settings.get("relax_pos") is True
             and settings.get("relax_shape") is False and settings.get("relax_vol") is False)
    add_check(report, "gamma_fix_xy", "pass" if valid else "fail",
              "Gamma line requires fixed x/y, z-only ionic relaxation and a fixed cell; this checks configuration, not execution.")


def gamma_report(prop_obj, tasks, source, *, interface_layers=None,
                 interface_target=None, composition_tolerance=1.e-6, layer_tolerance=0.2):
    report = {"schema_version": 1, "scope": "generated_geometry_and_resolved_configuration",
              "source": source_record(source), "relaxation_history": "unknown",
              "resolved_parameters": prop_obj.parameter, "checks": [], "frames": [],
              "atom_id_convention": "1-based row in each exported POSCAR"}
    geometry = getattr(prop_obj, "gamma_geometry", None) or {}
    # The generator source path points into a temporary staging directory.
    report["geometry"] = dict(geometry, source_structure=report["source"])
    constraint_check(report, prop_obj)
    bulk = Structure.from_file(source)
    report["bulk"] = dict(validate_gamma_cell_geometry(bulk), formula=bulk.composition.formula,
                          composition=composition(bulk, range(len(bulk))))
    require_orthogonal = getattr(prop_obj, "require_orthogonal_cell", False)
    if require_orthogonal:
        add_check(report, "bulk_orthogonal", "pass" if report["bulk"]["orthogonal"] else "fail",
                  "Strict orthogonal protocol checks the source bulk metric as well as the slab.")
    metadata = geometry.get("slab_geometry", {})
    baseline = None
    for task in tasks:
        task = Path(task)
        structure = Structure.from_file(task / "POSCAR")
        metric = validate_gamma_cell_geometry(structure)
        frame = {"task_id": task.name, "structure_sha256": source_record(task / "POSCAR")["sha256"],
                 "cell": metric, "atom_count": len(structure),
                 "minimum_pair_distance_angstrom": minimum_pair_distance(structure)}
        if not np.isfinite(frame["minimum_pair_distance_angstrom"]):
            frame["minimum_pair_distance_angstrom"] = None
        displacement_file = task / "displacement.json"
        if displacement_file.exists():
            frame["displacement"] = loadfn(displacement_file)
        else:
            u = float(loadfn(task / "normalized_displacement.json"))
            frame["displacement"] = {"u": u, "disp_cart": [u * float(loadfn(task / "slip_length.json")), 0., 0.]}
        # Pymatgen POSCAR serialization reverses all lattice vectors for a
        # left-handed cell, retaining fractional coordinates. Transform the
        # generator's Cartesian displacement into that exported coordinate frame.
        generated_cell = metadata.get("slab_lattice") or metadata.get("cell_geometry", {}).get("lattice_matrix_angstrom")
        if generated_cell is not None:
            transform = np.linalg.solve(np.asarray(generated_cell), structure.lattice.matrix)
            frame["generator_to_exported_cartesian"] = transform.tolist()
            add_check(report, "serialization_metric", "pass" if np.allclose(transform @ transform.T, np.eye(3), atol=1.e-7, rtol=0) else "fail",
                      "Exported coordinate transformation must preserve lengths and angles.", frame_id=task.name)
            original_disp = frame["displacement"]["disp_cart"]
            frame["displacement"]["generator_disp_cart"] = original_disp
            frame["displacement"]["disp_cart"] = (np.asarray(original_disp) @ transform).tolist()
        report["frames"].append(frame)
        distance = frame["minimum_pair_distance_angstrom"]
        add_check(report, "minimum_distance", "pass" if distance is not None and distance >= prop_obj.min_distance else "fail",
                  "Periodic pair distance against configured min_distance (angstrom).",
                  frame_id=task.name, observed=distance, expected=prop_obj.min_distance)
        add_check(report, "slab_orthogonal", "pass" if metric["zero_tilt"] else ("fail" if require_orthogonal else "warn"),
                  "Orthogonality and Cartesian-z normal; no lattice deformation is applied.", frame_id=task.name)
        cell = structure.lattice.matrix
        normal = np.cross(cell[0], cell[1]); normal /= np.linalg.norm(normal)
        if normal @ cell[2] < 0:
            normal *= -1
        disp = np.array(frame["displacement"]["disp_cart"])
        add_check(report, "in_plane_displacement", "pass" if abs(float(disp @ normal)) < 1.e-7 else "fail",
                  "Displacement must lie in the fault plane.", frame_id=task.name)
        if prop_obj.parameter.get("type") == "gamma":
            add_check(report, "fix_xy_normal", "pass" if abs(normal[2]) > 1 - 1.e-8 else "fail",
                      "Cartesian z must be the fault normal for fix_xy.", frame_id=task.name)
        heights = structure.cart_coords @ normal
        height = abs(float(cell[2] @ normal))
        frame["dimensions"] = {"area_angstrom2": float(np.linalg.norm(np.cross(cell[0], cell[1]))),
            "cell_normal_height_angstrom": height, "atomic_span_angstrom": float(np.ptp(heights)),
            "boundary_gap_angstrom": height - float(np.ptp(heights)),
            "added_vacuum_angstrom": float(prop_obj.vacuum_size),
            "material_height_angstrom": metadata.get("material_height_angstrom"),
            "interface_count": metadata.get("interface_count")}
        if prop_obj.vacuum_size > 0:
            add_check(report, "vacuum_gap", "pass" if frame["dimensions"]["boundary_gap_angstrom"] >= prop_obj.vacuum_size - 1.e-6 else "fail",
                      "Measured boundary gap must accommodate the configured added vacuum.",
                      frame_id=task.name, observed=frame["dimensions"]["boundary_gap_angstrom"], expected=prop_obj.vacuum_size)
        # Use the zero-displacement structure for identity and interface composition.
        if np.linalg.norm(disp) < 1.e-10:
            baseline = (task, structure, normal)
    if baseline is None:
        add_check(report, "zero_reference", "fail", "No zero-displacement reference was generated.")
        return report
    task, reference, normal = baseline
    try:
        upper = sorted_upper_indices(task, reference, metadata)
        lower = sorted(set(range(len(reference))) - set(upper))
        if not upper or not lower:
            raise ValueError("Fault must have atoms on both sides")
    except (ValueError, FileNotFoundError) as exc:
        add_check(report, "atom_groups", "fail", str(exc))
        return report
    heights = reference.cart_coords @ normal
    if max(heights[lower]) >= min(heights[upper]):
        add_check(report, "fault_partition", "fail", "Moving/fixed groups do not form two separated sides along the slab normal.")
        return report
    add_check(report, "fault_partition", "pass", "Moving and fixed groups lie on opposite sides of an internal gap.")
    report["fault_gap_angstrom"] = float(min(heights[upper]) - max(heights[lower]))
    report["fault_center_angstrom"] = float((min(heights[upper]) + max(heights[lower])) / 2)
    add_check(report, "group_balance", "pass" if len(upper) == len(lower) else "warn",
              "Moving/fixed atom counts; an explicitly shifted fault may be asymmetric.",
              observed={"moving": len(upper), "fixed": len(lower)})
    report["groups"] = {"moving": composition(reference, upper), "fixed": composition(reference, lower)}
    report["layers"] = {"lower": layer_compositions(reference, lower, normal, layer_tolerance),
                        "upper": layer_compositions(reference, upper, normal, layer_tolerance)}
    report["layer_tolerance_angstrom"] = layer_tolerance
    report["whole_cell_composition"] = composition(reference, range(len(reference)))
    # Verify final POSCAR ordering and rigid displacements against the same IDs.
    for frame, task_path in zip(report["frames"], tasks):
        current = Structure.from_file(Path(task_path) / "POSCAR")
        valid = (len(current) == len(reference) and current.species == reference.species
                 and np.allclose(current.lattice.matrix, reference.lattice.matrix, atol=1.e-7, rtol=0))
        error = None
        if valid:
            expected = reference.cart_coords.copy()
            expected[upper] += np.array(frame["displacement"]["disp_cart"])
            frac = current.lattice.get_fractional_coords(expected)
            distances = current.lattice.get_all_distances(frac, current.frac_coords)
            error = float(np.max(np.diag(distances)))
            valid = error < 1.e-6
        frame["rigid_displacement_max_error_angstrom"] = error
        add_check(report, "rigid_displacement", "pass" if valid else "fail",
                  "Same atom IDs, species and cell; only the moving group receives the prescribed displacement, modulo PBC.",
                  frame_id=frame["task_id"], observed=error)
    if interface_layers is None:
        add_check(report, "interface_composition", "unknown",
                  "Specify --interface-layers to select layers on each side of the internal fault; whole-cell composition is not interface composition.")
    elif any(len(report["layers"][side]) < interface_layers for side in ("lower", "upper")):
        add_check(report, "interface_composition", "fail", "Requested more interface layers than available on a side.")
    else:
        selected = {"lower": report["layers"]["lower"][-interface_layers:],
                    "upper": report["layers"]["upper"][:interface_layers]}
        side_ids = {side: [i - 1 for layer in layers for i in layer["atom_ids"]] for side, layers in selected.items()}
        interface = {side: composition(reference, ids) for side, ids in side_ids.items()}
        interface["combined"] = composition(reference, side_ids["lower"] + side_ids["upper"])
        interface["layers_per_side"] = interface_layers
        interface["target_fractions"] = interface_target or {}
        interface["fraction_tolerance"] = composition_tolerance
        report["interface"] = interface
        add_check(report, "interface_selection", "pass", "Selected nearest layers on each side of the internal fault in the zero frame.")
        for element, target in (interface_target or {}).items():
            actual = interface["combined"]["fractions"].get(element, 0.)
            count = interface["combined"]["atom_count"]
            candidates = sorted({int(np.floor(target * count)), int(np.ceil(target * count))})
            add_check(report, "interface_target", "pass" if abs(actual - target) <= composition_tolerance else "fail",
                      f"Combined interface fraction of {element}; target is not rounded silently.",
                      observed=actual, expected=target, tolerance=composition_tolerance,
                      atom_count=count, attainable_neighbours=[n / count for n in candidates])
        if not interface_target:
            add_check(report, "interface_target", "unknown", "Interface composition measured; no target fraction supplied.")
    if prop_obj.parameter.get("type") == "gamma" and len(tasks) <= 2:
        add_check(report, "path_sampling", "warn", "Sparse displacement points do not establish the maximum GSFE along a full path.")
    return report


def save_report(report, path):
    """Persist diagnostics even when a gate fails; return both artifact paths."""
    path = Path(path)
    statuses = [c["status"] for c in report["checks"]]
    report["status"] = "fail" if "fail" in statuses else "incomplete" if "unknown" in statuses else "warn" if "warn" in statuses else "pass"
    report["check_gate_passed"] = "fail" not in statuses and not (report.get("strict_mode") and "unknown" in statuses)
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False, default=lambda x: x.tolist() if isinstance(x, np.ndarray) else x.item()) + "\n")
    md = path.with_suffix(".md")
    lines = ["# Gamma preview checks", "", f"Status: **{report['status']}**", "",
             "Scope: generated geometry and resolved configuration; no calculator execution or energy validation.", "",
             f"Source: `{report['source']['path']}`", "", "| Check | Status | Frame | Detail |", "| --- | --- | --- | --- |"]
    for check in report["checks"]:
        message = check["message"].replace("|", "\\|").replace("\n", " ")
        if "observed" in check:
            message += " Observed: " + str(check["observed"]) + "; expected: " + str(check.get("expected", "see check definition"))
        lines.append(f"| {check['code']} | {check['status']} | {check.get('frame_id', '')} | {message} |")
    if "layers" in report:
        lines += ["", "## Layer compositions (zero displacement)", "",
                  "| Side | Height (Å) | Atoms | Element counts |", "| --- | --- | --- | --- |"]
        for side, layers in report["layers"].items():
            for layer in layers:
                lines.append(f"| {side} | {layer['height_angstrom']:.6f} | {layer['atom_count']} | {layer['counts']} |")
    if "interface" in report:
        lines += ["", "## Interface composition", "", "```json", json.dumps(report["interface"], indent=2), "```"]
    md.write_text("\n".join(lines) + "\n")
    return [str(path), str(md)]
