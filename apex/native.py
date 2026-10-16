"""Portable task preparation and execution; no workflow or cloud dependencies."""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import sys
import tempfile


def digest(path):
    h = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, delete=False) as out:
        json.dump(value, out, indent=2, allow_nan=False)
        out.write("\n")
        temporary = out.name
    os.replace(temporary, path)


@contextlib.contextmanager
def working_directory(path):
    previous = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


def contained(root, relative):
    path = root / relative
    if Path(relative).is_absolute() or ".." in Path(relative).parts:
        raise ValueError(f"Expected workspace-relative path: {relative}")
    # Input symlinks are materialized during packaging, but task directories
    # must themselves stay within the workspace.
    return path


def export_tasks(parameter, stage, command="lmp -in in.lammps", runtime=None):
    """Export a prepared stage using calculator file contracts and task commands."""
    from monty.serialization import loadfn
    from apex.core.calculator.calculator import make_calculator
    from apex.utils import handle_prop_suffix
    import glob

    parameter = Path(parameter).resolve()
    root = parameter.parent
    param = loadfn(parameter)
    tasks = []
    with working_directory(root):
        confs = sorted({p for pattern in param["structures"] for p in glob.glob(pattern)})
        for conf in confs:
            groups = [("relaxation", Path(conf) / "relaxation", {})] if stage == "relax" else [
                (prop["type"], Path(conf) / (prop["type"] + "_" + handle_prop_suffix(prop)[1]), prop)
                for prop in param["properties"] if handle_prop_suffix(prop)[1]
            ]
            for kind, group, prop in groups:
                directories = [group / "relax_task"] if stage == "relax" else sorted(group.glob("task.[0-9]*"))
                if not directories:
                    raise ValueError(f"No prepared tasks: {group}")
                preview_dependency = {}
                if kind in {"gamma", "gamma_surface"}:
                    from apex.core.common_prop import make_property_instance
                    from apex.preview_checks import gamma_report
                    obj = make_property_instance(dict(prop), param["interaction"])
                    geometry_file = group / "gamma_geometry.json"
                    if geometry_file.exists():
                        obj.gamma_geometry = json.loads(geometry_file.read_text())
                    source = Path(conf) / "relaxation/relax_task/CONTCAR"
                    report = gamma_report(obj, directories, source)
                    report["parameter_sha256"] = digest(parameter)
                    report_path = group / "native-preview.json"
                    write_json(report_path, report)
                    if any(check["status"] == "fail" for check in report["checks"]):
                        raise ValueError(f"Gamma task geometry/constraints failed: {report_path}")
                    preview_dependency[report_path.as_posix()] = digest(report_path)
                for directory in directories:
                    relative = directory.resolve().relative_to(root).as_posix()
                    interaction = prop.get("cal_setting", {}).get("overwrite_interaction", param["interaction"])
                    calculator = make_calculator(interaction, str(directory / "POSCAR"))
                    if interaction["type"] in {"vasp", "abacus"}:
                        raise ValueError("Native execution currently supports LAMMPS calculators")
                    required = calculator.forward_files(kind, prop)
                    for name in required:
                        if not (directory / name).is_file():
                            raise FileNotFoundError(directory / name)
                    # Include property-generated helper scripts/configuration. Export
                    # immediately after make so previous calculator outputs are absent.
                    inputs = {}
                    outputs = calculator.backward_files(kind)
                    import fnmatch
                    for path in sorted(directory.rglob("*")):
                        name = path.relative_to(directory).as_posix()
                        if path.is_file() and not any(fnmatch.fnmatch(name, pattern) for pattern in outputs):
                            inputs[name] = digest(path)
                    run_command = (directory / "run_command").read_text().strip() if (directory / "run_command").exists() else command
                    if not run_command:
                        raise ValueError(f"Empty command: {relative}")
                    required_outputs = {
                        "phonon": ["FORCE_CONSTANTS"],
                        "gruneisen": ["FORCE_CONSTANTS", "dump.relax"],
                        "finite_t_latt": ["log.lammps", "average_box.txt"],
                        "finite_t_elastic": ["log.lammps", "stress_timeseries.txt"],
                        "melting_point": ["log.lammps", "dump.melting"],
                        "annealing": ["log.lammps"],
                    }.get(kind, ["log.lammps", "dump.relax"])
                    dependency = Path(conf) / "relaxation/relax_task/result.json"
                    dependencies = {dependency.as_posix(): digest(dependency)} if stage == "props" and dependency.exists() else {}
                    dependencies.update(preview_dependency)
                    model_hash = interaction.get("runtime_model_sha256", interaction.get("model_sha256"))
                    if interaction.get("model_in_image") and not model_hash:
                        raise ValueError("Image-resident model requires runtime_model_sha256")
                    environment_files = {interaction["model"]: model_hash} if interaction.get("model_in_image") and model_hash else {}
                    spec = dict(environment_files=environment_files, stage=stage, property=kind, directory=relative, command=run_command,
                                inputs=inputs, dependencies=dependencies, required_outputs=required_outputs,
                                outputs=outputs, mutable_inputs=["POSCAR"] if kind in {"phonon", "gruneisen"} else [],
                                runtime=runtime or {})
                    revision = hashlib.sha256(json.dumps(spec, sort_keys=True).encode()).hexdigest()
                    tasks.append(dict(task_id=relative, revision=revision, **spec))
    if not tasks:
        raise ValueError("No structures/tasks matched")
    return dict(schema_version=1, parameter=parameter.name, parameter_sha256=digest(parameter), stage=stage, tasks=tasks)


def verify_inputs(root, task, *, completed=False):
    directory = contained(root, task["directory"])
    if not directory.resolve().is_relative_to(root.resolve()):
        raise ValueError("Task directory escapes workspace")
    status_path = directory / "apex_task_status.json"
    status = json.loads(status_path.read_text()) if completed and status_path.exists() else {}
    for name, expected in task["inputs"].items():
        path = contained(directory, name)
        if completed and name in task.get("mutable_inputs", []) and status.get("input_revision") == task["revision"]:
            original = contained(directory / ".apex-inputs", name)
            if not original.is_file() or digest(original) != expected:
                raise ValueError(f"Original input changed or missing: {original}")
            expected = status.get("derived_inputs", {}).get(name)
        if not path.is_file() or digest(path) != expected:
            raise ValueError(f"Input changed or missing: {path}")
    for name, expected in task["dependencies"].items():
        path = contained(root, name)
        if not path.is_file() or digest(path) != expected:
            raise ValueError(f"Stage dependency changed or missing: {path}")
    return directory


def load_task(manifest, task_id):
    manifest = Path(manifest).resolve()
    data = json.loads(manifest.read_text())
    if data.get("schema_version") != 1:
        raise ValueError("Unsupported manifest schema")
    tasks = [t for t in data["tasks"] if t["task_id"] == task_id]
    if len(tasks) != 1:
        raise ValueError(f"Expected one task: {task_id}")
    return manifest.parent, tasks[0]


def check_task(root, task):
    directory = contained(root, task["directory"])
    status_path = directory / "apex_task_status.json"
    status = json.loads(status_path.read_text()) if status_path.exists() else {}
    errors = []
    if status.get("state") == "succeeded":
        try:
            verify_inputs(root, task, completed=True)
        except ValueError as exc:
            errors.append(str(exc))
    if status.get("state") != "succeeded" or status.get("exit_code") != 0:
        errors.append("calculator has not succeeded")
    if status.get("input_revision") != task["revision"]:
        errors.append("result belongs to another input revision")
    for name in task["required_outputs"]:
        files = list(directory.glob(name))
        if not files or any(p.stat().st_size == 0 for p in files):
            errors.append(f"missing or empty output: {name}")
    return dict(task_id=task["task_id"], revision=task["revision"], ok=not errors, errors=errors, status=status)


def run_task(manifest, task_id):
    from apex.lammps_runner import LammpsRunner
    root, task = load_task(manifest, task_id)
    directory = contained(root, task["directory"])
    previous = check_task(root, task)
    if previous["ok"]:
        verify_inputs(root, task, completed=True)
        return previous
    directory = verify_inputs(root, task)
    for name, expected in task.get("environment_files", {}).items():
        if not Path(name).is_file() or digest(name) != expected:
            raise ValueError(f"Runtime model digest mismatch: {name}")
    # Atomic lock guards against duplicate starts, including a lost CLI response.
    lock = directory / ".apex-native.lock"
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        raise RuntimeError("Task already started; reconcile status before retrying") from None
    os.close(fd)
    try:
        previous = check_task(root, task)
        if previous["ok"]:
            return previous
        status_path = directory / "apex_task_status.json"
        if status_path.exists():
            attempts = directory / ".attempts"
            attempts.mkdir(exist_ok=True)
            index = len(list(attempts.iterdir())) + 1
            destination = attempts / str(index)
            destination.mkdir()
            for pattern in task["outputs"]:
                for path in directory.glob(pattern):
                    if path.is_file():
                        shutil.copy2(path, destination / path.name)
                        if path.name not in task["inputs"]:
                            path.unlink()
        for name in task.get("mutable_inputs", []):
            original = contained(directory / ".apex-inputs", name)
            original.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(directory / name, original)
        write_json(status_path, dict(state="running", input_revision=task["revision"], pid=os.getpid()))
        LammpsRunner().execute({"input_lammps": directory, "run_command": task["command"]})
        status = json.loads(status_path.read_text())
        status["input_revision"] = task["revision"]
        status["derived_inputs"] = {name: digest(directory / name) for name in task.get("mutable_inputs", [])}
        write_json(status_path, status)
        return check_task(root, task)
    finally:
        lock.unlink(missing_ok=True)


def pack(manifest, destination):
    """Materialize input links into a fresh portable workspace."""
    manifest = Path(manifest).resolve()
    root = manifest.parent
    data = json.loads(manifest.read_text())
    destination = Path(destination).resolve()
    if destination.exists():
        raise FileExistsError(destination)
    destination.mkdir(parents=True)
    for task in data["tasks"]:
        directory = verify_inputs(root, task)
        for name in task["inputs"]:
            target = contained(destination, task["directory"]) / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(directory / name, target)
        for name in task["dependencies"]:
            target = contained(destination, name)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(root / name, target)
    shutil.copyfile(manifest, destination / manifest.name)
    return {"ok": True, "directory": str(destination)}


def finite_result(value):
    if isinstance(value, float):
        return math.isfinite(value)
    if isinstance(value, dict):
        return all(finite_result(v) for v in value.values())
    if isinstance(value, list):
        return all(finite_result(v) for v in value)
    return True


def prepare(parameter, stage, command="lmp -in in.lammps", runtime=None):
    from monty.serialization import loadfn
    from apex.preparation import auto_fill_type_map_from_poscar
    from apex.step import do_step
    parameter = Path(parameter).resolve()
    with working_directory(parameter.parent):
        param = loadfn(parameter)
        auto_fill_type_map_from_poscar(param, str(parameter))
        if stage == "props":
            import glob
            for pattern in param["structures"]:
                for conf in glob.glob(pattern):
                    result = Path(conf) / "relaxation/relax_task/result.json"
                    status_path = result.with_name("apex_task_status.json")
                    status = json.loads(status_path.read_text()) if status_path.exists() else {}
                    if (not result.is_file() or not finite_result(json.loads(result.read_text()))
                            or status.get("state") != "succeeded" or status.get("exit_code") != 0):
                        raise ValueError(f"Complete relaxation and post_relax first: {conf}")
        do_step(param, "make_relax" if stage == "relax" else "make_props")
        return export_tasks(parameter, stage, command, runtime)


def post(parameter, manifest):
    from monty.serialization import loadfn
    from apex.step import do_step
    parameter = Path(parameter).resolve()
    root = parameter.parent
    data = json.loads(Path(manifest).read_text())
    if digest(parameter) != data["parameter_sha256"]:
        raise ValueError("Parameters changed since task preparation")
    checks = []
    for task in data["tasks"]:
        verify_inputs(root, task, completed=True)
        checks.append(check_task(root, task))
    if not checks or not all(item["ok"] for item in checks):
        raise ValueError("All tasks in the stage must pass result checks before post")
    with working_directory(root):
        do_step(loadfn(parameter), "post_relax" if data["stage"] == "relax" else "post_props")
    results = sorted({
        str((root / t["directory"] / "result.json") if data["stage"] == "relax"
            else (root / t["directory"]).parent / "result.json") for t in data["tasks"]
    })
    for path in results:
        value = json.loads(Path(path).read_text())
        if not value or not finite_result(value):
            raise ValueError(f"Empty or non-finite property result: {path}")
    return {"ok": True, "results": results}


@contextlib.contextmanager
def diagnostic_output():
    """Keep inherited subprocess stdout out of the CLI JSON stream."""
    try:
        stdout_fd, stderr_fd = sys.stdout.fileno(), sys.stderr.fileno()
    except (AttributeError, OSError, ValueError):
        with contextlib.redirect_stdout(sys.stderr):
            yield
        return
    sys.stdout.flush()
    saved = os.dup(stdout_fd)
    try:
        os.dup2(stderr_fd, stdout_fd)
        with contextlib.redirect_stdout(sys.stderr):
            yield
    finally:
        sys.stderr.flush()
        os.dup2(saved, stdout_fd)
        os.close(saved)


def main(argv=None):
    parser = argparse.ArgumentParser(prog="apex native")
    sub = parser.add_subparsers(dest="action", required=True)
    for action in ("export", "prepare"):
        export = sub.add_parser(action)
        export.add_argument("parameter")
        export.add_argument("--stage", choices=["relax", "props"], required=True)
        export.add_argument("--command", default="lmp -in in.lammps")
        export.add_argument("--runtime")
        export.add_argument("--output", default="tasks.json")
    item = sub.add_parser("post")
    item.add_argument("parameter")
    item.add_argument("manifest")
    for action in ("run", "check"):
        item = sub.add_parser(action)
        item.add_argument("manifest")
        item.add_argument("--task", required=True)
        item.add_argument("--result", help="Write the machine-readable report independently of logs")
    item = sub.add_parser("pack")
    item.add_argument("manifest")
    item.add_argument("destination")
    args = parser.parse_args(argv)
    try:
        with diagnostic_output():
            if args.action in {"export", "prepare"}:
                runtime = json.loads(Path(args.runtime).read_text()) if args.runtime else {}
                operation = export_tasks if args.action == "export" else prepare
                result = operation(args.parameter, args.stage, args.command, runtime)
                if Path(args.output).resolve().parent != Path(args.parameter).resolve().parent:
                    raise ValueError("Manifest must be written beside the parameter file")
                write_json(args.output, result)
                result = {"ok": True, "manifest": args.output, "tasks": len(result["tasks"])}
            elif args.action == "run":
                result = run_task(args.manifest, args.task)
            elif args.action == "check":
                root, task = load_task(args.manifest, args.task)
                result = check_task(root, task)
            elif args.action == "post":
                result = post(args.parameter, args.manifest)
            else:
                result = pack(args.manifest, args.destination)
    except Exception as exc:
        result = {"ok": False, "error": str(exc)}
    if getattr(args, "result", None):
        write_json(args.result, result)
    print(json.dumps(result, allow_nan=False))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
