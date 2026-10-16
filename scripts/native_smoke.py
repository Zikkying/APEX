"""Prepare small LAMMPS transport/execution smoke cases, not convergence studies.

Baseline must contain an actually calculated and postprocessed Al relaxation.
"""
import argparse
import copy
import importlib.util
import json
from pathlib import Path
import shutil

from apex.native import prepare, write_json, pack


def main():
    cli = argparse.ArgumentParser()
    cli.add_argument('--baseline', required=True)
    cli.add_argument('--output', required=True)
    cli.add_argument('--properties', nargs='*')
    args = cli.parse_args()
    baseline = Path(args.baseline).resolve()
    output = Path(args.output).resolve()
    source = Path(__file__).resolve().parents[1] / 'apex/skills/apex-flow/scripts/generate_config.py'
    spec = importlib.util.spec_from_file_location('generator', source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    properties = copy.deepcopy(module.PROPERTY_DEFAULTS)
    updates = {
        'eos': dict(vol_start=.96, vol_end=1.05, vol_step=.03),
        'cohesive': dict(latt_start=.95, latt_end=1.06, latt_step=.05),
        'surface': dict(min_slab_size=10, max_miller=1),
        'vacancy': dict(supercell=[2,2,2]),
        'interstitial': dict(supercell=[2,2,2], insert_ele=['Al'], lattice_type='fcc'),
        'phonon': dict(supercell_size=[2,2,2], BAND_POINTS=11),
        'gamma': dict(supercell_size=[1,1,3], n_steps=2, add_fix=['true','true','false'], cal_setting=dict(relax_pos=True,relax_shape=False,relax_vol=False)),
        'gamma_surface': dict(supercell_size=[1,1,3], n_steps_x=2, n_steps_y=2),
        'decohesive': dict(min_slab_size=10, max_vacuum_size=2, vacuum_size_step=1),
        'finite_t_latt': dict(supercell_size=[2,2,2], cal_setting=dict(temperature=[300],equi_step=200,ave_step=400,N_every=10,N_repeat=2,N_freq=20)),
        'finite_t_elastic': dict(supercell_size=[2,2,2],cal_setting=dict(temperature=[300],equi_step=200,response_step=400,stress_output_every=10,n_blocks=4)),
        'annealing': dict(supercell_size=[2,2,2], cal_setting=dict(start_temp=100,target_temp=300,end_temp=100,equi_step=100,init_lgv_thermo_equil_step=100,init_thermo_equil_step=100,final_thermo_equil_step=100,ramp_step=100,cool_step=100,hold_step=100,production_step=100,dump_step=10)),
        'melting_point': dict(supercell_size=[3,3,6],cal_setting=dict(temperature=[900],premelt_temperature=2000,premelt_steps=100,conditioning_steps=100,production_steps=200,dump_step=10,thermo_step=10,restart_interval=50,spatial_bins=6,analysis_stride=1,analysis_block_ps=.05)),
        'gruneisen': dict(supercell_size=[2,2,2],MESH=[4,4,4],volume_strains=[-.01,0,.01],temperatures=[100,300],BAND_POINTS=11),
    }
    evidence = {}
    for name, prop in properties.items():
        if args.properties and name not in args.properties: continue
        case = output / name
        case.mkdir(parents=True, exist_ok=False)
        shutil.copytree(baseline / 'confs', case / 'confs', symlinks=False,
                        ignore=shutil.ignore_patterns('eos_*'))
        param = json.loads((baseline/'param.json').read_text())
        if not param['interaction'].get('model_in_image'):
            models = param['interaction']['model']
            for model in models if isinstance(models, list) else [models]:
                target = case / model
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(baseline / model, target)
        param.pop('relaxation',None)
        prop.update(updates.get(name, {}))
        runtime=json.loads((baseline/'runtime.json').read_text())
        if name in {'phonon','gruneisen'}:
            prop['lammps_run_command']=runtime['command']
            prop['phonolammps_run_command']=runtime['phonolammps_command']
        param['properties']=[prop]
        write_json(case/'param.json',param)
        runtime=json.loads((baseline/'runtime.json').read_text())
        try:
            tasks=prepare(case/'param.json','props',runtime['command'],runtime)
            write_json(case/'tasks.json',tasks)
            pack(case/'tasks.json',case/'portable')
            evidence[name]={'prepared':True,'tasks':len(tasks['tasks'])}
        except Exception as exc:
            evidence[name]={'prepared':False,'error':str(exc)}
        write_json(output/'preparation.json',evidence)
    print(json.dumps(evidence,indent=2))

if __name__=='__main__':
    main()
