"""Roundtrip CODE without changing other sections; exercise codec metadata only."""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from wasm_vmp.codec import WasmCodec
from wasm_vmp.utils import write_leb128_unsigned

codec = WasmCodec()
source = Path(sys.argv[1]).read_bytes()
sections = []
offset = 8
while offset < len(source):
    section, offset = codec.read_next_section(source, offset)
    sections.append(section)
    kind, payload = section['section_id'], section['data']
    if kind == 1:
        codec.decode_type_section(payload)
    elif kind == 3:
        codec.decode_function_section(payload)
    elif kind == 7:
        codec.decode_export_section(payload)

code_section = next(s for s in sections if s['section_id'] == 10)
functions = codec.decode_code_section(code_section)
operations = []
for function in functions:
    for instruction in function['code']:
        if 0x28 <= instruction[1] <= 0x3E:
            metadata = instruction[4] if len(instruction) > 4 else {}
            operations.append({'opcode': instruction[1], 'memoryIndex': metadata.get('memory_index', 0),
                               'alignment': instruction[2][0]['val'], 'offset': instruction[2][1]['val']})
code_section['data'] = codec.encode_code_section(functions)
result = bytearray(source[:8])
for section in sections:
    result.append(section['section_id'])
    result.extend(write_leb128_unsigned(len(section['data'])))
    result.extend(section['data'])
Path(sys.argv[2]).write_bytes(result)
Path(sys.argv[3]).write_text(json.dumps({'operations': operations}, indent=2) + '\n')
