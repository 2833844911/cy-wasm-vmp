"""Protect compatibility fixtures in one process; each job has its own seed."""
import contextlib
import io
import json
from pathlib import Path
import random
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from wasm_vmp import JiexStart

jobs = json.loads(Path(sys.argv[1]).read_text())
results = []
for job in jobs:
    log = io.StringIO()
    started = time.perf_counter()
    try:
        with contextlib.redirect_stdout(log):
            random.seed(job['seed'])
            processor = JiexStart(job['input'])
            processor.parse_module()
            before = [repr(f['code']) for f in processor.function_codes]
            expected = [i for i in range(len(before)) if job.get('selectedFunctions') is None or processor.codec.imported_func_count + i in job['selectedFunctions']]
            processor.encrypt_module(job['output'], not_jeb=job['notJeb'],
                                     selected_functions=job.get('selectedFunctions'),
                                     instruction_expansion_factor=job.get('factor', 1))
            assert all(repr(processor.function_codes[i]['code']) != before[i] for i in expected), 'Selected function was not protected'
        results.append({'name': job['name'], 'seed': job['seed'], 'passed': True,
                        'protectedFunctions': processor.protected_function_indices,
                        'frameSizes': getattr(processor, 'vmp_frame_sizes', {}),
                        'memoryIndex': getattr(processor, 'vmp_memory_index', None),
                        'stackFloor': getattr(processor, 'vmp_stack_floor', None),
                        'stackCapacity': getattr(processor, 'vmp_stack_capacity', None),
                        'stackTop': getattr(processor, 'vmp_stack_top', None),
                        'seconds': time.perf_counter() - started})
    except Exception as exc:
        results.append({'name': job['name'], 'seed': job['seed'], 'passed': False,
                        'error': repr(exc), 'log': log.getvalue()[-1200:]})
print(json.dumps(results))
