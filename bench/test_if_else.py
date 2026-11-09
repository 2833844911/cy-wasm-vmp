#!/usr/bin/env python3
"""Source-built regression: check an ordinary if/else before and after VMP."""
from pathlib import Path
import contextlib
import io
import json
import random
import subprocess
import sys
import types

from build_md5 import (
    binary, choose, const, function, get, put, section, string, uleb, vec,
)

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
try:
    import symbol
except ModuleNotFoundError:
    symbol = types.ModuleType("symbol")
    symbol.continue_stmt = 0
    sys.modules["symbol"] = symbol
from wasm_vmp import JiexStart


def build_regression():
    # Source meaning: branch(x) { int result; if(x<16) result=1;
    #                              else result=2; return result; }
    body = choose(binary(0x49, get(0), const(16)),
                  const(1) + put(1), const(2) + put(1)) + get(1)
    return b"\x00asm\x01\x00\x00\x00" + b"".join([
        section(1, vec([b"\x60\x01\x7f\x01\x7f", b"\x60\x00\x01\x7f"])),
        section(3, vec([uleb(0), uleb(1)])),
        section(5, vec([b"\x01" + uleb(512) + uleb(4096)])),
        section(6, vec([b"\x7f\x01" + const(1048576) + b"\x0b"])),
        section(7, vec([string("branch") + b"\x00\x00"])),
        section(10, vec([function(1, body), function(0, const(0))])),
        section(11, vec([b"\x00" + const(1024) + b"\x0b\x01\x00"])),
    ])


def main():
    original = Path(__file__).with_name("if_else_original.wasm")
    protected = Path(__file__).with_name("if_else_vmp.wasm")
    original.write_bytes(build_regression())
    random.seed(1)
    with contextlib.redirect_stdout(io.StringIO()):
        processor = JiexStart(str(original))
        processor.parse_module()
        processor.encrypt_module(str(protected), not_jeb=False, selected_functions=[0])
    script = """
      const fs=require('fs');
      const result={};
      for (const path of process.argv.slice(1)) {
        const module=new WebAssembly.Module(fs.readFileSync(path));
        const e=new WebAssembly.Instance(module,{}).exports;
        result[path.split('/').pop()]=[0,15,16,100].map(x=>[x,e.branch(x)]);
      }
      console.log(JSON.stringify(result));
    """
    completed = subprocess.run(["node", "-e", script, str(original), str(protected)],
                               capture_output=True, text=True, check=True)
    observed = json.loads(completed.stdout)
    print(json.dumps(observed, indent=2))
    expected = [[0, 1], [15, 1], [16, 2], [100, 2]]
    assert all(values == expected for values in observed.values()), "if/else semantics changed after VMP"


if __name__ == "__main__":
    main()
