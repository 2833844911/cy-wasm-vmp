"""Compare compact stack heights with the preserved full-snapshot analyzer.

The baseline is read from Git, not recreated by the compact implementation.
Tracemalloc measures only analysis/AST allocations, with the same instruction
input already allocated, and retains the resulting AST until the sample ends.
"""
import argparse
import copy
import gc
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import tracemalloc

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from wasm_vmp.analyzer import WasmAnalyzer
from wasm_vmp.stack_frames import operand_frame_bytes
from wasm_vmp.utils import add_instr, pack_op

WIDTH = {'i32': 4, 'i64': 8, 'f32': 4, 'f64': 8}


def width(types):
    return sum(WIDTH[value] for value in types)


def load_baseline(reference, directory):
    source = subprocess.check_output(['git', 'show', reference + ':wasm_vmp/analyzer.py'], cwd=ROOT, text=True)
    path = Path(directory) / 'baseline_analyzer.py'
    path.write_text(source)
    spec = importlib.util.spec_from_file_location('wasm_vmp._snapshot_baseline', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.WasmAnalyzer


def fixtures():
    # Independent numeric operations retain a typed stack at many depths.
    mixed = [add_instr(0x41, pack_op(7)), add_instr(0x42, pack_op(9)),
             add_instr(0x43, pack_op(1.5)), add_instr(0x44, pack_op(2.5)),
             add_instr(0x1A), add_instr(0x1A), add_instr(0x1A), add_instr(0x0B)]
    # A block with parameters and mixed multiple results must restore its base.
    multi = [add_instr(0x41, pack_op(7)), add_instr(0x42, pack_op(9)),
             add_instr(0x02, {'val': 0, 'len': 1, 'type_index': True}),
             add_instr(0x21, pack_op(1)), add_instr(0x21, pack_op(0)),
             add_instr(0x20, pack_op(1)), add_instr(0x20, pack_op(0)),
             add_instr(0x0B), add_instr(0x0B)]
    choose = [add_instr(0x41, pack_op(7)), add_instr(0x41, pack_op(1)),
              add_instr(0x04, 0x7E), add_instr(0x42, pack_op(9)),
              add_instr(0x05), add_instr(0x42, pack_op(11)),
              add_instr(0x0B), add_instr(0x1A), add_instr(0x0B)]
    call = [add_instr(0x41, pack_op(7)), add_instr(0x10, pack_op(0)),
            *[add_instr(0x1A) for _ in range(300)], add_instr(0x0B)]
    return [
        ('mixed', mixed, {}, {}, [], ['i32'], 32),
        ('block_params_results', multi, {0: 'i32', 1: 'i64'}, {},
         [{'params': ['i32', 'i64'], 'results': ['i64', 'i32']}], ['i64', 'i32'], 16),
        ('if_branches', choose, {}, {}, [], ['i32'], 16),
        ('large_call_results', call, {}, {0: ([], ['i32'] * 300)}, [], ['i32'], 1216),
    ]


def compare(old_nodes, nodes, types):
    assert len(old_nodes) == len(nodes)
    checks = 0
    for old, node in zip(old_nodes, nodes):
        for field in ['name', 'opcode', 'operands', 'pops', 'pushes']:
            assert old[field] == node[field], (field, old['name'])
        assert 'stack_before' not in node and 'entry_stack' not in node
        assert node['stack_bytes_before'] == width(old['stack_before'])
        if node['name'] in ['block', 'loop', 'if']:
            assert node['entry_stack_bytes'] == width(old['entry_stack'])
            operand = node['operands'][0] if node['operands'] else 0x40
            value = operand['val'] if isinstance(operand, dict) else operand
            if isinstance(operand, dict) and operand.get('type_index'):
                results = types[value]['results']
            else:
                results = {0x40: [], 0x7F: ['i32'], 0x7E: ['i64'], 0x7D: ['f32'], 0x7C: ['f64']}[value]
            expected_after = width(old['entry_stack']) + width(results)
        else:
            expected_after = width(old['stack_before']) - width(old['pops']) + width(old['pushes'])
        assert node['stack_bytes_after'] == expected_after, node['name']
        checks += 1 + compare(old['children'], node['children'], types)
        checks += compare(old['else_children'], node['else_children'], types)
    return checks


def sample(analyzer_class, count):
    instructions = [add_instr(0x41, pack_op(0)) for _ in range(count)]
    instructions.extend(add_instr(0x1A) for _ in range(count - 1))
    instructions.append(add_instr(0x0B))
    gc.collect()
    tracemalloc.start()
    started = time.perf_counter()
    nodes = analyzer_class().analyze_wasm_ast(instructions)
    seconds = time.perf_counter() - started
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    assert len(nodes) == 2 * count - 1
    # Keep the AST live until after measuring peak memory.
    if analyzer_class is WasmAnalyzer:
        assert operand_frame_bytes(nodes, ['i32']) == ((count * 4 + 15) & ~15)
    return {'depth': count, 'nodes': len(nodes), 'peakBytes': peak, 'seconds': seconds}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--baseline-ref', default='62d3075')
    parser.add_argument('--json-output', type=Path)
    args = parser.parse_args()
    records = []
    checks = 0
    with tempfile.TemporaryDirectory(prefix='ast_snapshot_baseline_') as directory:
        baseline = load_baseline(args.baseline_ref, directory)
        for name, instructions, locals_, signatures, types, results, peak in fixtures():
            old = baseline(func_signatures=signatures, types=types).analyze_wasm_ast(copy.deepcopy(instructions), locals_types=locals_)
            current = WasmAnalyzer(func_signatures=signatures, types=types).analyze_wasm_ast(copy.deepcopy(instructions), locals_types=locals_)
            checks += compare(old, current, types)
            assert operand_frame_bytes(current, results) == peak, name
            records.append({'name': name, 'passed': True, 'frameBytes': peak})
        memory = []
        for depth in [1024, 2048]:
            before, after = sample(baseline, depth), sample(WasmAnalyzer, depth)
            assert after['peakBytes'] < before['peakBytes'] * 0.5, (before, after)
            memory.append({'depth': depth, 'baseline': before, 'compact': after,
                           'peakReductionPercent': 100 * (1 - after['peakBytes'] / before['peakBytes'])})
    report = {'passed': True, 'baselineRef': args.baseline_ref, 'nodeComparisons': checks,
              'scope': 'Differential AST types/heights against preserved analyzer, known frame peaks, flat deep-stack analysis allocation samples. Tracemalloc is Python allocation peak, not process RSS.',
              'fixtures': records, 'memory': memory}
    if args.json_output:
        args.json_output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
