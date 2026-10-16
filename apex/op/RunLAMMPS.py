"""dflow adapter for the standalone LAMMPS task runner."""
from pathlib import Path
from dflow.python import OP, OPIO, OPIOSign, Artifact, upload_packages
from apex.lammps_runner import LammpsRunner
from apex.optional_workflow import enable_workflow

import apex.lammps_runner
upload_packages.append(apex.lammps_runner.__file__)
enable_workflow()
upload_packages.append(__file__)

class RunLAMMPS(LammpsRunner, OP):
    @classmethod
    def get_input_sign(cls):
        return OPIOSign({'input_lammps': Artifact(Path), 'run_command': str})

    @classmethod
    def get_output_sign(cls):
        return OPIOSign({'backward_dir': Artifact(Path, sub_path=False)})

    @OP.exec_sign_check
    def execute(self, op_in: OPIO) -> OPIO:
        return OPIO(super().execute(op_in))
