"""Compare interpreter construction with a Git baseline, using identical protection scope."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import random
import statistics
import subprocess
import sys
import tempfile
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from wasm_vmp import JiexStart
from wasm_vmp import core

root=Path(__file__).resolve().parents[1]
out=root/'bench'/'verification_v2'
out.mkdir(exist_ok=True)
current=core.WasmVMP
baseline_ref=sys.argv[1] if len(sys.argv)>1 else '80d5852'
source=subprocess.check_output(['git','show',baseline_ref+':wasm_vmp/wasmvmp.py'],cwd=root,text=True)
with tempfile.TemporaryDirectory() as directory:
    saved=Path(directory)/'baseline.py';saved.write_text(source)
    spec=importlib.util.spec_from_file_location('wasm_vmp._baseline_v2',saved)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    timings={'baseline':[],'optimized':[]}
    for round_ in range(7):
        for name in (['baseline','optimized'] if round_%2==0 else ['optimized','baseline']):
            core.WasmVMP=module.WasmVMP if name=='baseline' else current
            random.seed(20261109)
            with contextlib.redirect_stdout(io.StringIO()):
                started=time.perf_counter()
                processor=JiexStart(str(root/'bench/md5.wasm'));processor.parse_module()
                selected=list(range(len(processor.function_codes)-1))
                processor.encrypt_module(str(out/(name+'.wasm')),not_jeb=True,selected_functions=selected)
                timings[name].append(time.perf_counter()-started)
    core.WasmVMP=current
medians={name:statistics.median(values) for name,values in timings.items()}
report={'baselineRef':baseline_ref,'scope':'identical MD5 functions; last accessor excluded in both builds',
        'selectedFunctions':selected,'rounds':7,'seconds':timings,'medianSeconds':medians,
        'buildSpeedup':medians['baseline']/medians['optimized'],
        'bytes':{n:(out/(n+'.wasm')).stat().st_size for n in timings}}
(out/'build_results.json').write_text(json.dumps(report,indent=2)+'\n')
config={'before':'verification_v2/baseline.wasm','after':'verification_v2/optimized.wasm','output':'verification_v2/runtime_results.json', 'protectionBefore':{'revision':baseline_ref,'settings':{'selected_functions':selected,'not_jeb':True}},'protectionOptimized':{'revision':'v2 source','settings':{'selected_functions':selected,'not_jeb':True}}}
(out/'benchmark_config.json').write_text(json.dumps(config,indent=2)+'\n')
print(json.dumps(report,indent=2))
