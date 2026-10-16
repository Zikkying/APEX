"""Shared structure/type-map normalization for native and workflow preparation."""
import os
import glob
import json
from typing import List

def _infer_type_map_from_structure_file(structure_file: str) -> dict:
    structure_name = os.path.basename(structure_file)
    symbols = []
    if structure_name in {"POSCAR", "CONTCAR"}:
        from pymatgen.io.vasp import Poscar

        poscar = Poscar.from_file(structure_file)
        symbols = [str(item) for item in poscar.site_symbols]
    else:
        from pymatgen.core import Structure

        structure = Structure.from_file(structure_file)
        seen = set()
        for site in structure.sites:
            symbol = str(site.specie)
            if symbol not in seen:
                seen.add(symbol)
                symbols.append(symbol)

    if not symbols:
        raise RuntimeError(f"Cannot infer type_map from structure file: {structure_file}")
    return {symbol: idx for idx, symbol in enumerate(symbols)}


def _resolve_structure_files(param_path: str, structures: List[str]) -> List[str]:
    """Resolve every structure file used to build a complete LAMMPS type map."""
    base_dir = os.path.dirname(os.path.abspath(param_path))
    structure_files = []
    seen_files = set()

    def add_file(path: str) -> None:
        absolute_path = os.path.abspath(path)
        if absolute_path not in seen_files:
            seen_files.add(absolute_path)
            structure_files.append(absolute_path)

    for pattern in structures:
        if os.path.isabs(pattern):
            search_patterns = [pattern]
        else:
            search_patterns = [os.path.join(base_dir, pattern), pattern]

        matches = []
        seen_matches = set()
        for search_pattern in search_patterns:
            for match in sorted(glob.glob(search_pattern)):
                absolute_match = os.path.abspath(match)
                if absolute_match not in seen_matches:
                    seen_matches.add(absolute_match)
                    matches.append(absolute_match)
        for match in matches:
            if os.path.isdir(match):
                for candidate in ("POSCAR", "CONTCAR", "STRU"):
                    candidate_path = os.path.join(match, candidate)
                    if os.path.isfile(candidate_path):
                        add_file(candidate_path)
                        break
                else:
                    nested_poscars = sorted(
                        glob.glob(os.path.join(match, "conf_*", "POSCAR"))
                    )
                    for nested_poscar in nested_poscars:
                        add_file(nested_poscar)
            elif os.path.isfile(match):
                add_file(match)

    if structure_files:
        return structure_files
    raise RuntimeError(
        "Cannot infer interaction.type_map automatically: no structure file found "
        f"for patterns {structures} from {param_path}"
    )


def _infer_type_map_from_structure_files(structure_files: List[str]) -> dict:
    symbols = []
    seen = set()
    for structure_file in structure_files:
        for symbol in _infer_type_map_from_structure_file(structure_file):
            if symbol not in seen:
                seen.add(symbol)
                symbols.append(symbol)
    if not symbols:
        raise RuntimeError("Cannot infer interaction.type_map from empty structures")
    return {symbol: idx for idx, symbol in enumerate(symbols)}


def _iter_lammps_interactions_for_type_map(parameter_dict: dict):
    """Yield each distinct LAMMPS interaction that may need CLI expansion."""
    seen = set()
    interactions = [parameter_dict.get("interaction")]
    for prop in parameter_dict.get("properties") or []:
        if not isinstance(prop, dict):
            continue
        cal_setting = prop.get("cal_setting") or {}
        if isinstance(cal_setting, dict):
            interactions.append(cal_setting.get("overwrite_interaction"))

    for interaction in interactions:
        if not isinstance(interaction, dict):
            continue
        if interaction.get("type") in {"vasp", "abacus"}:
            continue
        identity = id(interaction)
        if identity in seen:
            continue
        seen.add(identity)
        yield interaction


def auto_fill_type_map_from_poscar(parameter_dict: dict, param_path: str) -> bool:
    interactions = []
    for interaction in _iter_lammps_interactions_for_type_map(parameter_dict):
        current_type_map = interaction.get("type_map")
        if (
            current_type_map is None
            or current_type_map == ""
            or current_type_map == "auto"
        ):
            interactions.append(interaction)
    if not interactions:
        return False

    structures = parameter_dict.get("structures", [])
    if not isinstance(structures, list) or not structures:
        raise RuntimeError(
            "Cannot infer interaction.type_map automatically because `structures` is empty"
        )

    structure_files = _resolve_structure_files(param_path, structures)
    type_map = _infer_type_map_from_structure_files(structure_files)
    for interaction in interactions:
        interaction["type_map"] = dict(type_map)

    with open(param_path, "w", encoding="utf-8") as fp:
        json.dump(parameter_dict, fp, indent=4)
        fp.write("\n")
    return True
