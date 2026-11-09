"""Compare complete revisions in isolated processes with identical protection scope."""
import argparse
import contextlib
import hashlib
import io
import json
from pathlib import Path
import random
import statistics
import subprocess
import sys
import time


def worker(root, fixture, target):
    sys.path.insert(0, str(root))
    from wasm_vmp import JiexStart, core
    parent = core.WasmVMP
    captured = []
    class Capture(parent):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            captured.append(self)
    core.WasmVMP = Capture
    random.seed(20261109)
    with contextlib.redirect_stdout(io.StringIO()):
        started = time.perf_counter()
        processor = JiexStart(str(root / fixture))
        processor.parse_module()
        # Keep the benchmark's final MD5 address accessor outside protection
        # in both revisions; protect every function of the compiled C++ sample.
        selected = [0, 1, 2] if fixture.endswith('md5.wasm') else None
        processor.encrypt_module(str(target), not_jeb=True, selected_functions=selected)
        seconds = time.perf_counter() - started
    engine = captured[0]
    return {'seconds': seconds, 'bytes': target.stat().st_size,
            'sha256': hashlib.sha256(target.read_bytes()).hexdigest(),
            'handlers': len(engine.dispatch_opcodes),
            'interpreterInstructions': len(engine.vmp_fun['code']),
            'selectedFunctions': processor.protected_function_indices,
            'frames': getattr(processor, 'vmp_frame_sizes', {}),
            'stackCapacity': getattr(processor, 'vmp_stack_capacity', None)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('baseline', type=Path)
    parser.add_argument('--output-dir', type=Path, default=Path(__file__).parent / 'verification_frames')
    parser.add_argument('--worker', nargs=2, metavar=('FIXTURE', 'TARGET'))
    args = parser.parse_args()
    if args.worker:
        print(json.dumps(worker(args.baseline.resolve(), args.worker[0], Path(args.worker[1]))))
        return
    current = Path(__file__).resolve().parents[1]
    out = args.output_dir.resolve()
    out.mkdir(parents=True, exist_ok=True)
    records = []
    for name, fixture in [('md5', 'bench/md5.wasm'), ('base64', 'base64_2.wasm')]:
        runs = {'baseline': [], 'optimized': []}
        for round_ in range(7):
            for label in (['baseline', 'optimized'] if round_ % 2 == 0 else ['optimized', 'baseline']):
                root = args.baseline.resolve() if label == 'baseline' else current
                target = out / (name + '_' + label + '.wasm')
                command = [sys.executable, str(Path(__file__).resolve()), str(root), '--worker', fixture, str(target)]
                runs[label].append(json.loads(subprocess.check_output(command, text=True)))
        medians = {label: statistics.median(x['seconds'] for x in samples) for label, samples in runs.items()}
        records.append({'fixture': name, 'runs': runs, 'medianSeconds': medians,
                        'buildSpeedup': medians['baseline'] / medians['optimized']})
    report = {'baselineCommit': subprocess.check_output(['git', '-C', str(args.baseline), 'rev-parse', 'HEAD'], text=True).strip(),
              'rounds': 7, 'scope': 'Full revisions; alternating order, subprocess startup excluded; same protection settings and input', 'records': records}
    (out / 'build_results.json').write_text(json.dumps(report, indent=2) + '\n')
    try:
        prefix = out.relative_to(current / 'bench')
    except ValueError:
        prefix = out
    config = {'before': str(prefix / 'md5_baseline.wasm'), 'after': str(prefix / 'md5_optimized.wasm'),
              'output': str(prefix / 'runtime_results.json'),
              'protectionBefore': {'revision': report['baselineCommit'], 'settings': {'selected_functions': [0, 1, 2], 'not_jeb': True}},
              'protectionOptimized': {'revision': 'frame/dedup source', 'settings': {'selected_functions': [0, 1, 2], 'not_jeb': True}}}
    (out / 'benchmark_config.json').write_text(json.dumps(config, indent=2) + '\n')
    print(json.dumps({**report, 'records': [{k:v for k,v in r.items() if k != 'runs'} for r in records]}, indent=2))


if __name__ == '__main__':
    main()
