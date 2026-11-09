"""Measure generator instruction construction while protecting a fixture."""
import contextlib
import io
import json
from pathlib import Path
import random
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from wasm_vmp import JiexStart, core
import wasm_vmp.wasmvmp as engine_module

constructed = 0
original_add = engine_module.add_instr
original_engine = core.WasmVMP
captured = []


def counted_instruction(*args, **kwargs):
    global constructed
    constructed += 1
    return original_add(*args, **kwargs)


class CaptureEngine(original_engine):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        captured.append(self)


engine_module.add_instr = counted_instruction
core.WasmVMP = CaptureEngine
try:
    with contextlib.redirect_stdout(io.StringIO()):
        random.seed(20261109)
        processor = JiexStart(sys.argv[1])
        processor.parse_module()
        processor.encrypt_module(sys.argv[2], instruction_expansion_factor=int(sys.argv[3]))
    engine = captured[0]
    dedup = engine.generic_handler_dedup
    report = {'constructionCalls': constructed,
              'genericOccurrences': sum(map(len, engine.putongcodeInfo.values())),
              'retainedGenericHandlers': sum(map(len, dedup.representatives.values())),
              'outputBytes': Path(sys.argv[2]).stat().st_size}
    print(json.dumps(report))
finally:
    engine_module.add_instr = original_add
    core.WasmVMP = original_engine
