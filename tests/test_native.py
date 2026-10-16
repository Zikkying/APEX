import importlib.abc
import json
from pathlib import Path
import subprocess
import sys

import pytest

from apex.native import check_task, digest, pack, run_task, verify_inputs, write_json


def task_fixture(tmp_path, command="printf done > log.lammps; printf done > dump.relax"):
    directory = tmp_path / "confs/Al/relaxation/relax_task"
    directory.mkdir(parents=True)
    (directory / "in.lammps").write_text("# input\n")
    task = dict(task_id="relax-Al", directory=directory.relative_to(tmp_path).as_posix(),
                revision="revision1", command=command,
                inputs={"in.lammps": digest(directory / "in.lammps")}, dependencies={},
                required_outputs=["log.lammps", "dump.relax"],
                outputs=["log.lammps", "dump.relax", "apex_task_status.json"])
    manifest = tmp_path / "tasks.json"
    write_json(manifest, {"schema_version": 1, "tasks": [task]})
    return manifest, task, directory


def test_core_imports_without_workflow_packages():
    script = '''
import sys, importlib.abc
class Block(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'dflow', 'dpdispatcher', 'fpop'}:
            raise ImportError(fullname)
sys.meta_path.insert(0, Block())
import apex.main, apex.step, apex.preview, apex.native, apex.preparation
assert not any(k.startswith('dflow') for k in sys.modules)
'''
    subprocess.run([sys.executable, "-c", script], check=True)


def test_native_run_idempotent_and_changed_input_rejected(tmp_path):
    manifest, task, directory = task_fixture(tmp_path)
    assert run_task(manifest, task["task_id"])["ok"]
    status = (directory / "apex_task_status.json").read_bytes()
    assert run_task(manifest, task["task_id"])["ok"]
    assert (directory / "apex_task_status.json").read_bytes() == status
    (directory / "in.lammps").write_text("changed")
    with pytest.raises(ValueError, match="Input changed"):
        run_task(manifest, task["task_id"])


def test_nonzero_and_missing_output_are_failures(tmp_path):
    manifest, task, directory = task_fixture(tmp_path, "exit 7")
    assert not run_task(manifest, task["task_id"])["ok"]
    write_json(directory / "apex_task_status.json", dict(state="succeeded", exit_code=0, input_revision="revision1"))
    assert not check_task(tmp_path, task)["ok"]


def test_pack_materializes_external_symlinks(tmp_path):
    manifest, task, directory = task_fixture(tmp_path)
    model = tmp_path / "source-model"
    model.write_bytes(b"potential")
    (directory / "model").symlink_to(model)
    task["inputs"]["model"] = digest(model)
    write_json(manifest, {"schema_version": 1, "tasks": [task]})
    target = tmp_path / "portable"
    pack(manifest, target)
    model.unlink()
    assert not (target / task["directory"] / "model").is_symlink()
    verify_inputs(target, task)


def test_duplicate_start_requires_reconciliation(tmp_path):
    manifest, task, directory = task_fixture(tmp_path)
    (directory / ".apex-native.lock").touch()
    with pytest.raises(RuntimeError, match="already started"):
        run_task(manifest, task["task_id"])


def test_dependency_revision_and_path_escape_rejected(tmp_path):
    _, task, _ = task_fixture(tmp_path)
    task["dependencies"] = {"missing-result.json": "old"}
    with pytest.raises(ValueError, match="dependency"):
        verify_inputs(tmp_path, task)
    task["directory"] = "../escape"
    with pytest.raises(ValueError, match="workspace-relative"):
        verify_inputs(tmp_path, task)


def test_mutable_poscar_preserves_original_and_rejects_later_changes(tmp_path):
    manifest, task, directory = task_fixture(tmp_path,
        'printf transformed > POSCAR; printf done > log.lammps; printf done > dump.relax')
    (directory / 'POSCAR').write_text('original')
    task['inputs']['POSCAR'] = digest(directory / 'POSCAR')
    task['mutable_inputs'] = ['POSCAR']
    write_json(manifest, {'schema_version': 1, 'tasks': [task]})
    assert run_task(manifest, task['task_id'])['ok']
    assert (directory / '.apex-inputs/POSCAR').read_text() == 'original'
    assert run_task(manifest, task['task_id'])['ok']
    (directory / 'POSCAR').write_text('unrecorded')
    assert not check_task(tmp_path, task)['ok']


def test_cli_stdout_is_json_when_calculator_prints(tmp_path):
    manifest, task, _ = task_fixture(tmp_path,
        'echo calculator-output; printf done > log.lammps; printf done > dump.relax')
    proc = subprocess.run([sys.executable, '-m', 'apex', 'native', 'run',
                           str(manifest), '--task', task['task_id']], capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    assert json.loads(proc.stdout)['ok']


def test_native_tongqi_generator_pins_image_and_model_without_ticket(tmp_path):
    structure = tmp_path / 'POSCAR'
    structure.write_text('Al\n1\n4.05 0 0\n0 4.05 0\n0 0 4.05\nAl\n4\nDirect\n0 0 0\n0 .5 .5\n.5 0 .5\n.5 .5 0\n')
    generator = Path(__file__).resolve().parents[1] / 'apex/skills/apex-flow/scripts/generate_config.py'
    output = tmp_path / 'job'
    proc = subprocess.run([sys.executable, str(generator), 'create', '--execution', 'native',
                           '--backend', 'lammps', '--runtime-profile', 'dpa4-alloytongqi-l20',
                           '--structure', str(structure), '--properties', 'eos', '--flow-type', 'relax',
                           '--output-dir', str(output)], capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    runtime = json.loads((output / 'runtime.json').read_text())
    manifest = json.loads((output / 'tasks.json').read_text())
    assert '@sha256:' in runtime['image']
    assert runtime['phonolammps_command'].startswith('/usr/local/bin/dpa4-phonolammps ')
    assert manifest['tasks'][0]['environment_files']
    assert not (output / 'global.json').exists()
    assert 'ticket' not in runtime
