"""Protect the MD5 fixture with the unmodified public project API."""
from pathlib import Path
import json
import random
import sys
import time
import types

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
# Python 3.10+ removed 'symbol'. The project imports continue_stmt once but
# never uses it. Supply only that unused legacy name without editing source.
try:
    import symbol
except ModuleNotFoundError:
    symbol = types.ModuleType('symbol')
    symbol.continue_stmt = 0
    sys.modules['symbol'] = symbol
from wasm_vmp import JiexStart

SEED = 20261109
selection = json.loads(sys.argv[1]) if len(sys.argv) > 1 else None
random.seed(SEED)
source = ROOT / 'bench' / 'md5.wasm'
suffix = '_' + '_'.join(map(str, selection)) if selection is not None else ''
target = ROOT / 'bench' / ('md5_vmp' + suffix + '.wasm')
started = time.perf_counter()
processor = JiexStart(str(source))
processor.parse_module()
original_functions = len(processor.function_codes)
processor.encrypt_module(str(target), not_jeb=True, selected_functions=selection, instruction_expansion_factor=1)
metadata = {
    'repository': '2833844911/cy-wasm-vmp',
    'commit': 'e998a57301ef37c0453e3e567da137d50450a566',
    'random_seed': SEED,
    'settings': {'not_jeb': True, 'selected_functions': selection, 'instruction_expansion_factor': 1},
    'note': 'Unmodified core.py virtualizes all original functions except the final one. The fixture places an accessor last.',
    'python_compatibility': 'Shim supplies the unused symbol.continue_stmt import on Python 3.12.',
    'local_patch': 'bench/if_else_fix.patch fixes the false target of if/else. Performance results use this local source fix; upstream output fails MD5 correctness.',
    'original_function_count': original_functions,
    'protected_function_indices': list(range(original_functions - 1)),
    'protection_seconds': time.perf_counter() - started,
    'baseline_bytes': source.stat().st_size,
    'protected_bytes': target.stat().st_size,
}
(ROOT / 'bench' / ('protection' + suffix + '.json')).write_text(json.dumps(metadata, indent=2) + '\n')
print(json.dumps(metadata, indent=2))
