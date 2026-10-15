"""Quick FeCoNi FCC inference probe: run with dpa4-python, one GPU/thread.

One cold call plus five warm calls at each size. This checks raw checkpoint
inference only and does not qualify a frozen artifact or a production image.
"""

import json,time,os,hashlib
import numpy as np
import torch
from deepmd.infer import DeepPot
model='/opt/dpa4-runtime/models/DPA4-alloytongqi/model.pt'
t0=time.perf_counter()
dp=DeepPot(model)
tm=dp.get_type_map()
records=[]
for n in (1,2,3):
    basis=np.array([[0,0,0],[0,.5,.5],[.5,0,.5],[.5,.5,0]])
    coords=np.concatenate([(basis+[i,j,k])*3.55 for i in range(n) for j in range(n) for k in range(n)])
    types=[tm.index(('Fe','Co','Ni')[i%3]) for i in range(len(coords))]
    cell=np.eye(3)*3.55*n
    timings=[]
    for iteration in range(6):
        torch.cuda.synchronize()
        start=time.perf_counter()
        e,f,v=dp.eval(coords.reshape(1,-1),cell.reshape(1,9),types)
        torch.cuda.synchronize()
        timings.append(time.perf_counter()-start)
    assert all(np.isfinite(x).all() for x in (e,f,v))
    records.append(dict(atoms=len(coords),energy=float(e[0,0]),force_max=float(np.abs(f).max()),seconds=timings,median_warm_seconds=float(np.median(timings[1:]))))
print(json.dumps(dict(torch=torch.__version__,gpu=torch.cuda.get_device_name(),capability=torch.cuda.get_device_capability(),checkpoint_sha256=hashlib.sha256(open(model,'rb').read()).hexdigest(),records=records,total_seconds=time.perf_counter()-t0)))
