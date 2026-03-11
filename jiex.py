import struct
import sys

# WebAssembly magic and version constants
WASM_MAGIC = b'\x00\x61\x73\x6D'  # 魔数: '0x00 0x61 0x73 0x6D' (对应 'wasm')
WASM_VERSION = b'\x01\x00\x00\x00'  # 版本: '0x01 0x00 0x00 0x00'

# Section codes (对应 V8 中的 SectionCode 枚举)
SECTION_NAMES = {
    0: "Custom",
    1: "Type",
    2: "Import",
    3: "Function",
    4: "Table",
    5: "Memory",
    6: "Global",
    7: "Export",
    8: "Start",
    9: "Element",
    10: "Code",
    11: "Data",
    12: "DataCount",
    13: "Tag"
}

# Value type codes (对应 V8 的 ValueTypeCode)
VALUE_TYPE_NAMES = {
    0x7F: "i32",
    0x7E: "i64",
    0x7D: "f32",
    0x7C: "f64",
    0x7B: "v128",
    0x70: "funcref",
    0x6F: "externref",
    0x40: "void"
}

# Type definition codes
WASM_FUNCTION_TYPE_CODE = 0x60

# Import/Export kinds (对应 ImportExportKindCode)
IMPORT_EXPORT_KIND_NAMES = {
    0: "Function",
    1: "Table",
    2: "Memory",
    3: "Global",
    4: "Tag"
}

EXTERNAL_FUNCTION = 0
EXTERNAL_TABLE = 1
EXTERNAL_MEMORY = 2
EXTERNAL_GLOBAL = 3
EXTERNAL_TAG = 4

# Memory limits flags (对应 V8 的内存标志)
MEMORY_NO_MAXIMUM = 0x00  # 只有初始大小，无最大值
MEMORY_WITH_MAXIMUM = 0x01  # 有初始大小和最大值
MEMORY_SHARED_NO_MAXIMUM = 0x02  # 共享内存，无最大值
MEMORY_SHARED_WITH_MAXIMUM = 0x03  # 共享内存，有最大值
MEMORY64_NO_MAXIMUM = 0x04  # 64位内存，无最大值
MEMORY64_WITH_MAXIMUM = 0x05  # 64位内存，有最大值

# WASM 操作码字典 (对应 V8: wasm-opcodes.h)
# 这个字典包含了所有标准 WASM 操作码的映射
WASM_OPCODES = {
    # 控制流指令 (0x00-0x1F) - wasm-opcodes.h 第34-55行
    0x00: "unreachable",
    0x01: "nop",
    0x02: "block",
    0x03: "loop",
    0x04: "if",
    0x05: "else",
    0x0B: "end",
    0x0C: "br",
    0x0D: "br_if",
    0x0E: "br_table",
    0x0F: "return",

    # 函数调用 (0x10-0x15) - wasm-opcodes.h 第59-64行
    0x10: "call",
    0x11: "call_indirect",
    0x12: "return_call",
    0x13: "return_call_indirect",

    # 变量操作 (0x1A-0x26) - wasm-opcodes.h 第65-74行
    0x1A: "drop",
    0x1B: "select",
    0x20: "local.get",
    0x21: "local.set",
    0x22: "local.tee",
    0x23: "global.get",
    0x24: "global.set",
    0x25: "table.get",
    0x26: "table.set",

    # 内存加载 (0x28-0x35) - wasm-opcodes.h 第86-99行
    0x28: "i32.load",
    0x29: "i64.load",
    0x2A: "f32.load",
    0x2B: "f64.load",
    0x2C: "i32.load8_s",
    0x2D: "i32.load8_u",
    0x2E: "i32.load16_s",
    0x2F: "i32.load16_u",
    0x30: "i64.load8_s",
    0x31: "i64.load8_u",
    0x32: "i64.load16_s",
    0x33: "i64.load16_u",
    0x34: "i64.load32_s",
    0x35: "i64.load32_u",

    # 内存存储 (0x36-0x3E) - wasm-opcodes.h 第103-111行
    0x36: "i32.store",
    0x37: "i64.store",
    0x38: "f32.store",
    0x39: "f64.store",
    0x3A: "i32.store8",
    0x3B: "i32.store16",
    0x3C: "i64.store8",
    0x3D: "i64.store16",
    0x3E: "i64.store32",

    # 内存操作 (0x3F-0x40) - wasm-opcodes.h 第115-116行
    0x3F: "memory.size",
    0x40: "memory.grow",

    # 常量 (0x41-0x44) - wasm-opcodes.h 第75-78行
    0x41: "i32.const",
    0x42: "i64.const",
    0x43: "f32.const",
    0x44: "f64.const",

    # i32 比较 (0x45-0x4F) - wasm-opcodes.h 第131-141行
    0x45: "i32.eqz",
    0x46: "i32.eq",
    0x47: "i32.ne",
    0x48: "i32.lt_s",
    0x49: "i32.lt_u",
    0x4A: "i32.gt_s",
    0x4B: "i32.gt_u",
    0x4C: "i32.le_s",
    0x4D: "i32.le_u",
    0x4E: "i32.ge_s",
    0x4F: "i32.ge_u",

    # i64 比较 (0x50-0x5A) - wasm-opcodes.h 第142-152行
    0x50: "i64.eqz",
    0x51: "i64.eq",
    0x52: "i64.ne",
    0x53: "i64.lt_s",
    0x54: "i64.lt_u",
    0x55: "i64.gt_s",
    0x56: "i64.gt_u",
    0x57: "i64.le_s",
    0x58: "i64.le_u",
    0x59: "i64.ge_s",
    0x5A: "i64.ge_u",

    # f32 比较 (0x5B-0x60) - wasm-opcodes.h 第153-158行
    0x5B: "f32.eq",
    0x5C: "f32.ne",
    0x5D: "f32.lt",
    0x5E: "f32.gt",
    0x5F: "f32.le",
    0x60: "f32.ge",

    # f64 比较 (0x61-0x66) - wasm-opcodes.h 第159-164行
    0x61: "f64.eq",
    0x62: "f64.ne",
    0x63: "f64.lt",
    0x64: "f64.gt",
    0x65: "f64.le",
    0x66: "f64.ge",

    # i32 算术 (0x67-0x78) - wasm-opcodes.h 第165-179行
    0x67: "i32.clz",
    0x68: "i32.ctz",
    0x69: "i32.popcnt",
    0x6A: "i32.add",
    0x6B: "i32.sub",
    0x6C: "i32.mul",
    0x6D: "i32.div_s",
    0x6E: "i32.div_u",
    0x6F: "i32.rem_s",
    0x70: "i32.rem_u",
    0x71: "i32.and",
    0x72: "i32.or",
    0x73: "i32.xor",
    0x74: "i32.shl",
    0x75: "i32.shr_s",
    0x76: "i32.shr_u",
    0x77: "i32.rotl",
    0x78: "i32.rotr",

    # i64 算术 (0x79-0x8A) - wasm-opcodes.h 第180-194行
    0x79: "i64.clz",
    0x7A: "i64.ctz",
    0x7B: "i64.popcnt",
    0x7C: "i64.add",
    0x7D: "i64.sub",
    0x7E: "i64.mul",
    0x7F: "i64.div_s",
    0x80: "i64.div_u",
    0x81: "i64.rem_s",
    0x82: "i64.rem_u",
    0x83: "i64.and",
    0x84: "i64.or",
    0x85: "i64.xor",
    0x86: "i64.shl",
    0x87: "i64.shr_s",
    0x88: "i64.shr_u",
    0x89: "i64.rotl",
    0x8A: "i64.rotr",

    # f32 算术 (0x8B-0x98) - wasm-opcodes.h 第195-208行
    0x8B: "f32.abs",
    0x8C: "f32.neg",
    0x8D: "f32.ceil",
    0x8E: "f32.floor",
    0x8F: "f32.trunc",
    0x90: "f32.nearest",
    0x91: "f32.sqrt",
    0x92: "f32.add",
    0x93: "f32.sub",
    0x94: "f32.mul",
    0x95: "f32.div",
    0x96: "f32.min",
    0x97: "f32.max",
    0x98: "f32.copysign",

    # f64 算术 (0x99-0xA6) - wasm-opcodes.h 第209-222行
    0x99: "f64.abs",
    0x9A: "f64.neg",
    0x9B: "f64.ceil",
    0x9C: "f64.floor",
    0x9D: "f64.trunc",
    0x9E: "f64.nearest",
    0x9F: "f64.sqrt",
    0xA0: "f64.add",
    0xA1: "f64.sub",
    0xA2: "f64.mul",
    0xA3: "f64.div",
    0xA4: "f64.min",
    0xA5: "f64.max",
    0xA6: "f64.copysign",

    # 类型转换 (0xA7-0xC4) - wasm-opcodes.h 第223-252行
    0xA7: "i32.wrap_i64",
    0xA8: "i32.trunc_f32_s",
    0xA9: "i32.trunc_f32_u",
    0xAA: "i32.trunc_f64_s",
    0xAB: "i32.trunc_f64_u",
    0xAC: "i64.extend_i32_s",
    0xAD: "i64.extend_i32_u",
    0xAE: "i64.trunc_f32_s",
    0xAF: "i64.trunc_f32_u",
    0xB0: "i64.trunc_f64_s",
    0xB1: "i64.trunc_f64_u",
    0xB2: "f32.convert_i32_s",
    0xB3: "f32.convert_i32_u",
    0xB4: "f32.convert_i64_s",
    0xB5: "f32.convert_i64_u",
    0xB6: "f32.demote_f64",
    0xB7: "f64.convert_i32_s",
    0xB8: "f64.convert_i32_u",
    0xB9: "f64.convert_i64_s",
    0xBA: "f64.convert_i64_u",
    0xBB: "f64.promote_f32",
    0xBC: "i32.reinterpret_f32",
    0xBD: "i64.reinterpret_f64",
    0xBE: "f32.reinterpret_i32",
    0xBF: "f64.reinterpret_i64",
    0xC0: "i32.extend8_s",
    0xC1: "i32.extend16_s",
    0xC2: "i64.extend8_s",
    0xC3: "i64.extend16_s",
    0xC4: "i64.extend32_s",

    # 引用类型 (0xD0-0xD6)
    0xD0: "ref.null",
    0xD1: "ref.is_null",
    0xD2: "ref.func",
    0xD3: "ref.as_non_null",
    0xD4: "br_on_null",
    0xD5: "ref.eq",
    0xD6: "br_on_non_null",
}


def get_opcode_name(opcode):
    """
    根据操作码获取助记符名称
    :param opcode: 操作码字节
    :return: 操作码助记符字符串
    """
    return WASM_OPCODES.get(opcode, f"unknown_0x{opcode:02x}")


def find_opcode_by_name(name):
    """
    根据助记符名称查找操作码
    :param name: 操作码助记符（如 "i32.add"）
    :return: 操作码字节，如果未找到返回 None
    """
    for opcode, mnemonic in WASM_OPCODES.items():
        if mnemonic == name:
            return opcode
    return None


def read_leb128_unsigned(data, offset):
    """
    读取 LEB128 编码的无符号整数（用于读取节长度等）
    :param data: 字节数据
    :param offset: 当前偏移
    :return: (值, 读取的字节数)
    """
    result = 0
    shift = 0
    bytes_read = 0

    while True:
        byte = data[offset + bytes_read]
        bytes_read += 1
        result |= (byte & 0x7F) << shift
        if (byte & 0x80) == 0:
            break
        shift += 7

    return result, bytes_read


def read_utf8_string(data, offset):
    """
    读取 UTF-8 字符串（LEB128 长度前缀）
    对应 V8: consume_string

    :param data: 字节数据
    :param offset: 当前偏移
    :return: (字符串, 总字节数)
    """
    # 读取字符串长度
    string_length, length_bytes = read_leb128_unsigned(data, offset)
    offset += length_bytes

    # 读取字符串内容
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


def decode_module_header(bytes_data, offset=0):
    """
    解码 WebAssembly 模块头部，检查魔数和版本。
    对应 V8: module-decoder.cc 中的 DecodeModuleHeader

    :param bytes_data: 包含 WebAssembly 数据的字节流
    :param offset: 数据的偏移量，默认从 0 开始
    :return: 无返回值，但在失败时抛出错误信息
    """
    print(f"\n{'=' * 60}")
    print(f"[DecodeModuleHeader] offset={offset}")
    print(f"{'=' * 60}")

    # 获取魔数
    magic_word = bytes_data[offset:offset + 4]

    # 检查魔数是否匹配
    if magic_word != WASM_MAGIC:
        expected_magic = ' '.join(f"{b:02x}" for b in WASM_MAGIC)
        found_magic = ' '.join(f"{b:02x}" for b in magic_word)
        raise ValueError(f"Expected magic word {expected_magic}, found {found_magic}")

    # 获取版本号
    version = bytes_data[offset + 4:offset + 8]

    # 检查版本号是否匹配
    if version != WASM_VERSION:
        expected_version = ' '.join(f"{b:02x}" for b in WASM_VERSION)
        found_version = ' '.join(f"{b:02x}" for b in version)
        raise ValueError(f"Expected version {expected_version}, found {found_version}")

    print(f"✓ Magic: {magic_word.hex()} (valid)")
    print(f"✓ Version: {version.hex()} (valid)")
    print(f"→ Module header size: 8 bytes")


class SectionIterator:
    """
    节迭代器，对应 V8 中的 WasmSectionIterator
    用于遍历 WASM 模块中的各个节
    """

    def __init__(self, data, offset):
        self.data = data
        self.offset = offset
        self.section_start = offset
        self.section_id = None
        self.section_length = None
        self.payload_start = None
        self.payload_length = None
        self.section_end = None

    def read_next_section(self):
        """
        读取下一个节的头部信息
        对应 V8: WasmSectionIterator::next()
        :return: True 如果成功读取，False 如果没有更多节
        """
        if self.offset >= len(self.data):
            return False

        # 记录节的起始位置
        self.section_start = self.offset

        # 读取节 ID (1 byte)
        self.section_id = self.data[self.offset]
        self.offset += 1

        # 读取节长度 (LEB128)
        self.section_length, length_bytes = read_leb128_unsigned(self.data, self.offset)
        self.offset += length_bytes

        # payload 起始位置（跳过 section_id 和 length）
        self.payload_start = self.offset
        self.payload_length = self.section_length

        # 节结束位置
        self.section_end = self.payload_start + self.payload_length

        return True

    def get_section_header_length(self):
        """返回节头的长度（Section ID + Length 字段）"""
        return self.payload_start - self.section_start

    def advance_to_next(self):
        """移动到下一个节"""
        self.offset = self.section_end


def decode_type_section(payload_data):
    """
    解析 Type Section (节 ID = 1)
    对应 V8: module-decoder.cc 中的 DecodeTypeSection (第 671 行)

    Type Section 定义了模块中所有的函数签名

    :param payload_data: Type Section 的 payload 数据
    :return: 解析出的类型列表
    """
    print(f"  │")
    print(f"  │  [DecodeTypeSection]")

    # 第 672 行：读取类型数量
    types_count, bytes_read = read_leb128_unsigned(payload_data, 0)
    offset = bytes_read

    print(f"  │  ├─ Types count: {types_count}")

    types = []

    # 第 676-683 行：简化版的类型解析（不支持 GC）
    for i in range(types_count):
        if offset >= len(payload_data):
            break

        print(f"  │  │")
        print(f"  │  ├─ [Type #{i}]")

        # 第 679 行：期待函数类型码 0x60
        type_code = payload_data[offset]
        offset += 1

        if type_code != WASM_FUNCTION_TYPE_CODE:
            print(f"  │  │  ⚠ Unexpected type code: 0x{type_code:02x} (expected 0x60)")
            print(f"  │  │  → 可能是 GC 扩展类型（struct/array）或错误")
            continue

        # 第 680 行：consume_sig - 读取函数签名
        # 函数签名格式：参数数量 + 参数类型列表 + 返回值数量 + 返回值类型列表

        # 读取参数数量
        param_count, pb = read_leb128_unsigned(payload_data, offset)
        offset += pb
        print(f"  │  │  ├─ Param count: {param_count}")

        # 读取参数类型
        params = []
        for p in range(param_count):
            if offset >= len(payload_data):
                break
            param_type = payload_data[offset]
            offset += 1
            type_name = VALUE_TYPE_NAMES.get(param_type, f"0x{param_type:02x}")
            params.append(type_name)

        print(f"  │  │  ├─ Params: ({', '.join(params)})")

        # 读取返回值数量
        result_count, rb = read_leb128_unsigned(payload_data, offset)
        offset += rb
        print(f"  │  │  ├─ Result count: {result_count}")

        # 读取返回值类型
        results = []
        for r in range(result_count):
            if offset >= len(payload_data):
                break
            result_type = payload_data[offset]
            offset += 1
            type_name = VALUE_TYPE_NAMES.get(result_type, f"0x{result_type:02x}")
            results.append(type_name)

        result_str = ', '.join(results) if results else 'void'
        print(f"  │  │  └─ Results: ({result_str})")

        # 第 682 行：add_signature
        signature = {
            'index': i,
            'params': params,
            'results': results,
            'signature_str': f"({', '.join(params)}) -> ({result_str})"
        }
        types.append(signature)

        print(f"  │  │     Signature: {signature['signature_str']}")

    print(f"  │  │")
    print(f"  │  └─ Total types parsed: {len(types)}")

    return types


def decode_import_section(payload_data):
    """
    解析 Import Section (节 ID = 2)
    对应 V8: module-decoder.cc 中的 DecodeImportSection (第 758 行)

    Import Section 声明模块需要从外部导入的资源

    :param payload_data: Import Section 的 payload 数据
    :return: 解析出的导入列表
    """
    print(f"  │")
    print(f"  │  [DecodeImportSection]")

    # 第 759-760 行：读取导入数量
    import_count, bytes_read = read_leb128_unsigned(payload_data, 0)
    offset = bytes_read

    print(f"  │  ├─ Import count: {import_count}")

    imports = []

    # 第 762-858 行：遍历每个导入项
    for i in range(import_count):
        if offset >= len(payload_data):
            break

        print(f"  │  │")
        print(f"  │  ├─ [Import #{i}]")

        # 第 774 行：读取模块名
        module_name, mb = read_utf8_string(payload_data, offset)
        offset += mb
        print(f"  │  │  ├─ Module name: \"{module_name}\"")

        # 第 775 行：读取字段名
        field_name, fb = read_utf8_string(payload_data, offset)
        offset += fb
        print(f"  │  │  ├─ Field name: \"{field_name}\"")

        # 第 776-777 行：读取导入类型
        if offset >= len(payload_data):
            break
        import_kind = payload_data[offset]
        offset += 1
        kind_name = IMPORT_EXPORT_KIND_NAMES.get(import_kind, f"Unknown(0x{import_kind:02x})")
        print(f"  │  │  ├─ Import kind: {import_kind} ({kind_name})")

        import_desc = {
            'index': i,
            'module_name': module_name,
            'field_name': field_name,
            'kind': import_kind,
            'kind_name': kind_name
        }

        # 第 778-857 行：根据类型解析导入描述
        if import_kind == EXTERNAL_FUNCTION:
            # 第 779-794 行：导入函数
            print(f"  │  │  │  → Function Import")
            # 读取类型索引（函数签名索引）
            type_index, tb = read_leb128_unsigned(payload_data, offset)
            offset += tb
            print(f"  │  │  └─ Type index: {type_index} (refers to Type #{type_index})")
            import_desc['type_index'] = type_index

        elif import_kind == EXTERNAL_TABLE:
            # 第 796-816 行：导入表
            print(f"  │  │  │  → Table Import")
            # 读取表的元素类型
            if offset >= len(payload_data):
                break
            elem_type = payload_data[offset]
            offset += 1
            type_name = VALUE_TYPE_NAMES.get(elem_type, f"0x{elem_type:02x}")
            print(f"  │  │  ├─ Element type: {type_name}")

            # 读取限制（初始大小、最大大小）
            if offset >= len(payload_data):
                break
            flags = payload_data[offset]
            offset += 1
            has_max = (flags & 0x01) != 0

            initial_size, ib = read_leb128_unsigned(payload_data, offset)
            offset += ib
            print(f"  │  │  ├─ Initial size: {initial_size}")

            if has_max:
                max_size, maxb = read_leb128_unsigned(payload_data, offset)
                offset += maxb
                print(f"  │  │  └─ Maximum size: {max_size}")
            else:
                print(f"  │  │  └─ Maximum size: (unbounded)")

            import_desc.update({
                'elem_type': type_name,
                'initial_size': initial_size,
                'has_max': has_max
            })

        elif import_kind == EXTERNAL_MEMORY:
            # 第 818-827 行：导入内存
            print(f"  │  │  │  → Memory Import")
            # 读取限制标志
            if offset >= len(payload_data):
                break
            flags = payload_data[offset]
            offset += 1
            has_max = (flags & 0x01) != 0
            is_shared = (flags & 0x02) != 0
            is_memory64 = (flags & 0x04) != 0

            # 读取初始页数
            initial_pages, ib = read_leb128_unsigned(payload_data, offset)
            offset += ib
            print(f"  │  │  ├─ Initial pages: {initial_pages} ({initial_pages * 65536} bytes)")

            if has_max:
                max_pages, maxb = read_leb128_unsigned(payload_data, offset)
                offset += maxb
                print(f"  │  │  ├─ Maximum pages: {max_pages} ({max_pages * 65536} bytes)")
            else:
                print(f"  │  │  ├─ Maximum pages: (unbounded)")

            if is_shared:
                print(f"  │  │  ├─ Shared: yes")
            if is_memory64:
                print(f"  │  │  └─ Memory64: yes")
            else:
                print(f"  │  │  └─ Memory type: 32-bit")

            import_desc.update({
                'initial_pages': initial_pages,
                'has_max': has_max,
                'is_shared': is_shared,
                'is_memory64': is_memory64
            })

        elif import_kind == EXTERNAL_GLOBAL:
            # 第 829-839 行：导入全局变量
            print(f"  │  │  │  → Global Import")
            # 读取值类型
            if offset >= len(payload_data):
                break
            value_type = payload_data[offset]
            offset += 1
            type_name = VALUE_TYPE_NAMES.get(value_type, f"0x{value_type:02x}")
            print(f"  │  │  ├─ Value type: {type_name}")

            # 读取可变性
            if offset >= len(payload_data):
                break
            mutability = payload_data[offset]
            offset += 1
            is_mutable = mutability == 1
            print(f"  │  │  └─ Mutability: {'mutable' if is_mutable else 'immutable'}")

            import_desc.update({
                'value_type': type_name,
                'mutable': is_mutable
            })

        elif import_kind == EXTERNAL_TAG:
            # 第 841-852 行：导入标签（异常处理）
            print(f"  │  │  │  → Tag Import (Exception Handling)")
            # 读取属性（通常被忽略）
            if offset >= len(payload_data):
                break
            attribute = payload_data[offset]
            offset += 1

            # 读取标签签名索引
            tag_sig_index, tb = read_leb128_unsigned(payload_data, offset)
            offset += tb
            print(f"  │  │  └─ Tag signature index: {tag_sig_index}")

            import_desc['tag_sig_index'] = tag_sig_index

        else:
            # 第 854-856 行：未知类型
            print(f"  │  │  └─ ⚠ Unknown import kind: 0x{import_kind:02x}")

        imports.append(import_desc)

    print(f"  │  │")
    print(f"  │  └─ Total imports parsed: {len(imports)}")

    # 统计导入的函数数量（用于计算函数索引偏移）
    global module_imported_func_count
    imported_func_count = sum(1 for imp in imports if imp['kind'] == EXTERNAL_FUNCTION)
    module_imported_func_count = imported_func_count
    print(f"  │     Note: 其中 {imported_func_count} 个是函数导入")

    return imports


def decode_function_section(payload_data):
    """
    解析 Function Section (节 ID = 3)
    对应 V8: module-decoder.cc 中的 DecodeFunctionSection (第 861 行)

    Function Section 声明模块内部定义的函数（不包括导入的函数）
    只包含函数的类型索引，函数体在 Code Section

    :param payload_data: Function Section 的 payload 数据
    :return: 解析出的函数列表
    """
    print(f"  │")
    print(f"  │  [DecodeFunctionSection]")

    # 第 862-863 行：读取函数数量
    functions_count, bytes_read = read_leb128_unsigned(payload_data, 0)
    offset = bytes_read

    print(f"  │  ├─ Functions count: {functions_count}")
    print(f"  │  │  (这些是模块内部定义的函数，不包括导入的函数)")

    functions = []

    # 第 872-885 行：遍历每个函数
    for i in range(functions_count):
        if offset >= len(payload_data):
            break

        # 第 883 行：读取类型索引（函数签名索引）
        type_index, tb = read_leb128_unsigned(payload_data, offset)
        offset += tb

        function_info = {
            'index': i,
            'type_index': type_index
        }
        functions.append(function_info)

        if i < 5 or i >= functions_count - 2:  # 只显示前5个和最后2个
            print(f"  │  ├─ Function #{i}: type_index = {type_index} (signature from Type #{type_index})")
        elif i == 5:
            print(f"  │  ├─ ... ({functions_count - 7} more functions) ...")

    print(f"  │  │")
    print(f"  │  └─ Total functions declared: {len(functions)}")
    print(f"  │     Note: 函数体代码在 Code Section (节 10)")

    return functions


def decode_export_section(payload_data):
    """
    解析 Export Section (节 7)
    对应 V8: module-decoder.cc 第 946-1017 行的 DecodeExportSection()

    Export Section 定义了模块向外部暴露的资源

    格式：
      export_section ::= export_count:u32 export*
      export ::= name:name kind:byte index:u32

    其中 kind 可以是：
      0x00 = Function (导出函数)
      0x01 = Table (导出表)
      0x02 = Memory (导出内存)
      0x03 = Global (导出全局变量)
      0x04 = Tag (导出标签，用于异常处理)

    :param payload_data: Export Section 的 payload 数据
    :return: 导出项列表
    """
    offset = 0


    exports = []

    print(f"  │")
    print(f"  │  ┌─ [Export Section Parsing]")
    print(f"  │  │")

    # 第 947-948 行：读取导出项数量
    if offset >= len(payload_data):
        print(f"  │  └─ Error: Insufficient data for export count")
        return exports

    export_count, bytes_read = read_leb128_unsigned(payload_data, offset)
    offset += bytes_read
    print(f"  │  ├─ Export count: {export_count}")
    print(f"  │  │")

    # 第 950-1017 行：遍历每个导出项
    for i in range(export_count):
        if i > 0:
            print(f"  │  │")

        print(f"  │  ├─ [Export #{i}]")

        export_info = {
            'index': i,
            'name': '',
            'kind': 0,
            'kind_name': '',
            'export_index': 0
        }

        # 第 961 行：读取导出名称（字符串）
        # consume_string: 读取 LEB128 长度 + UTF-8 字符串
        name, tb = read_utf8_string(payload_data, offset)
        offset += tb
        export_info['name'] = name
        print(f"  │  │  ├─ Export name: \"{name}\"")

        # 第 964 行：读取导出类型（1 字节）
        # exp->kind = consume_u8("export kind")
        if offset >= len(payload_data):
            print(f"  │  │  └─ Error: Insufficient data for export kind")
            break

        export_kind = payload_data[offset]
        offset += 1
        kind_name = IMPORT_EXPORT_KIND_NAMES.get(export_kind, f"Unknown(0x{export_kind:02x})")
        export_info['kind'] = export_kind
        export_info['kind_name'] = kind_name
        print(f"  │  │  ├─ Export kind: {export_kind} ({kind_name})")

        # 第 965-1015 行：根据导出类型读取索引
        # switch (exp->kind) { ... }
        if export_kind == EXTERNAL_FUNCTION:
            # 第 966-979 行：导出函数
            print(f"  │  │  │  → Function Export")
            # exp->index = consume_func_index(...)
            func_index, tb = read_leb128_unsigned(payload_data, offset)
            offset += tb
            export_info['export_index'] = func_index
            print(f"  │  │  └─ Function index: {func_index} (exports function #{func_index})")

        elif export_kind == EXTERNAL_TABLE:
            # 第 980-985 行：导出表
            print(f"  │  │  │  → Table Export")
            # exp->index = consume_table_index(...)
            table_index, tb = read_leb128_unsigned(payload_data, offset)
            offset += tb
            export_info['export_index'] = table_index
            print(f"  │  │  └─ Table index: {table_index} (exports table #{table_index})")

        elif export_kind == EXTERNAL_MEMORY:
            # 第 986-995 行：导出内存
            print(f"  │  │  │  → Memory Export")
            # uint32_t index = consume_u32v("memory index")
            mem_index, tb = read_leb128_unsigned(payload_data, offset)
            offset += tb
            export_info['export_index'] = mem_index
            # 第 990-991 行：WASM 1.0 只支持一个内存（索引必须为 0）
            if mem_index != 0:
                print(f"  │  │  │  Warning: Invalid memory index {mem_index} (expected 0)")
            print(f"  │  │  └─ Memory index: {mem_index}")

        elif export_kind == EXTERNAL_GLOBAL:
            # 第 996-1003 行：导出全局变量
            print(f"  │  │  │  → Global Export")
            # exp->index = consume_global_index(...)
            global_index, tb = read_leb128_unsigned(payload_data, offset)
            offset += tb
            export_info['export_index'] = global_index
            print(f"  │  │  └─ Global index: {global_index} (exports global #{global_index})")

        elif export_kind == EXTERNAL_TAG:
            # 第 1004-1012 行：导出标签（异常处理）
            print(f"  │  │  │  → Tag Export")
            # exp->index = consume_tag_index(...)
            tag_index, tb = read_leb128_unsigned(payload_data, offset)
            offset += tb
            export_info['export_index'] = tag_index
            print(f"  │  │  └─ Tag index: {tag_index} (exports tag #{tag_index})")

        else:
            # 第 1013-1015 行：无效的导出类型
            print(f"  │  │  └─ Error: Invalid export kind 0x{export_kind:02x}")
            break

        exports.append(export_info)

    print(f"  │  │")
    print(f"  │  └─ Total exports: {len(exports)}")

    # 收集导出的函数名（用于在 Code Section 显示）
    global module_function_names
    for exp in exports:
        if exp['kind'] == EXTERNAL_FUNCTION:
            func_index = exp['export_index']
            func_name = exp['name']
            module_function_names[func_index] = func_name
            print(f"  │     → 函数 #{func_index} = \"{func_name}\"")

    return exports


def decode_memory_section(payload_data):
    """
    解析 Memory Section (节 5)
    对应 V8: module-decoder.cc 第 915-927 行的 DecodeMemorySection()

    Memory Section 定义了模块的线性内存

    格式：
      memory_section ::= memory_count:u32 memory*
      memory ::= limits
      limits ::= flags:byte initial:u32 [maximum:u32]?

    其中 flags 可以是：
      0x00 = 只有初始大小
      0x01 = 有初始大小和最大值
      0x02 = 共享内存，无最大值
      0x03 = 共享内存，有最大值
      0x04 = 64位内存，无最大值
      0x05 = 64位内存，有最大值

    内存大小单位：页（page），1 页 = 64 KiB = 65536 字节

    :param payload_data: Memory Section 的 payload 数据
    :return: 内存定义列表
    """
    offset = 0
    memories = []

    print(f"  │")
    print(f"  │  ┌─ [Memory Section Parsing]")
    print(f"  │  │")

    # 第 916 行：读取内存数量
    # uint32_t memory_count = consume_count("memory count", kV8MaxWasmMemories);
    if offset >= len(payload_data):
        print(f"  │  └─ Error: Insufficient data for memory count")
        return memories

    memory_count, bytes_read = read_leb128_unsigned(payload_data, offset)
    offset += bytes_read
    print(f"  │  ├─ Memory count: {memory_count}")

    # WASM 1.0 规范：只允许最多 1 个内存
    if memory_count > 1:
        print(f"  │  │  Warning: WASM 1.0 only supports 1 memory, found {memory_count}")

    print(f"  │  │")

    # 第 918-926 行：遍历每个内存定义
    for i in range(memory_count):
        if i > 0:
            print(f"  │  │")

        print(f"  │  ├─ [Memory #{i}]")

        memory_info = {
            'index': i,
            'flags': 0,
            'initial': 0,
            'has_maximum': False,
            'maximum': 0,
            'is_shared': False,
            'is_memory64': False
        }

        # 第 920-921 行：读取标志字节
        # uint8_t flags = validate_memory_flags(...)
        if offset >= len(payload_data):
            print(f"  │  │  └─ Error: Insufficient data for memory flags")
            break

        flags = payload_data[offset]
        offset += 1
        memory_info['flags'] = flags

        # 解析标志
        flag_descriptions = []
        has_max = False
        is_shared = False
        is_memory64 = False

        if flags == MEMORY_NO_MAXIMUM:
            flag_descriptions.append("No maximum")
            has_max = False
        elif flags == MEMORY_WITH_MAXIMUM:
            flag_descriptions.append("With maximum")
            has_max = True
        elif flags == MEMORY_SHARED_NO_MAXIMUM:
            flag_descriptions.append("Shared, no maximum")
            has_max = False
            is_shared = True
        elif flags == MEMORY_SHARED_WITH_MAXIMUM:
            flag_descriptions.append("Shared, with maximum")
            has_max = True
            is_shared = True
        elif flags == MEMORY64_NO_MAXIMUM:
            flag_descriptions.append("Memory64, no maximum")
            has_max = False
            is_memory64 = True
        elif flags == MEMORY64_WITH_MAXIMUM:
            flag_descriptions.append("Memory64, with maximum")
            has_max = True
            is_memory64 = True
        else:
            flag_descriptions.append(f"Unknown(0x{flags:02x})")

        memory_info['has_maximum'] = has_max
        memory_info['is_shared'] = is_shared
        memory_info['is_memory64'] = is_memory64

        print(f"  │  │  ├─ Flags: 0x{flags:02x} ({', '.join(flag_descriptions)})")

        # 第 922-925 行：读取可调整大小的限制
        # consume_resizable_limits(..., &module_->initial_pages,
        #                          &module_->has_maximum_pages,
        #                          &module_->maximum_pages, flags)

        # 第 1781-1789 行：读取初始大小
        if offset >= len(payload_data):
            print(f"  │  │  └─ Error: Insufficient data for initial size")
            break

        initial_size, tb = read_leb128_unsigned(payload_data, offset)
        offset += tb
        memory_info['initial'] = initial_size

        # 内存大小以页为单位，1 页 = 64 KiB
        initial_bytes = initial_size * 65536
        print(f"  │  │  ├─ Initial size: {initial_size} pages ({initial_bytes} bytes = {initial_bytes // 1024} KiB)")

        # 第 1790-1805 行：如果标志指示有最大值，读取最大值
        # if (flags & 1)
        if has_max:
            if offset >= len(payload_data):
                print(f"  │  │  └─ Error: Insufficient data for maximum size")
                break

            maximum_size, tb = read_leb128_unsigned(payload_data, offset)
            offset += tb
            memory_info['maximum'] = maximum_size

            maximum_bytes = maximum_size * 65536
            print(
                f"  │  │  ├─ Maximum size: {maximum_size} pages ({maximum_bytes} bytes = {maximum_bytes // 1024} KiB)")

            # 验证最大值 >= 初始值
            if maximum_size < initial_size:
                print(f"  │  │  │  Warning: Maximum size ({maximum_size}) < Initial size ({initial_size})")
        else:
            print(f"  │  │  ├─ Maximum size: unlimited")

        # 额外信息
        if is_shared:
            print(f"  │  │  ├─ Shared: Yes (可以在多个线程间共享)")
            if not has_max:
                print(f"  │  │  │  Warning: Shared memory should have a maximum size")

        if is_memory64:
            print(f"  │  │  └─ Memory64: Yes (支持 64 位地址空间)")
        else:
            print(f"  │  │  └─ Memory64: No (32 位地址空间)")

        memories.append(memory_info)

    print(f"  │  │")
    print(f"  │  └─ Total memories: {len(memories)}")

    return memories


def decode_table_section(payload_data):
    """
    解析 Table Section (节 4)
    对应 V8: module-decoder.cc 第 889-913 行的 DecodeTableSection()

    Table Section 定义了模块的间接函数表（用于函数指针/动态调用）

    格式：
      table_section ::= table_count:u32 table*
      table ::= table_type limits [init_expr]?
      table_type ::= reftype (引用类型)
      limits ::= flags:byte initial:u32 [maximum:u32]?

    表类型（reftype）：
      0x70 = funcref (函数引用)
      0x6F = externref (外部引用)

    :param payload_data: Table Section 的 payload 数据
    :return: 表定义列表
    """
    offset = 0
    tables = []

    print(f"  │")
    print(f"  │  ┌─ [Table Section Parsing]")
    print(f"  │  │")

    # 第 890 行：读取表数量
    # uint32_t table_count = consume_count("table count", kV8MaxWasmTables);
    if offset >= len(payload_data):
        print(f"  │  └─ Error: Insufficient data for table count")
        return tables

    table_count, bytes_read = read_leb128_unsigned(payload_data, offset)
    offset += bytes_read
    print(f"  │  ├─ Table count: {table_count}")

    # WASM 1.0 规范：只允许最多 1 个表
    if table_count > 1:
        print(f"  │  │  Note: WASM 1.0 only supports 1 table, but multiple tables is allowed in newer proposals")

    print(f"  │  │")

    # 第 892-912 行：遍历每个表定义
    for i in range(table_count):
        if i > 0:
            print(f"  │  │")

        print(f"  │  ├─ [Table #{i}]")

        table_info = {
            'index': i,
            'type': 0,
            'type_name': '',
            'flags': 0,
            'initial': 0,
            'has_maximum': False,
            'maximum': 0
        }

        # 第 895-902 行：读取表类型（引用类型）
        # ValueType table_type = consume_reference_type();
        if offset >= len(payload_data):
            print(f"  │  │  └─ Error: Insufficient data for table type")
            break

        table_type = payload_data[offset]
        offset += 1
        table_info['type'] = table_type

        # 解析表类型
        if table_type == 0x70:
            type_name = "funcref"
        elif table_type == 0x6F:
            type_name = "externref"
        else:
            type_name = f"Unknown(0x{table_type:02x})"

        table_info['type_name'] = type_name
        print(f"  │  │  ├─ Table type: 0x{table_type:02x} ({type_name})")

        # 第 896-902 行：验证表类型
        # if (!WasmTable::IsValidTableType(table_type, module_.get()))
        if table_type not in [0x70, 0x6F]:
            print(f"  │  │  │  Warning: Currently, only funcref and externref are allowed as table types")

        # 第 904 行：读取标志字节
        # uint8_t flags = validate_table_flags("table elements");
        if offset >= len(payload_data):
            print(f"  │  │  └─ Error: Insufficient data for table flags")
            break

        flags = payload_data[offset]
        offset += 1
        table_info['flags'] = flags

        # 解析标志
        has_max = (flags & 0x01) != 0
        table_info['has_maximum'] = has_max

        flag_desc = "With maximum" if has_max else "No maximum"
        print(f"  │  │  ├─ Flags: 0x{flags:02x} ({flag_desc})")

        # 第 905-908 行：读取可调整大小的限制
        # consume_resizable_limits("table elements", "elements", ...,
        #                          &table->initial_size, &table->has_maximum_size,
        #                          &table->maximum_size, flags)

        # 读取初始大小（表元素数量）
        if offset >= len(payload_data):
            print(f"  │  │  └─ Error: Insufficient data for initial size")
            break

        initial_size, tb = read_leb128_unsigned(payload_data, offset)
        offset += tb
        table_info['initial'] = initial_size
        print(f"  │  │  ├─ Initial size: {initial_size} elements")

        # 如果标志指示有最大值，读取最大值
        if has_max:
            if offset >= len(payload_data):
                print(f"  │  │  └─ Error: Insufficient data for maximum size")
                break

            maximum_size, tb = read_leb128_unsigned(payload_data, offset)
            offset += tb
            table_info['maximum'] = maximum_size
            print(f"  │  │  ├─ Maximum size: {maximum_size} elements")

            # 验证最大值 >= 初始值
            if maximum_size < initial_size:
                print(f"  │  │  │  Warning: Maximum size ({maximum_size}) < Initial size ({initial_size})")
        else:
            print(f"  │  │  ├─ Maximum size: unlimited")

        # 第 909-911 行：如果类型不可默认初始化，读取初始值表达式
        # if (!table_type.is_defaultable()) {
        #   table->initial_value = consume_init_expr(module_.get(), table_type);
        # }
        # 注意：funcref 和 externref 都是可默认初始化的（默认为 null）
        # 所以这部分在大多数情况下不会执行

        print(f"  │  │  └─ Element type: {type_name} (可以存储{type_name}类型的引用)")

        tables.append(table_info)

    print(f"  │  │")
    print(f"  │  └─ Total tables: {len(tables)}")
    if len(tables) > 0:
        print(f"  │     Note: 表内容由 Element Section (节 9) 初始化")

    return tables


def decode_global_section(payload_data):
    """
    解析 Global Section (节 6)
    对应 V8: module-decoder.cc 第 929-944 行的 DecodeGlobalSection()

    Global Section 定义了模块的全局变量

    格式：
      global_section ::= global_count:u32 global*
      global ::= global_type init_expr
      global_type ::= value_type mutability
      mutability ::= 0x00 (immutable) | 0x01 (mutable)
      init_expr ::= <instruction>* 0x0B (end)

    常见的初始化指令：
      i32.const <value>  0x41 <i32>
      i64.const <value>  0x42 <i64>
      f32.const <value>  0x43 <f32>
      f64.const <value>  0x44 <f64>
      global.get <index> 0x23 <index>
      ref.null           0xD0
      ref.func <index>   0xD2 <index>

    :param payload_data: Global Section 的 payload 数据
    :return: 全局变量定义列表
    """
    offset = 0
    globals_list = []

    print(f"  │")
    print(f"  │  ┌─ [Global Section Parsing]")
    print(f"  │  │")

    # 第 930 行：读取全局变量数量
    # uint32_t globals_count = consume_count("globals count", kV8MaxWasmGlobals);
    if offset >= len(payload_data):
        print(f"  │  └─ Error: Insufficient data for globals count")
        return globals_list

    globals_count, bytes_read = read_leb128_unsigned(payload_data, offset)
    offset += bytes_read
    print(f"  │  ├─ Globals count: {globals_count}")
    print(f"  │  │")

    # 第 935-942 行：遍历每个全局变量定义
    for i in range(globals_count):
        if i > 0:
            print(f"  │  │")

        print(f"  │  ├─ [Global #{i}]")

        global_info = {
            'index': i,
            'type': 0,
            'type_name': '',
            'mutability': False,
            'init_expr': []
        }

        # 第 937 行：读取值类型
        # ValueType type = consume_value_type();
        if offset >= len(payload_data):
            print(f"  │  │  └─ Error: Insufficient data for global type")
            break

        value_type = payload_data[offset]
        offset += 1
        global_info['type'] = value_type

        # 解析值类型
        type_name = VALUE_TYPE_NAMES.get(value_type, f"Unknown(0x{value_type:02x})")
        global_info['type_name'] = type_name
        print(f"  │  │  ├─ Value type: 0x{value_type:02x} ({type_name})")

        # 第 938 行：读取可变性标志
        # bool mutability = consume_mutability();
        if offset >= len(payload_data):
            print(f"  │  │  └─ Error: Insufficient data for mutability")
            break

        mutability_byte = payload_data[offset]
        offset += 1

        if mutability_byte > 1:
            print(f"  │  │  │  Warning: Invalid mutability value 0x{mutability_byte:02x}")

        is_mutable = (mutability_byte != 0)
        global_info['mutability'] = is_mutable
        mutability_str = "mutable (var)" if is_mutable else "immutable (const)"
        print(f"  │  │  ├─ Mutability: 0x{mutability_byte:02x} ({mutability_str})")

        # 第 940 行：读取初始化表达式
        # ConstantExpression init = consume_init_expr(module_.get(), type);
        print(f"  │  │  ├─ Init expression:")

        # 解析初始化表达式（简化版本）
        # 初始化表达式是一系列指令，以 0x0B (end) 结束
        init_expr_bytes = []
        init_expr_str = []

        while offset < len(payload_data):
            opcode = payload_data[offset]
            init_expr_bytes.append(opcode)
            offset += 1

            # 根据操作码解析
            if opcode == 0x0B:  # end
                init_expr_str.append("end")
                break
            elif opcode == 0x41:  # i32.const
                if offset >= len(payload_data):
                    break
                value, tb = read_leb128_unsigned(payload_data, offset)
                offset += tb
                for b in payload_data[offset - tb:offset]:
                    init_expr_bytes.append(b)
                init_expr_str.append(f"i32.const {value}")
            elif opcode == 0x42:  # i64.const
                if offset >= len(payload_data):
                    break
                value, tb = read_leb128_unsigned(payload_data, offset)
                offset += tb
                for b in payload_data[offset - tb:offset]:
                    init_expr_bytes.append(b)
                init_expr_str.append(f"i64.const {value}")
            elif opcode == 0x43:  # f32.const
                if offset + 3 >= len(payload_data):
                    break
                # 读取 4 字节浮点数
                f32_bytes = payload_data[offset:offset + 4]
                init_expr_bytes.extend(f32_bytes)
                offset += 4
                init_expr_str.append(f"f32.const <4 bytes>")
            elif opcode == 0x44:  # f64.const
                if offset + 7 >= len(payload_data):
                    break
                # 读取 8 字节浮点数
                f64_bytes = payload_data[offset:offset + 8]
                init_expr_bytes.extend(f64_bytes)
                offset += 8
                init_expr_str.append(f"f64.const <8 bytes>")
            elif opcode == 0x23:  # global.get
                if offset >= len(payload_data):
                    break
                global_index, tb = read_leb128_unsigned(payload_data, offset)
                offset += tb
                for b in payload_data[offset - tb:offset]:
                    init_expr_bytes.append(b)
                init_expr_str.append(f"global.get {global_index}")
            elif opcode == 0xD0:  # ref.null
                if offset >= len(payload_data):
                    break
                heap_type = payload_data[offset]
                init_expr_bytes.append(heap_type)
                offset += 1
                type_str = VALUE_TYPE_NAMES.get(heap_type, f"0x{heap_type:02x}")
                init_expr_str.append(f"ref.null {type_str}")
            elif opcode == 0xD2:  # ref.func
                if offset >= len(payload_data):
                    break
                func_index, tb = read_leb128_unsigned(payload_data, offset)
                offset += tb
                for b in payload_data[offset - tb:offset]:
                    init_expr_bytes.append(b)
                init_expr_str.append(f"ref.func {func_index}")
            else:
                init_expr_str.append(f"opcode 0x{opcode:02x}")

        global_info['init_expr'] = init_expr_bytes

        # 显示初始化表达式
        print(f"  │  │  │  └─ Instructions: {' → '.join(init_expr_str)}")
        print(f"  │  │  │     Bytes: {bytes(init_expr_bytes).hex()}")

        # 显示全局变量摘要
        print(f"  │  │  └─ Summary: {mutability_str} {type_name} = {init_expr_str[0] if init_expr_str else '(empty)'}")

        globals_list.append(global_info)

    print(f"  │  │")
    print(f"  │  └─ Total globals: {len(globals_list)}")

    return globals_list


def decode_start_section(payload_data):
    """
    解析 Start Section (节 8)
    对应 V8: module-decoder.cc 第 1049-1058 行的 DecodeStartSection()

    Start Section 指定了模块实例化后自动执行的启动函数

    格式：
      start_section ::= function_index:u32

    限制：
      - 启动函数必须没有参数
      - 启动函数必须没有返回值
      - 启动函数签名必须是 () -> ()

    :param payload_data: Start Section 的 payload 数据
    :return: 启动函数索引
    """
    offset = 0
    start_func_index = None

    print(f"  │")
    print(f"  │  ┌─ [Start Section Parsing]")
    print(f"  │  │")

    # 第 1052-1053 行：读取启动函数索引
    # module_->start_function_index = consume_func_index(...);
    if offset >= len(payload_data):
        print(f"  │  └─ Error: Insufficient data for start function index")
        return start_func_index

    start_func_index, bytes_read = read_leb128_unsigned(payload_data, offset)
    offset += bytes_read

    print(f"  │  ├─ Start function index: {start_func_index}")
    print(f"  │  │")
    print(f"  │  ├─ Note: 此函数在模块实例化后自动执行")
    print(f"  │  ├─ Requirement: 启动函数签名必须是 () -> ()")
    print(f"  │  │              即：无参数，无返回值")
    print(f"  │  │")

    # 第 1054-1057 行：验证函数签名
    # if (func->sig->parameter_count() > 0 || func->sig->return_count() > 0) {
    #   error("invalid start function: non-zero parameter or return count");
    # }
    # 注意：实际验证需要查找 Type Section 中的函数签名
    # 这里我们只是提示，实际验证在运行时由 V8 完成

    print(f"  │  └─ Start function will be: Function #{start_func_index}")
    print(f"  │     (Will be auto-executed after module instantiation)")

    return start_func_index


def decode_element_section(payload_data):
    """
    解析 Element Section (节 9) - 简化版本
    对应 V8: module-decoder.cc 第 1060-1083 行的 DecodeElementSection()

    Element Section 初始化表的内容（将函数引用放入表中）

    格式（简化，WASM 1.0）：
      element_section ::= elem_count:u32 elem*
      elem ::= table_index:u32 offset:expr func_indices:vec(u32)

    注意：Element Section 的格式在不同版本有所不同，这里实现基础版本

    :param payload_data: Element Section 的 payload 数据
    :return: 元素段列表
    """
    offset = 0
    elem_segments = []

    print(f"  │")
    print(f"  │  ┌─ [Element Section Parsing]")
    print(f"  │  │")
    print(f"  │  │  Note: Element Section 用于初始化表的内容")
    print(f"  │  │")

    # 第 1061-1062 行：读取元素段数量
    # uint32_t element_count = consume_count("element count", ...);
    if offset >= len(payload_data):
        print(f"  │  └─ Error: Insufficient data for element count")
        return elem_segments

    elem_count, bytes_read = read_leb128_unsigned(payload_data, offset)
    offset += bytes_read
    print(f"  │  ├─ Element segment count: {elem_count}")
    print(f"  │  │")

    # 第 1064-1082 行：遍历每个元素段
    for i in range(elem_count):
        if i > 0:
            print(f"  │  │")

        print(f"  │  ├─ [Element Segment #{i}]")

        elem_info = {
            'index': i,
            'flags': 0,
            'table_index': 0,
            'offset_expr': [],
            'elements': []
        }

        # 读取标志字节（简化版本，假设为 0x00 = active segment with table 0）
        if offset >= len(payload_data):
            print(f"  │  │  └─ Error: Insufficient data for flags")
            break

        flags = payload_data[offset]
        offset += 1
        elem_info['flags'] = flags

        print(f"  │  │  ├─ Flags: 0x{flags:02x}")

        # 根据标志解析
        if flags == 0x00:
            # Active segment with table index 0
            print(f"  │  │  ├─ Type: Active (table 0)")
            elem_info['table_index'] = 0

            # 读取偏移表达式（通常是 i32.const + end）
            print(f"  │  │  ├─ Offset expression:")
            offset_expr = []
            while offset < len(payload_data):
                opcode = payload_data[offset]
                offset_expr.append(opcode)
                offset += 1

                if opcode == 0x0B:  # end
                    print(f"  │  │  │  └─ end")
                    break
                elif opcode == 0x41:  # i32.const
                    value, tb = read_leb128_unsigned(payload_data, offset)
                    offset += tb
                    for b in payload_data[offset - tb:offset]:
                        offset_expr.append(b)
                    print(f"  │  │  │  ├─ i32.const {value}")
                elif opcode == 0x23:  # global.get
                    global_idx, tb = read_leb128_unsigned(payload_data, offset)
                    offset += tb
                    for b in payload_data[offset - tb:offset]:
                        offset_expr.append(b)
                    print(f"  │  │  │  ├─ global.get {global_idx}")

            elem_info['offset_expr'] = offset_expr

        elif flags == 0x01:
            # Passive segment
            print(f"  │  │  ├─ Type: Passive")
            elem_info['table_index'] = None

        elif flags == 0x02:
            # Active segment with table index
            print(f"  │  │  ├─ Type: Active (explicit table)")
            table_idx, tb = read_leb128_unsigned(payload_data, offset)
            offset += tb
            elem_info['table_index'] = table_idx
            print(f"  │  │  ├─ Table index: {table_idx}")

            # 读取偏移表达式
            print(f"  │  │  ├─ Offset expression:")
            offset_expr = []
            while offset < len(payload_data):
                opcode = payload_data[offset]
                offset_expr.append(opcode)
                offset += 1

                if opcode == 0x0B:  # end
                    print(f"  │  │  │  └─ end")
                    break
                elif opcode == 0x41:  # i32.const
                    value, tb = read_leb128_unsigned(payload_data, offset)
                    offset += tb
                    for b in payload_data[offset - tb:offset]:
                        offset_expr.append(b)
                    print(f"  │  │  │  ├─ i32.const {value}")

            elem_info['offset_expr'] = offset_expr

        # 第 1069-1070 行：读取元素数量
        # uint32_t num_elem = consume_count("number of elements", ...);
        if offset >= len(payload_data):
            print(f"  │  │  └─ Error: Insufficient data for element count")
            break

        num_elements, tb = read_leb128_unsigned(payload_data, offset)
        offset += tb
        print(f"  │  │  ├─ Number of elements: {num_elements}")

        # 第 1072-1080 行：读取函数索引列表
        elements = []
        print(f"  │  │  ├─ Function indices:")

        for j in range(num_elements):
            if offset >= len(payload_data):
                break

            func_idx, tb = read_leb128_unsigned(payload_data, offset)
            offset += tb
            elements.append(func_idx)

            # 只显示前5个和最后2个
            if j < 5 or j >= num_elements - 2:
                print(f"  │  │  │  ├─ [{j}] Function #{func_idx}")
            elif j == 5:
                print(f"  │  │  │  ├─ ... ({num_elements - 7} more functions) ...")

        elem_info['elements'] = elements

        print(f"  │  │  └─ Summary: {len(elements)} function references")

        elem_segments.append(elem_info)

    print(f"  │  │")
    print(f"  │  └─ Total element segments: {len(elem_segments)}")
    if len(elem_segments) > 0:
        print(f"  │     Note: 这些段将函数引用初始化到表中")

    return elem_segments


def decode_data_section(payload_data):
    """
    解析 Data Section (节 11)
    对应 V8: module-decoder.cc 的 DecodeDataSection()

    Data Section 初始化线性内存的内容

    格式（简化，WASM 1.0）：
      data_section ::= data_count:u32 data*
      data ::= memory_index:u32 offset:expr bytes:vec(byte)

    :param payload_data: Data Section 的 payload 数据
    :return: 数据段列表
    """
    offset = 0
    data_segments = []

    print(f"  │")
    print(f"  │  ┌─ [Data Section Parsing]")
    print(f"  │  │")
    print(f"  │  │  Note: Data Section 用于初始化线性内存的内容")
    print(f"  │  │")

    # 读取数据段数量
    if offset >= len(payload_data):
        print(f"  │  └─ Error: Insufficient data for data count")
        return data_segments

    data_count, bytes_read = read_leb128_unsigned(payload_data, offset)
    offset += bytes_read
    print(f"  │  ├─ Data segment count: {data_count}")
    print(f"  │  │")

    # 遍历每个数据段
    for i in range(data_count):
        if i > 0:
            print(f"  │  │")

        print(f"  │  ├─ [Data Segment #{i}]")

        data_info = {
            'index': i,
            'flags': 0,
            'memory_index': 0,
            'offset_expr': [],
            'data': b''
        }

        # 读取标志字节
        if offset >= len(payload_data):
            print(f"  │  │  └─ Error: Insufficient data for flags")
            break

        flags = payload_data[offset]
        offset += 1
        data_info['flags'] = flags

        print(f"  │  │  ├─ Flags: 0x{flags:02x}")

        # 根据标志解析
        if flags == 0x00:
            # Active segment with memory index 0
            print(f"  │  │  ├─ Type: Active (memory 0)")
            data_info['memory_index'] = 0

            # 读取偏移表达式
            print(f"  │  │  ├─ Offset expression:")
            offset_expr = []
            while offset < len(payload_data):
                opcode = payload_data[offset]
                offset_expr.append(opcode)
                offset += 1

                if opcode == 0x0B:  # end
                    print(f"  │  │  │  └─ end")
                    break
                elif opcode == 0x41:  # i32.const
                    value, tb = read_leb128_unsigned(payload_data, offset)
                    offset += tb
                    for b in payload_data[offset - tb:offset]:
                        offset_expr.append(b)
                    print(f"  │  │  │  ├─ i32.const {value} (offset in memory)")
                elif opcode == 0x23:  # global.get
                    global_idx, tb = read_leb128_unsigned(payload_data, offset)
                    offset += tb
                    for b in payload_data[offset - tb:offset]:
                        offset_expr.append(b)
                    print(f"  │  │  │  ├─ global.get {global_idx}")

            data_info['offset_expr'] = offset_expr

        elif flags == 0x01:
            # Passive segment
            print(f"  │  │  ├─ Type: Passive")
            data_info['memory_index'] = None

        elif flags == 0x02:
            # Active segment with memory index
            print(f"  │  │  ├─ Type: Active (explicit memory)")
            mem_idx, tb = read_leb128_unsigned(payload_data, offset)
            offset += tb
            data_info['memory_index'] = mem_idx
            print(f"  │  │  ├─ Memory index: {mem_idx}")

            # 读取偏移表达式
            print(f"  │  │  ├─ Offset expression:")
            offset_expr = []
            while offset < len(payload_data):
                opcode = payload_data[offset]
                offset_expr.append(opcode)
                offset += 1

                if opcode == 0x0B:  # end
                    print(f"  │  │  │  └─ end")
                    break
                elif opcode == 0x41:  # i32.const
                    value, tb = read_leb128_unsigned(payload_data, offset)
                    offset += tb
                    for b in payload_data[offset - tb:offset]:
                        offset_expr.append(b)
                    print(f"  │  │  │  ├─ i32.const {value}")

            data_info['offset_expr'] = offset_expr

        # 读取数据长度
        if offset >= len(payload_data):
            print(f"  │  │  └─ Error: Insufficient data for data size")
            break

        data_size, tb = read_leb128_unsigned(payload_data, offset)
        offset += tb
        print(f"  │  │  ├─ Data size: {data_size} bytes")

        # 读取数据
        if offset + data_size > len(payload_data):
            print(f"  │  │  └─ Error: Insufficient data")
            break

        data_bytes = payload_data[offset:offset + data_size]
        offset += data_size
        data_info['data'] = data_bytes

        # 显示数据预览
        preview_len = min(32, data_size)
        preview_hex = data_bytes[:preview_len].hex()

        # 尝试解码为字符串
        try:
            preview_str = data_bytes[:preview_len].decode('utf-8', errors='ignore')
            # 替换不可打印字符
            preview_str = ''.join(c if c.isprintable() else '.' for c in preview_str)
        except:
            preview_str = ''

        print(f"  │  │  ├─ Data (hex): {preview_hex}")
        if preview_str:
            print(f"  │  │  ├─ Data (text): \"{preview_str}\"")
        if data_size > preview_len:
            print(f"  │  │  │  ... ({data_size - preview_len} more bytes)")

        print(f"  │  │  └─ Summary: {data_size} bytes of data")

        data_segments.append(data_info)

    print(f"  │  │")
    print(f"  │  └─ Total data segments: {len(data_segments)}")
    if len(data_segments) > 0:
        print(f"  │     Note: 这些段将数据初始化到线性内存中")

    return data_segments


def decode_data_count_section(payload_data):
    """
    解析 Data Count Section (节 12) - 数据段数量声明
    对应 V8: module-decoder.cc 第 1404-1407 行的 DecodeDataCountSection()

    Data Count Section 是 WASM 的一个优化特性，用于提前声明数据段的数量。
    这允许验证器在解析 Code Section 时就知道数据段的数量，而不需要等到 Data Section。

    格式：
      data_count_section ::= count:u32

    注意：
      - 这是一个可选的 Section（WASM 1.0 不需要，bulk memory 提案引入）
      - 如果存在，必须在 Code Section 之前，Data Section 之前
      - count 必须与 Data Section 中实际的数据段数量匹配
      - 用于支持 memory.init 和 data.drop 指令的验证

    :param payload_data: Data Count Section 的 payload 数据
    :return: 数据段数量
    """
    offset = 0

    print(f"  │")
    print(f"  │  ┌─ [Data Count Section Parsing]")
    print(f"  │  │")
    print(f"  │  │  Note: 提前声明数据段数量（用于优化验证）")
    print(f"  │  │")

    # 第 1405-1406 行：读取数据段数量
    # module_->num_declared_data_segments = consume_count("data segments count", kV8MaxWasmDataSegments);
    if offset >= len(payload_data):
        print(f"  │  └─ Error: Insufficient data for data count")
        return 0

    data_count, bytes_read = read_leb128_unsigned(payload_data, offset)
    offset += bytes_read

    print(f"  │  ├─ Declared data segments count: {data_count}")
    print(f"  │  │")
    print(f"  │  └─ Note: 此数量必须与 Data Section 中的实际数量匹配")

    return data_count


def decode_tag_section(payload_data):
    """
    解析 Tag Section (节 13) - 异常标签定义
    对应 V8: module-decoder.cc 第 1409-1418 行的 DecodeTagSection()

    Tag Section 定义了异常处理的标签（也称为事件或异常类型）。
    这是 WASM 异常处理提案的一部分。

    格式：
      tag_section ::= tag_count:u32 tag*
      tag ::= attribute:byte type_index:u32

    注意：
      - 这是实验性特性，需要 --experimental-wasm-eh 标志
      - attribute 当前被忽略（保留用于未来扩展）
      - type_index 指向 Type Section 中的函数签名（定义异常的参数类型）
      - 标签可以被导入、导出和使用（throw, catch）

    :param payload_data: Tag Section 的 payload 数据
    :return: 标签定义列表
    """
    offset = 0
    tags = []

    print(f"  │")
    print(f"  │  ┌─ [Tag Section Parsing]")
    print(f"  │  │")
    print(f"  │  │  Note: 异常处理标签（实验性特性）")
    print(f"  │  │")

    # 第 1410 行：读取标签数量
    # uint32_t tag_count = consume_count("tag count", kV8MaxWasmTags);
    if offset >= len(payload_data):
        print(f"  │  └─ Error: Insufficient data for tag count")
        return tags

    tag_count, bytes_read = read_leb128_unsigned(payload_data, offset)
    offset += bytes_read
    print(f"  │  ├─ Tag count: {tag_count}")
    print(f"  │  │")

    # 第 1411-1417 行：遍历每个标签
    for i in range(tag_count):
        if offset >= len(payload_data):
            print(f"  │  └─ Error: Insufficient data for tag {i}")
            break

        print(f"  │  ├─ [Tag #{i}]")

        tag_info = {
            'index': i,
            'attribute': 0,
            'type_index': 0
        }

        # 第 1414 行：读取异常属性
        # consume_exception_attribute(); // Attribute ignored for now.
        if offset >= len(payload_data):
            print(f"  │  │  └─ Error: Insufficient data for attribute")
            break

        attribute = payload_data[offset]
        offset += 1
        tag_info['attribute'] = attribute

        print(f"  │  │  ├─ Attribute: 0x{attribute:02x} (当前被忽略)")

        # 第 1415 行：读取类型索引
        # consume_tag_sig_index(module_.get(), &tag_sig);
        if offset >= len(payload_data):
            print(f"  │  │  └─ Error: Insufficient data for type index")
            break

        type_index, type_bytes = read_leb128_unsigned(payload_data, offset)
        offset += type_bytes
        tag_info['type_index'] = type_index

        print(f"  │  │  ├─ Type index: {type_index}")
        print(f"  │  │  │  (指向 Type Section 中的函数签名)")
        print(f"  │  │  └─ Note: 定义异常的参数类型")

        if i < tag_count - 1:
            print(f"  │  │")

        tags.append(tag_info)

    print(f"  │  │")
    print(f"  │  └─ Total tags: {len(tags)}")
    if len(tags) > 0:
        print(f"  │     Note: 用于 try-catch-throw 异常处理")
        print(f"  │     需要: --experimental-wasm-eh 标志")

    return tags


def decode_code_section(payload_data):
    """
    解析 Code Section (节 10) - 函数体字节码
    对应 V8: module-decoder.cc 第 1085-1105 行的 DecodeCodeSection()

    Code Section 包含所有内部函数的字节码实现

    格式：
      code_section ::= code_count:u32 code*
      code ::= size:u32 func_body
      func_body ::= local_decl* instructions
      local_decl ::= count:u32 type:valuetype
      instructions ::= instruction* 0x0B (end)

    注意：
      - Code Section 中的函数顺序必须与 Function Section 一致
      - 不包含导入的函数（它们没有代码）
      - 这里只解析结构，不完全解析字节码指令

    :param payload_data: Code Section 的 payload 数据
    :return: 函数代码列表
    """
    offset = 0
    function_codes = []

    print(f"  │")
    print(f"  │  ┌─ [Code Section Parsing]")
    print(f"  │  │")
    print(f"  │  │  Note: Code Section 包含函数的字节码实现")
    print(f"  │  │")

    # 第 1088 行：读取函数体数量
    # uint32_t functions_count = consume_u32v("functions count");
    if offset >= len(payload_data):
        print(f"  │  └─ Error: Insufficient data for functions count")
        return function_codes

    functions_count, bytes_read = read_leb128_unsigned(payload_data, offset)
    offset += bytes_read
    print(f"  │  ├─ Function bodies count: {functions_count}")
    print(f"  │  │")

    # 第 1089 行：验证函数数量
    # CheckFunctionsCount(functions_count, code_section_start);
    # 注意：这里应该与 Function Section 中声明的数量一致
    # 我们只是解析，不做严格验证

    # 第 1090-1102 行：遍历每个函数体
    for i in range(functions_count):
        if offset >= len(payload_data):
            print(f"  │  └─ Error: Insufficient data for function body")
            break

        if i > 0 and i < 3:  # 只在前几个函数之间显示分隔
            print(f"  │  │")

        # 只详细显示前3个和最后1个函数
        show_details = (i < 3) or (i >= functions_count - 1)

        # 计算全局函数索引
        global_func_index = module_imported_func_count + i

        # 查找函数名
        func_name = module_function_names.get(global_func_index, "")
        func_name_str = f" \"{func_name}\"" if func_name else ""

        if show_details:
            print(f"  │  ├─ [Function Body #{i}] (全局索引 #{global_func_index}){func_name_str}")
        elif i == 3:
            print(f"  │  ├─ ... ({functions_count - 4} more function bodies) ...")

        function_code = {
            'index': i,
            'size': 0,
            'locals': [],
            'code_bytes': b''
        }

        # 第 1092 行：读取函数体大小
        # uint32_t size = consume_u32v("body size");
        body_start = offset
        body_size, tb = read_leb128_unsigned(payload_data, offset)
        offset += tb
        function_code['size'] = body_size

        if show_details:
            print(f"  │  │  ├─ Body size: {body_size} bytes")

        # 第 1093-1097 行：检查大小限制
        # if (size > kV8MaxWasmFunctionSize)
        max_function_size = 128 * 1024  # 128 KB (V8的限制)
        if body_size > max_function_size:
            if show_details:
                print(f"  │  │  │  Warning: Body size exceeds maximum ({max_function_size} bytes)")

        # 第 1098-1099 行：读取函数体数据
        # consume_bytes(size, "function body");
        if offset + body_size > len(payload_data):
            if show_details:
                print(f"  │  │  └─ Error: Insufficient data for function body")
            break

        body_data = payload_data[offset:offset + body_size]
        function_code['code_bytes'] = body_data

        # 解析函数体内部结构（局部变量声明）
        body_offset = 0

        # 读取局部变量声明
        if body_offset < len(body_data):
            local_decl_count, lb = read_leb128_unsigned(body_data, body_offset)
            body_offset += lb

            if show_details:
                print(f"  │  │  ├─ Local declarations: {local_decl_count}")

            # 解析每个局部变量声明
            for j in range(local_decl_count):
                if body_offset >= len(body_data):
                    break

                # 读取局部变量数量
                local_count, lc_bytes = read_leb128_unsigned(body_data, body_offset)
                body_offset += lc_bytes

                # 读取局部变量类型
                if body_offset >= len(body_data):
                    break
                local_type = body_data[body_offset]
                body_offset += 1

                type_name = VALUE_TYPE_NAMES.get(local_type, f"0x{local_type:02x}")

                function_code['locals'].append({
                    'count': local_count,
                    'type': local_type,
                    'type_name': type_name
                })

                if show_details:
                    print(f"  │  │  │  ├─ Local group [{j}]: {local_count} × {type_name}")

        # 剩余的是指令字节码
        instruction_bytes = body_data[body_offset:]
        instructions_size = len(instruction_bytes)

        if show_details:
            print(f"  │  │  ├─ Instructions size: {instructions_size} bytes")

            # 显示字节码预览（前32字节）
            preview_len = min(32, instructions_size)
            if preview_len > 0:
                preview_hex = instruction_bytes[:preview_len].hex()
                print(f"  │  │  ├─ Bytecode (hex): {preview_hex}")
                if instructions_size > preview_len:
                    print(f"  │  │  │  ... ({instructions_size - preview_len} more bytes)")

            # 尝试识别指令（使用完整的操作码字典，带嵌套层次显示）
            if instructions_size > 0:
                print(f"  │  │  ├─ Instructions (with nesting):")
                print(f"  │  │  │  注意：[depth] 表示控制流嵌套深度，不是栈深度")
                print(f"  │  │  │")
                instr_offset = 0
                instr_count = 0
                max_show = 130  # 最多显示30条指令
                depth = 0  # 控制流嵌套深度（block/loop/if 的层数）
                block_counter = 0  # 块计数器

                # 控制流指令：会增加深度
                block_start_opcodes = [0x02, 0x03, 0x04]  # block, loop, if
                # 控制流结束：会减少深度
                block_end_opcodes = [0x0B]  # end

                while instr_offset < min(instructions_size, 200) and instr_count < max_show:
                    if instr_offset >= len(instruction_bytes):
                        break

                    # 记录当前偏移
                    current_offset = instr_offset
                    opcode = instruction_bytes[instr_offset]
                    instr_offset += 1

                    # 使用 WASM_OPCODES 字典识别操作码
                    opcode_name = get_opcode_name(opcode)

                    # 如果是 end，先减少深度再显示
                    if opcode in block_end_opcodes:
                        depth = max(-1, depth - 1)

                    # 某些指令有立即数操作数，尝试读取
                    operand_str = ""
                    block_type_str = ""

                    # 控制流指令需要读取块类型
                    if opcode in block_start_opcodes:  # block, loop, if
                        if instr_offset < len(instruction_bytes):
                            try:
                                block_type = instruction_bytes[instr_offset]
                                instr_offset += 1

                                # 块类型可能是 value type 或 type index
                                if block_type == 0x40:
                                    block_type_str = " (void)"
                                elif block_type in VALUE_TYPE_NAMES:
                                    block_type_str = f" (result {VALUE_TYPE_NAMES[block_type]})"
                                else:
                                    block_type_str = f" (type {block_type})"

                                # 为块分配标签
                                operand_str = f" $B{block_counter}{block_type_str}"
                                block_counter += 1
                            except:
                                pass
                    elif opcode in [0x20, 0x21, 0x22]:  # local.get, local.set, local.tee
                        if instr_offset < len(instruction_bytes):
                            try:
                                idx, idx_bytes = read_leb128_unsigned(instruction_bytes, instr_offset)
                                instr_offset += idx_bytes
                                operand_str = f" ${idx}"
                            except:
                                pass
                    elif opcode in [0x23, 0x24]:  # global.get, global.set
                        if instr_offset < len(instruction_bytes):
                            try:
                                idx, idx_bytes = read_leb128_unsigned(instruction_bytes, instr_offset)
                                instr_offset += idx_bytes
                                operand_str = f" ${idx}"
                            except:
                                pass
                    elif opcode == 0x10:  # call
                        if instr_offset < len(instruction_bytes):
                            try:
                                func_idx, idx_bytes = read_leb128_unsigned(instruction_bytes, instr_offset)
                                instr_offset += idx_bytes
                                operand_str = f" ${func_idx}"
                            except:
                                pass
                    elif opcode in [0x0C, 0x0D]:  # br, br_if
                        if instr_offset < len(instruction_bytes):
                            try:
                                label_idx, idx_bytes = read_leb128_unsigned(instruction_bytes, instr_offset)
                                instr_offset += idx_bytes
                                operand_str = f" ${label_idx}"
                            except:
                                pass
                    elif opcode == 0x0E:  # br_table
                        if instr_offset < len(instruction_bytes):
                            try:
                                # 读取目标数量
                                target_count, count_bytes = read_leb128_unsigned(instruction_bytes, instr_offset)
                                instr_offset += count_bytes

                                # 读取所有目标索引
                                targets = []
                                for _ in range(target_count):
                                    if instr_offset >= len(instruction_bytes):
                                        break
                                    target_idx, idx_bytes = read_leb128_unsigned(instruction_bytes, instr_offset)
                                    instr_offset += idx_bytes
                                    targets.append(target_idx)

                                # 读取默认目标
                                default_target = 0
                                if instr_offset < len(instruction_bytes):
                                    default_target, def_bytes = read_leb128_unsigned(instruction_bytes, instr_offset)
                                    instr_offset += def_bytes

                                # 格式化输出
                                targets_str = ",".join(str(t) for t in targets)
                                operand_str = f" targets=[{targets_str}],default={default_target}"
                            except:
                                pass
                    elif opcode == 0x41:  # i32.const
                        if instr_offset < len(instruction_bytes):
                            try:
                                val, val_bytes = read_leb128_unsigned(instruction_bytes, instr_offset)
                                instr_offset += val_bytes
                                operand_str = f" {val}"
                            except:
                                pass
                    elif opcode == 0x42:  # i64.const
                        if instr_offset < len(instruction_bytes):
                            try:
                                val, val_bytes = read_leb128_unsigned(instruction_bytes, instr_offset)
                                instr_offset += val_bytes
                                operand_str = f" {val}"
                            except:
                                pass
                    elif opcode == 0x43:  # f32.const
                        if instr_offset + 4 <= len(instruction_bytes):
                            try:
                                # f32 是 4 字节的 IEEE 754 单精度浮点数
                                import struct
                                f32_bytes = instruction_bytes[instr_offset:instr_offset + 4]
                                instr_offset += 4
                                # 以十六进制显示（像 IDA Pro）
                                f32_hex = f32_bytes.hex().upper()
                                # 也可以解析为浮点数
                                f32_val = struct.unpack('<f', f32_bytes)[0]
                                operand_str = f" {f32_hex}h ({f32_val})"
                            except:
                                pass
                    elif opcode == 0x44:  # f64.const
                        if instr_offset + 8 <= len(instruction_bytes):
                            try:
                                # f64 是 8 字节的 IEEE 754 双精度浮点数
                                import struct
                                f64_bytes = instruction_bytes[instr_offset:instr_offset + 8]
                                instr_offset += 8
                                # 以十六进制显示（像 IDA Pro）
                                f64_hex = f64_bytes.hex().upper()
                                # 也可以解析为浮点数
                                f64_val = struct.unpack('<d', f64_bytes)[0]
                                operand_str = f" {f64_hex}h ({f64_val})"
                            except:
                                pass
                    # 内存指令：需要读取 alignment 和 offset 两个立即数
                    elif opcode in [0x28, 0x29, 0x2A, 0x2B, 0x2C, 0x2D, 0x2E, 0x2F,  # load 指令
                                    0x30, 0x31, 0x32, 0x33, 0x34, 0x35,  # load 指令
                                    0x36, 0x37, 0x38, 0x39, 0x3A, 0x3B, 0x3C, 0x3D, 0x3E]:  # store 指令
                        # 格式：alignment:u32 offset:u32
                        if instr_offset < len(instruction_bytes):
                            try:
                                # 读取 alignment hint (2^N)
                                align, align_bytes = read_leb128_unsigned(instruction_bytes, instr_offset)
                                instr_offset += align_bytes

                                # 读取 offset
                                mem_offset, offset_bytes = read_leb128_unsigned(instruction_bytes, instr_offset)
                                instr_offset += offset_bytes

                                # 格式化：align=N, offset=M 或使用 IDA 风格
                                operand_str = f" align={align} offset={mem_offset:#x}"
                            except:
                                pass

                    # 格式化输出：偏移 深度 [栈效果] 缩进+指令
                    indent = "  " * depth
                    stack_effect = f"[{depth}]"

                    print(f"  │  │  │  {current_offset:4d} {stack_effect:5s} {indent}{opcode_name}{operand_str}")

                    # 如果是块开始指令，增加深度
                    if opcode in block_start_opcodes:
                        depth += 1

                    instr_count += 1

                    # 如果是最外层的 end，停止解析
                    if opcode == 0x0B and depth == -1:
                        break

                if instructions_size > 200 or instr_count >= max_show:
                    print(f"  │  │  │  ... (more instructions not shown)")

            print(f"  │  │  └─ Summary: {body_size} bytes total")

        # 移动到下一个函数体
        offset += body_size

        # 第 1101 行：DecodeFunctionBody - 在V8中会详细验证字节码
        # 我们这里只是读取和显示结构

        function_codes.append(function_code)

    print(f"  │  │")
    print(f"  │  └─ Total function bodies: {len(function_codes)}")
    if len(function_codes) > 0:
        total_code_size = sum(fc['size'] for fc in function_codes)
        print(f"  │     Total code size: {total_code_size} bytes")
        print(f"  │     Note: 每个函数体对应 Function Section 中声明的函数")

    return function_codes


def decode_section(section_id, payload_data, offset, payload_length):
    """
    解析具体的节内容（空函数框架）
    对应 V8: module-decoder.cc 中的 DecodeSection

    :param section_id: 节的 ID
    :param payload_data: 节的 payload 数据
    :param offset: 该节 payload 在整个模块中的绝对偏移
    :param payload_length: payload 的长度
    """
    section_name = SECTION_NAMES.get(section_id, f"Unknown({section_id})")

    print(f"\n  ┌─ [DecodeSection] {section_name} Section")
    print(f"  │  Payload offset: {offset}")
    print(f"  │  Payload length: {payload_length} bytes")
    print(f"  │  Payload data (first 16 bytes): {payload_data[:16].hex()}")

    # 根据 section_id 分发到不同的解析函数
    # 对应 V8: module-decoder.cc 第 464-509 行的 switch 语句
    if section_id == 1:
        # Type Section - 函数签名定义
        types = decode_type_section(payload_data)
    elif section_id == 2:
        # Import Section - 导入声明
        imports = decode_import_section(payload_data)
    elif section_id == 3:
        # Function Section - 函数声明
        functions = decode_function_section(payload_data)
    elif section_id == 4:
        # Table Section - 间接函数表定义
        tables = decode_table_section(payload_data)
    elif section_id == 5:
        # Memory Section - 内存定义
        memories = decode_memory_section(payload_data)
    elif section_id == 6:
        # Global Section - 全局变量定义
        globals_list = decode_global_section(payload_data)
        print(globals_list)
    elif section_id == 7:
        # Export Section - 导出声明
        exports = decode_export_section(payload_data)
    elif section_id == 8:
        # Start Section - 启动函数
        start_func = decode_start_section(payload_data)
    elif section_id == 9:
        # Element Section - 表初始化
        elem_segments = decode_element_section(payload_data)
    elif section_id == 10:
        # Code Section - 函数体字节码
        function_codes = decode_code_section(payload_data)
    elif section_id == 11:
        # Data Section - 内存初始化
        data_segments = decode_data_section(payload_data)
    elif section_id == 12:
        # Data Count Section - 数据段数量声明
        data_count = decode_data_count_section(payload_data)
    elif section_id == 13:
        # Tag Section - 异常标签定义（实验性）
        tags = decode_tag_section(payload_data)
    else:
        print(f"  │  → (暂未实现具体解析)")

    print(f"  └─ End of {section_name} Section\n")


def decode_module(wasm_data):
    """
    完整的模块解析流程
    对应 V8: module-decoder.cc 中的 ModuleDecoderImpl::DecodeModule

    :param wasm_data: WASM 模块的字节数据
    """
    print(f"\n{'#' * 60}")
    print(f"# 开始解析 WASM 模块 (总大小: {len(wasm_data)} bytes)")
    print(f"{'#' * 60}")

    # 全局数据收集：用于在 Code Section 显示函数名
    global module_function_names  # 函数索引 -> 名字
    global module_imported_func_count  # 导入的函数数量
    module_function_names = {}
    module_imported_func_count = 0

    # 步骤 1: 解析模块头 (对应 module-decoder.cc 第 1470 行)
    offset = 0
    decode_module_header(wasm_data, offset)

    # 步骤 2: 跳过模块头，从第 8 字节开始 (对应 module-decoder.cc 第 1475 行)
    offset += 8  # Size of the module header
    print(f"\n→ Offset after header: {offset}")

    # 步骤 3: 创建节迭代器 (对应 module-decoder.cc 第 1476-1478 行)
    section_iter = SectionIterator(wasm_data, offset)

    print(f"\n{'=' * 60}")
    print(f"开始遍历各个节 (Section)")
    print(f"{'=' * 60}")

    section_count = 0

    # 步骤 4: 循环遍历所有节 (对应 module-decoder.cc 第 1480-1491 行)
    while section_iter.read_next_section():
        section_count += 1
        section_name = SECTION_NAMES.get(section_iter.section_id, f"Unknown({section_iter.section_id})")

        print(f"\n[Section #{section_count}] {section_name}")
        print(f"├─ section_start:  {section_iter.section_start}")
        print(f"├─ section_id:     {section_iter.section_id}")
        print(f"├─ section_length: {section_iter.section_length}")
        print(f"├─ payload_start:  {section_iter.payload_start}")
        print(f"├─ payload_length: {section_iter.payload_length}")
        print(f"└─ section_end:    {section_iter.section_end}")

        # 对应 module-decoder.cc 第 1482 行
        # offset += section_iter.payload_start() - section_iter.section_start()
        offset += section_iter.get_section_header_length()
        print(f"\n  [Offset Update #1] offset += {section_iter.get_section_header_length()} (节头长度)")
        print(f"  → offset = {offset} (指向 payload 开始)")

        # 获取 payload 数据
        payload_data = wasm_data[section_iter.payload_start:section_iter.section_end]

        # 对应 module-decoder.cc 第 1484-1485 行
        # DecodeSection(section_code, payload, offset, verify_functions)
        decode_section(section_iter.section_id, payload_data, offset, section_iter.payload_length)

        # 对应 module-decoder.cc 第 1488 行
        # offset += section_iter.payload_length()
        offset += section_iter.payload_length
        print(f"  [Offset Update #2] offset += {section_iter.payload_length} (payload 长度)")
        print(f"  → offset = {offset} (指向下一个节)")

        # 对应 module-decoder.cc 第 1490 行
        # section_iter.advance(true)
        section_iter.advance_to_next()

    print(f"\n{'=' * 60}")
    print(f"✓ 解析完成！共处理 {section_count} 个节")
    print(f"✓ 最终 offset: {offset}")
    print(f"{'=' * 60}\n")


# 主程序入口
if __name__ == "__main__":
    # 检查命令行参数
    if len(sys.argv) > 1:
        wasm_file = sys.argv[1]
    else:
        # 默认文件
        wasm_file = './base64_2.wasm'

    print(f"正在读取 WASM 文件: {wasm_file}")

    try:
        with open(wasm_file, "rb") as f:
            wasm_data = f.read()

        # 调用完整的解析流程
        decode_module(wasm_data)

    except FileNotFoundError:
        print(f"错误: 文件 '{wasm_file}' 不存在")
        print("用法: python jiex.py <wasm_file_path>")
    except ValueError as e:
        print(f"解析错误: {e}")
    except Exception as e:
        print(f"未预期的错误: {e}")
        import traceback

        traceback.print_exc()
