"""Prevent runtime selection from regressing to stale images/interpreters."""
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1] / 'apex/skills/apex-flow'


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class RuntimeSelectionTests(unittest.TestCase):
    def test_default_openapi_paths_match_selected_environment(self):
        generator = load('generate_config')
        for potential, command, interpreter in [
            ('eam_alloy', '/usr/bin/lmp -in in.lammps', '/opt/apex-venv/bin/python'),
            ('deepmd', '/usr/local/bin/apex-lmp -in in.lammps', '/usr/local/bin/apex-calculator-python'),
        ]:
            with self.subTest(potential=potential):
                cfg = generator.build_global_json_sandbox(
                    'lammps', potential=potential, access_key='test', project_id=397953)
                self.assertEqual(cfg['lammps_run_command'], command)
                self.assertEqual(cfg['dispatcher_remote_command'], interpreter)
                self.assertFalse(cfg['ignore_exit_code'])
                self.assertEqual(cfg['image_address'], cfg['lammps_image_name'])

    def test_phonon_commands_survive_sandbox_path_reset(self):
        from apex.config import Config
        generator = load('generate_config')
        for potential, image, executable in [
            ('eam_alloy', generator.LAMMPS_CPU_IMAGE, '/opt/apex-venv/bin/phonolammps'),
            ('deepmd', generator.LAMMPS_GPU_IMAGE, '/opt/deepmd-kit-3.1.3/bin/phonolammps'),
        ]:
            cfg = generator.build_global_json_sandbox('lammps', potential=potential,
                access_key='test', project_id=397953)
            command = cfg['phonolammps_run_command']
            self.assertTrue(command.startswith(executable + ' '))
            self.assertIn('{primitive_axes}', command)
            self.assertEqual(Config(lammps_image_name=image).basic_config_dict['phonolammps_run_command'], command)
        self.assertIsNone(Config(lammps_image_name='custom:lammps').basic_config_dict['phonolammps_run_command'])

    def test_generic_image_rejects_cpu_and_unqualified_gpu(self):
        validator = load('validate_apex_combo')
        for machine in ['c1_m2_cpu', 'c8_m31_1 * NVIDIA T4', 'c8_m32_1 * NVIDIA 4090']:
            self.assertFalse(validator.check_combo(validator.DPA4_LAMMPS_IMAGE, machine)[0])
        self.assertTrue(validator.check_combo(validator.DPA4_LAMMPS_IMAGE, 'c16_m120_1 * NVIDIA L20')[0])

    def test_special_models_do_not_silently_use_deepmd_runtime(self):
        generator = load('generate_config')
        for potential in ['mace', 'nep', 'gap', 'rann', 'snap']:
            with self.assertRaisesRegex(ValueError, 'custom image'):
                generator.select_lammps_image(potential)

    def test_custom_image_does_not_inherit_nonexistent_wrapper(self):
        generator = load('generate_config')
        cfg = generator.build_global_json_sandbox('lammps', potential='mace',
            access_key='test', project_id=397953, lammps_image='custom:mace',
            run_command='/custom/bin/lmp -in in.lammps')
        self.assertEqual(cfg['lammps_run_command'], '/custom/bin/lmp -in in.lammps')
        self.assertNotIn('dispatcher_remote_command', cfg)

    def test_frontmatter_is_only_name_and_description(self):
        import yaml
        text = (ROOT / 'SKILL.md').read_text()
        metadata = yaml.safe_load(text.split('---', 2)[1])
        self.assertEqual(set(metadata), {'name', 'description'})
