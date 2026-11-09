"""Build full-function VMP MD5 with the local dispatch optimization."""
from pathlib import Path
import argparse
import hashlib
import json
import random
import sys
import time
import types

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
try:
    import symbol
except ModuleNotFoundError:
    symbol = types.ModuleType('symbol')
    symbol.continue_stmt = 0
    sys.modules['symbol'] = symbol
from wasm_vmp import JiexStart

parser = argparse.ArgumentParser()
parser.add_argument('--seed', type=int, default=20261109)
parser.add_argument('--suffix', default='optimized')
args = parser.parse_args()
random.seed(args.seed)
source = ROOT / 'bench' / 'md5.wasm'
target = ROOT / 'bench' / ('md5_vmp_' + args.suffix + '.wasm')
started = time.perf_counter()
processor = JiexStart(str(source))
processor.parse_module()
count = len(processor.function_codes)
processor.encrypt_module(str(target), not_jeb=True, selected_functions=None, instruction_expansion_factor=1)
metadata = {
    'repository': '2833844911/cy-wasm-vmp',
    'base_commit': 'e998a57301ef37c0453e3e567da137d50450a566',
    'random_seed': args.seed,
    'settings': {'not_jeb': True, 'selected_functions': None, 'instruction_expansion_factor': 1},
    'local_changes': 'Prior if/else correctness fix plus instruction dispatch optimization; see included patch.',
    'python_compatibility': 'Shim supplies unused symbol.continue_stmt import on Python 3.12.',
    'protected_function_indices': list(range(count - 1)),
    'note': 'MD5 compression and hash entry stay virtualized; only the final output_ptr accessor is skipped by existing core.py behavior.',
    'protection_seconds': time.perf_counter() - started,
    'baseline_bytes': source.stat().st_size,
    'protected_bytes': target.stat().st_size,
    'protected_sha256': hashlib.sha256(target.read_bytes()).hexdigest(),
}
path = ROOT / 'bench' / ('protection_' + args.suffix + '.json')
path.write_text(json.dumps(metadata, indent=2) + '\n')
print(json.dumps(metadata, indent=2))
