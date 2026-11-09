#!/usr/bin/env python3
"""Source-generated semantic regressions for WASM VMP dispatch changes.

The fixtures below are built from explicit source operations, not inspected
from a protected artifact. --engine-source can select a preserved Python
interpreter-generator source file for comparison with the current version.
"""
from pathlib import Path
import argparse
import contextlib
import importlib.util
import io
import json
import random
import struct
import subprocess
import sys
import tempfile
import types

from build_md5 import (add, binary, call, choose, const, get, load, loop, mul,
                       put, section, store, string, uleb, vec)

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from wasm_vmp import JiexStart
import wasm_vmp.core as core


def signed_leb(value):
    out = bytearray()
    while True:
        byte = value & 127
        value >>= 7
        done = (value == 0 and not byte & 64) or (value == -1 and byte & 64)
        out.append(byte | (0 if done else 128))
        if done:
            return bytes(out)


def i64(value):
    return b'\x42' + signed_leb(value)


def f32(value):
    return b'\x43' + struct.pack('<f', value)


def f64(value):
    return b'\x44' + struct.pack('<d', value)


def signature(params, results):
    return b'\x60' + vec([bytes([x]) for x in params]) + vec([bytes([x]) for x in results])


def function(locals_, code):
    declarations = vec([uleb(count) + bytes([kind]) for count, kind in locals_])
    body = declarations + code + b'\x0b'
    return uleb(len(body)) + body


def module(types_, functions):
    # Retain the historical dummy for comparisons with pre-v2 engines. Current
    # core protects every original function, including this final function.
    funcs = list(functions) + [('dummy', 0, [], const(0))]
    exports = [string(name) + b'\x00' + uleb(i) for i, (name, *_) in enumerate(funcs[:-1])]
    exports += [string('memory') + b'\x02\x00', string('counter') + b'\x03\x00']
    return b'\x00asm\x01\x00\x00\x00' + b''.join([
        section(1, vec(types_)),
        section(3, vec([uleb(type_id) for _, type_id, _, _ in funcs])),
        section(5, vec([b'\x01' + uleb(512) + uleb(4096)])),
        section(6, vec([b'\x7f\x01' + const(123) + b'\x0b'])),
        section(7, vec(exports)),
        section(10, vec([function(locals_, code) for _, _, locals_, code in funcs])),
        section(11, vec([b'\x00' + const(1024) + b'\x0b\x01\x37'])),
    ])


def fixtures():
    # Type 0 is intentionally () -> i32 so the final dummy is valid everywhere.
    types_i32 = [signature([], [0x7f]), signature([0x7f], [0x7f]), signature([0x7f, 0x7f], [0x7f])]
    arith = binary(0x77, add(binary(0x73, get(0), get(1)), mul(get(0), get(1))), const(5))
    nested = choose(binary(0x48, get(0), const(0)),
                    choose(binary(0x48, get(0), const(-5)), const(11) + put(1), const(22) + put(1)),
                    choose(binary(0x49, get(0), const(16)), const(33) + put(1), const(44) + put(1))) + get(1)
    sum_loop = const(0) + put(1) + const(0) + put(2)
    sum_loop += loop(binary(0x4f, get(1), get(0)),
                     add(get(1), const(1)) + put(1) + add(get(2), get(1)) + put(2)) + get(2)
    callee = add(mul(get(0), const(3)), const(1))
    caller = get(0) + call(3) + call(3)
    recurse = choose(binary(0x4d, get(0), const(1)), const(1) + put(1),
                     mul(get(0), binary(0x6b, get(0), const(1)) + call(5)) + put(1)) + get(1)
    memory = store(get(0), mul(get(1), const(3)), 12)
    memory += add(get(1), const(7)) + b'\x24\x00'
    memory += binary(0x73, load(get(0), 12), b'\x23\x00')
    early = choose(binary(0x48, get(0), const(0)), const(-7) + b'\x0f') + add(get(0), const(5))
    implicit_if = const(77) + get(0) + b'\x0d\x00\x1a' + const(88)
    implicit_br = const(123) + b'\x0c\x00' + const(0)
    m32 = module(types_i32, [
        ('arith', 2, [], arith), ('nested', 1, [(1, 0x7f)], nested),
        ('sum_loop', 1, [(2, 0x7f)], sum_loop), ('callee', 1, [], callee),
        ('caller', 1, [], caller), ('factorial', 1, [(1, 0x7f)], recurse),
        ('memory_roundtrip', 2, [], memory), ('early', 1, [], early),
        ('implicit_if', 1, [], implicit_if), ('implicit_br', 0, [], implicit_br),
    ])
    types64 = [signature([], [0x7f]), signature([0x7e, 0x7e], [0x7e]), signature([0x7e], [0x7e])]
    wide = binary(0x85, binary(0x7c, get(0), get(1)), binary(0x89, get(0), i64(7)))
    square = binary(0x7c, get(0), i64(5)) + b'\x22\x01' + get(1) + b'\x7e'
    m64 = module(types64, [('wide', 1, [], wide), ('square', 2, [(1, 0x7e)], square)])
    typesf32 = [signature([], [0x7f]), signature([0x7d, 0x7d], [0x7d]), signature([0x7d], [0x7d])]
    float32 = binary(0x92, binary(0x94, get(0), get(1)), get(0))
    abs32 = choose(binary(0x5d, get(0), f32(0)), get(0) + b'\x8c' + put(1), get(0) + put(1)) + get(1)
    mf32 = module(typesf32, [('float32', 1, [], float32), ('abs32', 2, [(1, 0x7d)], abs32)])
    typesf64 = [signature([], [0x7f]), signature([0x7c, 0x7c], [0x7c]), signature([0x7c], [0x7c])]
    float64 = binary(0xa3, binary(0xa2, get(0), get(1)), binary(0xa0, get(1), f64(1)))
    square64 = get(0) + b'\x22\x01' + get(1) + b'\xa2'
    mf64 = module(typesf64, [('float64', 1, [], float64), ('square64', 2, [(1, 0x7c)], square64)])
    return [('i32_control_memory_calls', m32), ('i64', m64), ('f32', mf32), ('f64', mf64)]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--engine-source', type=Path)
    parser.add_argument('--json-output', type=Path)
    parser.add_argument('--allow-known-baseline-failures', action='store_true',
                        help='For historical baselines only: allow the old implicit-function br_if failures.')
    parser.add_argument('--strict', action='store_true',
                        help='Fail also for the documented pre-existing implicit-function br_if defect.')
    args = parser.parse_args()
    if args.engine_source:
        spec = importlib.util.spec_from_file_location('wasm_vmp._dispatch_regression_engine', args.engine_source.resolve())
        selected = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(selected)
        core.WasmVMP = selected.WasmVMP
    results = []
    with tempfile.TemporaryDirectory(prefix='wasmvmp_dispatch_') as dirname:
        temp = Path(dirname)
        for name, wasm in fixtures():
            original, protected = temp / (name + '.wasm'), temp / (name + '_vmp.wasm')
            original.write_bytes(wasm)
            log = io.StringIO()
            try:
                with contextlib.redirect_stdout(log):
                    random.seed(20261109)
                    processor = JiexStart(str(original))
                    processor.parse_module()
                    processor.encrypt_module(str(protected), not_jeb=False)
                command = ['node', str(Path(__file__).with_name('check_dispatch.mjs')), name, str(original), str(protected)]
                observed = subprocess.run(command, capture_output=True, text=True, timeout=45)
                record = json.loads(observed.stdout) if observed.stdout else {'passed': False, 'error': observed.stderr}
                record['suite'] = name
                record['protectionBytes'] = protected.stat().st_size
                if observed.returncode:
                    record['stderr'] = observed.stderr
                results.append(record)
            except Exception as exc:
                results.append({'suite': name, 'passed': False, 'error': repr(exc), 'generationLog': log.getvalue()[-3000:]})
    report = {'engine': str(args.engine_source or 'current project source'), 'passed': all(x['passed'] for x in results),
              'passedSupportedScope': all(x.get('passedSupportedScope', False) for x in results),
              'knownPreexistingFailureCount': sum(x.get('knownPreexistingFailureCount', 0) for x in results),
              'suites': results, 'checks': sum(x.get('checks', 0) for x in results),
              'scope': 'Source-built control flow, direct/recursive calls, memory/global operations, i64/f32/f64 typed values, repeated calls. Not exhaustive for all WASM features.',
              'historicalIssue': 'Implicit-function br_if failed in the pre-v2 baseline. Current source must pass all checks; only explicit --allow-known-baseline-failures permits that historical failure.'}
    text = json.dumps(report, indent=2)
    print(text)
    if args.json_output:
        args.json_output.write_text(text + '\n')
    return 0 if report['passedSupportedScope' if args.allow_known_baseline_failures and not args.strict else 'passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
