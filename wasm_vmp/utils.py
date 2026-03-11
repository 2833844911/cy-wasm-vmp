from .consts import WASM_OPCODES
import struct

def write_leb128_unsigned(val, min_bytes=0):
    val = int(val)
    if val < 0: val = 0
    result = bytearray()
    while True:
        byte = val & 0x7F
        val >>= 7
        if val == 0 and (len(result) + 1) >= min_bytes:
            result.append(byte)
            break
        else:
            byte |= 0x80
            result.append(byte)
    return bytes(result)

def read_leb128_unsigned(data, offset):
    result = 0
    shift = 0
    bytes_read = 0
    while True:
        if offset + bytes_read >= len(data): break
        byte = data[offset + bytes_read]
        bytes_read += 1
        result |= (byte & 0x7F) << shift
        if (byte & 0x80) == 0:
            break
        shift += 7
    return result, bytes_read

def write_leb128_signed(val, min_bytes=0):
    val = int(val)
    result = bytearray()
    while True:
        byte = val & 0x7F
        val >>= 7
        is_termination_val = (val == 0 and (byte & 0x40) == 0) or \
                             (val == -1 and (byte & 0x40) != 0)
        current_len = len(result) + 1
        if is_termination_val and current_len >= min_bytes:
            result.append(byte)
            break
        else:
            byte |= 0x80
            result.append(byte)
    return bytes(result)

def read_leb128_signed(data, offset):
    result = 0
    shift = 0
    count = 0
    byte = 0
    while True:
        if offset + count >= len(data): break
        byte = data[offset + count]
        result |= (byte & 0x7F) << shift
        count += 1
        shift += 7
        if not (byte & 0x80):
            break

    if byte & 0x40:
        result |= (~0 << shift)

    return result, count

def read_utf8_string(data, offset):
    string_length, length_bytes = read_leb128_unsigned(data, offset)
    offset += length_bytes

    if string_length > 0:
        string_data = data[offset:offset + string_length]
        try:
            string_value = string_data.decode('utf-8')
        except UnicodeDecodeError:
            string_value = f"<invalid UTF-8: {string_data.hex()}>"
    else:
        string_value = ""

    total_bytes = length_bytes + string_length
    return string_value, total_bytes

def get_opcode_name(opcode):
    return WASM_OPCODES.get(opcode, f"unknown_0x{opcode:02x}")

def pack_op(val):
    return {'val': val, 'len': 0}

def add_instr(opcode, operands=None):
    name = get_opcode_name(opcode)
    raw = bytearray([opcode])

    ops_list = []
    if operands is not None:
        if isinstance(operands, list):
            ops_list = operands
        else:
            ops_list = [operands]

    # Simple Raw Bytes Generation (for known injected instructions)
    # Simple Raw Bytes Generation (for known injected instructions)
    if opcode in [0x02, 0x03, 0x04]:  # Block/Loop/If
        if isinstance(operands, dict):
             # Type Index (s33)
             raw.extend(write_leb128_signed(operands['val']))
        elif isinstance(operands, int):
             # Block Type (e.g. 0x40 or value type)
             raw.append(operands)

    elif opcode == 0x41:  # i32.const
        raw.extend(write_leb128_signed(operands['val']))
    elif opcode in [0x20, 0x21, 0x0D, 0x0C, 0x10]:  # Index
        raw.extend(write_leb128_unsigned(operands['val']))
    elif opcode in [0x2D, 0x3A]:  # Load/Store
        raw.extend(b'\x00\x00')  # align=0, offset=0
    # Note: This list might need extension if you use other opcodes in add_instr

    return [name, opcode, ops_list, bytes(raw)]
