"""Run phonoLAMMPS against the same native DeepMD library as dpa4-lmp."""
import runpy
import sys
import lammps

_original_lammps = lammps.lammps

class NativeDeepMDLAMMPS(_original_lammps):
    def __init__(self, name="", *args, **kwargs):
        if name not in ("", "dpa4"):
            raise ValueError("DPA4 phonoLAMMPS requires the audited native library")
        super().__init__("dpa4", *args, **kwargs)
        if not self.has_style("pair", "deepmd"):
            self.close()
            raise RuntimeError("native LAMMPS lacks pair_style deepmd")
        print("DPA4_NATIVE_LIBRARY=" + str(self.lib._name), file=sys.stderr)

lammps.lammps = NativeDeepMDLAMMPS
runpy.run_path("/opt/mamba/bin/phonolammps", run_name="__main__")
