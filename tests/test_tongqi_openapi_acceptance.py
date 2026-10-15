"""Backend contract checks; these do not certify cloud acceptance."""
import unittest
from apex.config import Config
from apex.submit import _validate_dpa4_execution_config, _dpa4_image_name, DPA4_LAMMPS_RUN_COMMAND

class TestTongqiOpenAPI(unittest.TestCase):
    def config(self, **overrides):
        values = dict(context_type='OpenAPI', batch_type='OpenAPI', project_id=397953,
                      machine_type='c16_m120_1 * NVIDIA L20', image_address=_dpa4_image_name(),
                      platform='ali', dispatcher_remote_command='/usr/local/bin/dpa4-python', ignore_exit_code=False, group_size=1, pool_size=1,
                      lammps_run_command=DPA4_LAMMPS_RUN_COMMAND)
        values.update(overrides)
        return Config(**values)

    def test_exact_l20_contract(self):
        _validate_dpa4_execution_config(self.config(), None)

    def test_wrong_gpu_image_and_ignored_failures_rejected(self):
        for override in ({'machine_type':'c1_m2_cpu'}, {'image_address':'wrong:image'},
                         {'ignore_exit_code':True}, {'batch_type':'Bohrium'},
                         {'dispatcher_remote_command':'python3'}, {'group_size':2}, {'machine':{'remote_profile':{'ignore_exit_code':True}}}):
            with self.subTest(override=override), self.assertRaises((RuntimeError, ValueError)):
                _validate_dpa4_execution_config(self.config(**override), None)

    def test_generator_qualification_gate_and_backend_contract(self):
        import importlib.util
        from pathlib import Path
        root=Path(__file__).resolve().parents[1]/"apex/skills/apex-flow/scripts"
        spec=importlib.util.spec_from_file_location("openapi_generator",root/"generate_config.py")
        gen=importlib.util.module_from_spec(spec);spec.loader.exec_module(gen)
        profile=gen._load_dpa4_runtime_profile(gen.DPA4_RUNTIME_PROFILE)
        profile.pop("openapi_qualification", None)
        with self.assertRaisesRegex(RuntimeError,"qualification is pending"):
            gen.build_global_json_sandbox("lammps","deepmd",access_key="test",project_id=1,runtime_profile=profile)
        profile["openapi_qualification"]={"status":"passed"}
        config=gen.build_global_json_sandbox("lammps","deepmd",access_key="test",project_id=1,runtime_profile=profile)
        self.assertEqual(config["machine_type"],"c16_m120_1 * NVIDIA L20")
        self.assertEqual(config["image_address"],_dpa4_image_name())
        _validate_dpa4_execution_config(Config(**config),None)
        spec=importlib.util.spec_from_file_location("openapi_validator",root/"validate_inputs.py")
        validator=importlib.util.module_from_spec(spec);spec.loader.exec_module(validator)
        self.assertEqual(validator._validate_dpa4_global_contract({},config,_dpa4_image_name()),[])
        spec=importlib.util.spec_from_file_location("openapi_combo",root/"validate_apex_combo.py")
        combo=importlib.util.module_from_spec(spec);spec.loader.exec_module(combo)
        self.assertTrue(combo.check_combo(_dpa4_image_name(),config["machine_type"],runtime_profile=gen.DPA4_RUNTIME_PROFILE,sandbox=True)[0])
        self.assertFalse(combo.check_combo(_dpa4_image_name(),config["machine_type"],runtime_profile=gen.DPA4_RUNTIME_PROFILE)[0])
        with self.assertRaises(ValueError):
            gen.build_global_json_sandbox("lammps","deepmd",access_key="test",project_id=1,runtime_profile=profile,machine_type="c1_m2_cpu")

    def test_job_identifier_normalization(self):
        from apex.openapi_compat import normalize_job_detail, dispatcher_pre_script
        self.assertEqual(normalize_job_detail({"jobId":"a","status":2},"a")["id"],"a")
        self.assertEqual(normalize_job_detail({"id":"a"},"a")["id"],"a")
        for detail in ({}, {"id":"b"}, {"id":"a","jobId":"b"}):
            with self.subTest(detail=detail), self.assertRaises(RuntimeError):
                normalize_job_detail(detail,"a")
        compile(dispatcher_pre_script(),"<dispatcher-pre-script>","exec")
        self.assertIn("_APEXOpenAPIJob.detail",self.config().get_executor(self.config().dispatcher_config_dict).pre_script)

class TestLowLevelTypeMapGuard(unittest.TestCase):
    def test_unresolved_map_rejected_before_config_or_cloud(self):
        from apex.submit import submit_workflow
        for value in (None, "", "auto"):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "submit_from_args"):
                submit_workflow([{"structures": ["confs/*"], "interaction": {
                    "type": "deepmd", "type_map": value}}], {}, ["."], "relax")
