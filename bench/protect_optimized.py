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
from wasm_vmp import JiexStart

parser = argparse.ArgumentParser()
parser.add_argument('--seed', type=int, default=20261109)
parser.add_argument('--suffix', default='optimized')
parser.add_argument('--output-dir', type=Path, default=ROOT / 'bench')
args = parser.parse_args()
random.seed(args.seed)
source = ROOT / 'bench' / 'md5.wasm'
args.output_dir.mkdir(parents=True, exist_ok=True)
target = args.output_dir / ('md5_vmp_' + args.suffix + '.wasm')
started = time.perf_counter()
processor = JiexStart(str(source))
processor.parse_module()
count = len(processor.function_codes)
processor.encrypt_module(str(target), not_jeb=True, selected_functions=None, instruction_expansion_factor=1)
metadata = {
    'repository': '2833844911/cy-wasm-vmp',
    'base_commit': '62d3075dc5aed061e71414d802d020920a90b9d0',
    'random_seed': args.seed,
    'settings': {'not_jeb': True, 'selected_functions': None, 'instruction_expansion_factor': 1},
    'local_changes': 'In-place native scalar loads, generic dedup before body generation, compact typed AST heights.',
    'python_compatibility': 'Unused symbol import removed from the library; no shim required.',
    'protected_function_indices': processor.protected_function_indices,
    'frame_sizes': processor.vmp_frame_sizes,
    'private_memory_index': processor.vmp_memory_index,
    'stack_floor': processor.vmp_stack_floor,
    'stack_capacity': processor.vmp_stack_capacity,
    'note': 'All original functions, including the final accessor, are protected.',
    'protection_seconds': time.perf_counter() - started,
    'baseline_bytes': source.stat().st_size,
    'protected_bytes': target.stat().st_size,
    'protected_sha256': hashlib.sha256(target.read_bytes()).hexdigest(),
}
path = args.output_dir / ('protection_' + args.suffix + '.json')
path.write_text(json.dumps(metadata, indent=2) + '\n')
print(json.dumps(metadata, indent=2))
