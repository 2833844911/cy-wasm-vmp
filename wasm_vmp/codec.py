from .consts import (
    WASM_MAGIC, WASM_VERSION, VALUE_TYPE_NAMES, WASM_OPCODES,
    IMPORT_EXPORT_KIND_NAMES, EXTERNAL_FUNCTION, EXTERNAL_TABLE,
    EXTERNAL_MEMORY, EXTERNAL_GLOBAL, EXTERNAL_TAG
)
from .utils import (
    read_leb128_unsigned, read_leb128_signed, write_leb128_unsigned,
    write_leb128_signed, read_utf8_string, get_opcode_name
)
import struct

class WasmCodec:
    def __init__(self):
        self.module_function_names = {}
        self.types = []
        self.functions = []
        self.imports = []
        self.imported_func_count = 0

    def decode_module_header(self, bytes_data, offset):
        if len(bytes_data) < 8: return
        magic_word = bytes_data[offset:offset + 4]
        if magic_word != WASM_MAGIC: raise ValueError("Invalid Magic")
        version = bytes_data[offset + 4:offset + 8]
        if version != WASM_VERSION: raise ValueError("Invalid Version")
        print(f"[OK] Magic & Version Valid")

    def read_next_section(self, wasm_data, offset):
        if offset >= len(wasm_data): return False, offset
        section_id = wasm_data[offset]
        offset += 1
        section_length, length_bytes = read_leb128_unsigned(wasm_data, offset)
        offset += length_bytes
        section_info = {
            'section_id': section_id,
            'data': wasm_data[offset:offset + section_length],
        }
        offset += section_length
        return section_info, offset

    def _pack_operand(self, val, length):
        return {'val': val, 'len': length}

    def _extract_operand(self, operand):
        if isinstance(operand, dict):
            return operand['val'], operand.get('len', 0)
        return operand, 0

    def decode_type_section(self, payload_data):
        types_count, bytes_read = read_leb128_unsigned(payload_data, 0)
        offset = bytes_read
        self.types = []

        for i in range(types_count):
            if offset >= len(payload_data): break
            
            type_code = payload_data[offset]
            offset += 1
            
            if type_code != 0x60: # WASM_FUNCTION_TYPE_CODE
                continue
                
            param_count, pb = read_leb128_unsigned(payload_data, offset)
            offset += pb
            
            params = []
            for _ in range(param_count):
                if offset >= len(payload_data): break
                param_type = payload_data[offset]
                offset += 1
                type_name = VALUE_TYPE_NAMES.get(param_type, f"0x{param_type:02x}")
                params.append(type_name)
                
            result_count, rb = read_leb128_unsigned(payload_data, offset)
            offset += rb
            
            results = []
            for _ in range(result_count):
                if offset >= len(payload_data): break
                result_type = payload_data[offset]
                offset += 1
                type_name = VALUE_TYPE_NAMES.get(result_type, f"0x{result_type:02x}")
                results.append(type_name)
                
            result_str = ', '.join(results) if results else 'void'
            signature = {
                'index': i,
                'params': params,
                'results': results,
                'signature_str': f"({', '.join(params)}) -> ({result_str})"
            }
            self.types.append(signature)
            
        return self.types

    def add_type(self, params, results):
        """
        Add a new function type signature.
        :param params: list of type strings, e.g. ['i32', 'i64']
        :param results: list of type strings, e.g. ['i32']
        :return: new type index
        """
        # Create reverse mapping for types
        TYPE_NAME_TO_ID = {v: k for k, v in VALUE_TYPE_NAMES.items()}
        
        # Validate types
        for p in params:
            if p not in TYPE_NAME_TO_ID:
                raise ValueError(f"Invalid param type: {p}")
        for r in results:
            if r not in TYPE_NAME_TO_ID:
                raise ValueError(f"Invalid result type: {r}")
                
        result_str = ', '.join(results) if results else 'void'
        signature = {
            'index': len(self.types),
            'params': params,
            'results': results,
            'signature_str': f"({', '.join(params)}) -> ({result_str})"
        }
        self.types.append(signature)
        return len(self.types) - 1

    def encode_type_section(self):
        """
        Encode self.types back to bytes (Section ID 1 payload).
        """
        TYPE_NAME_TO_ID = {v: k for k, v in VALUE_TYPE_NAMES.items()}
        buffer = bytearray()
        
        # Count
        buffer.extend(write_leb128_unsigned(len(self.types)))
        
        for sig in self.types:
            # Form: 0x60 | param_count | params... | result_count | results...
            buffer.append(0x60)
            
            # Params
            buffer.extend(write_leb128_unsigned(len(sig['params'])))
            for p_name in sig['params']:
                buffer.append(TYPE_NAME_TO_ID[p_name])
                
            # Results
            buffer.extend(write_leb128_unsigned(len(sig['results'])))
            for r_name in sig['results']:
                buffer.append(TYPE_NAME_TO_ID[r_name])
                
        return bytes(buffer)

    def decode_global_section(self, payload_data):
        count, bytes_read = read_leb128_unsigned(payload_data, 0)
        offset = bytes_read
        globals_list = []
        
        for i in range(count):
            if offset >= len(payload_data): break
            
            # Global Type
            value_type = payload_data[offset]
            offset += 1
            type_name = VALUE_TYPE_NAMES.get(value_type, f"0x{value_type:02x}")
            
            mutability = payload_data[offset]
            offset += 1
            
            # Init Expr
            init_expr_start = offset
            init_val = 0
            
            while offset < len(payload_data):
                opcode = payload_data[offset]
                offset += 1
                if opcode == 0x0B: # END
                    break
                
                # Simple parsing for common init ops (consts, global.get)
                if opcode in [0x41, 0x42, 0x23]: # i32.const, i64.const, global.get
                    val, b = read_leb128_unsigned(payload_data, offset) # Treat as unsigned for skipping
                    offset += b
                    init_val = val # Capture val if possible
                elif opcode == 0x43: # f32.const
                    val = struct.unpack('<f', payload_data[offset:offset+4])[0]
                    offset += 4
                    init_val = val
                elif opcode == 0x44: # f64.const
                    val = struct.unpack('<d', payload_data[offset:offset+8])[0]
                    offset += 8
                    init_val = val
                # Add more if needed, but for now we just need to skip to END
            
            init_raw = payload_data[init_expr_start:offset-1] # Exclude END opcode, we append it later or encode logic handles it.
            # Actually encode logic appends END. So we exclude it here.
            
            globals_list.append({
                'index': i,
                'type': value_type,
                'type_name': type_name,
                'mutability': mutability,
                'init_raw': init_raw,
                'init_val': init_val 
            })
            
        return globals_list

    def encode_global_section(self, globals_list):
        buffer = bytearray()
        buffer.extend(write_leb128_unsigned(len(globals_list)))
        
        for g in globals_list:
            buffer.append(g['type'])
            buffer.append(g['mutability'])
            
            # Simple init expr encoding
            # If we know the value, we can encode it.
            # Assuming 'init_val' is present for injected globals, or we use defaults.
            # For now, we only support i32.const init for injected globals.
            if 'init_val' in g and 'init_raw' not in g:
                val = g['init_val']
                if g['type'] == 0x7F: # i32
                     buffer.append(0x41)
                     buffer.extend(write_leb128_signed(val))
                elif g['type'] == 0x7E: # i64
                     buffer.append(0x42)
                     buffer.extend(write_leb128_signed(val))
                elif g['type'] == 0x7D: # f32
                     buffer.append(0x43)
                     buffer.extend(struct.pack('<f', float(val)))
                elif g['type'] == 0x7C: # f64
                     buffer.append(0x44)
                     buffer.extend(struct.pack('<d', float(val)))
                # Add others if needed
            elif 'init_raw' in g:
                 raw = g['init_raw']
                 # Defensive fix: Ensure we don't duplicate END opcode if init_raw captured it
                 while raw.endswith(b'\x0b'):
                     raw = raw[:-1]
                 buffer.extend(raw)
            else:
                 # Should not happen if decoded correctly
                 buffer.append(0x41)
                 buffer.append(0x00) # i32.const 0 default
                 
            buffer.append(0x0B) # END
            
        return bytes(buffer)


    def decode_function_section(self, payload_data):
        functions_count, bytes_read = read_leb128_unsigned(payload_data, 0)
        offset = bytes_read
        self.functions = []
        
        for i in range(functions_count):
            if offset >= len(payload_data): break
            type_index, tb = read_leb128_unsigned(payload_data, offset)
            offset += tb
            
            function_info = {
                'index': i,
                'type_index': type_index
            }
            self.functions.append(function_info)
            
        return self.functions

    def encode_function_section(self, functions):
        buffer = bytearray()
        buffer.extend(write_leb128_unsigned(len(functions)))
        
        for func in functions:
            buffer.extend(write_leb128_unsigned(func['type_index']))
            
        return bytes(buffer)

    def decode_code_section(self, section_data):
        payload_data = section_data['data']
        offset = 0
        function_codes = []

        if offset >= len(payload_data): return function_codes

        functions_count, bytes_read = read_leb128_unsigned(payload_data, offset)
        offset += bytes_read

        for i in range(functions_count):
            if offset >= len(payload_data): break

            global_func_index = self.imported_func_count + i
            func_name = self.module_function_names.get(global_func_index, "")
            
            # Get function signature if available
            signature = None
            type_index = -1
            if i < len(self.functions):
                type_index = self.functions[i]['type_index']
                if type_index < len(self.types):
                    signature = self.types[type_index]

            function_code = {
                'index': i, 
                'locals': [], 
                'code': [],
                'name': func_name,
                'type_index': type_index,
                'signature': signature
            }

            body_size, tb = read_leb128_unsigned(payload_data, offset)
            offset += tb
            body_end = offset + body_size
            body_data = payload_data[offset: body_end]
            offset = body_end

            # Locals
            b_offset = 0
            locals_start = b_offset
            local_decl_count, lb = read_leb128_unsigned(body_data, b_offset)
            b_offset += lb
            function_code['locals_count_len'] = lb

            for _ in range(local_decl_count):
                local_cnt, lc_b = read_leb128_unsigned(body_data, b_offset)
                b_offset += lc_b
                local_type = body_data[b_offset]
                b_offset += 1
                type_name = VALUE_TYPE_NAMES.get(local_type, f"0x{local_type:02x}")
                function_code['locals'].append({'count': local_cnt, 'type': local_type, 'len': lc_b, 'type_name': type_name})

            function_code['locals_raw'] = body_data[locals_start:b_offset]

            # Instructions
            instruction_bytes = body_data[b_offset:]
            instr_offset = 0
            block_start_opcodes = [0x02, 0x03, 0x04]

            while instr_offset < len(instruction_bytes):
                start_offset = instr_offset
                opcode = instruction_bytes[instr_offset]
                opcode_name = get_opcode_name(opcode)
                instr_offset += 1
                operand_int_list = []

                if opcode in block_start_opcodes:
                    block_type = instruction_bytes[instr_offset]
                    instr_offset += 1
                    operand_int_list = [block_type]

                elif opcode in [0x20, 0x21, 0x22, 0x23, 0x24, 0x10, 0x0C, 0x0D, 0x25, 0x26]:
                    idx, idx_bytes = read_leb128_unsigned(instruction_bytes, instr_offset)
                    instr_offset += idx_bytes
                    operand_int_list = [self._pack_operand(idx, idx_bytes)]

                elif opcode == 0x11:
                    type_idx, b1 = read_leb128_unsigned(instruction_bytes, instr_offset)
                    instr_offset += b1
                    table_idx, b2 = read_leb128_unsigned(instruction_bytes, instr_offset)
                    instr_offset += b2
                    operand_int_list = [self._pack_operand(type_idx, b1), self._pack_operand(table_idx, b2)]

                elif opcode == 0x0E:
                    target_cnt, b = read_leb128_unsigned(instruction_bytes, instr_offset)
                    instr_offset += b
                    operand_int_list.append(self._pack_operand(target_cnt, b))
                    for _ in range(target_cnt):
                        t, tb = read_leb128_unsigned(instruction_bytes, instr_offset)
                        instr_offset += tb
                        operand_int_list.append(self._pack_operand(t, tb))
                    def_idx, db = read_leb128_unsigned(instruction_bytes, instr_offset)
                    instr_offset += db
                    operand_int_list.append(self._pack_operand(def_idx, db))

                elif opcode in [0x3F, 0x40]:
                    m, b = read_leb128_unsigned(instruction_bytes, instr_offset)
                    instr_offset += b
                    operand_int_list = [self._pack_operand(m, b)]

                elif opcode == 0x41:
                    val, val_bytes = read_leb128_signed(instruction_bytes, instr_offset)
                    instr_offset += val_bytes
                    operand_int_list = [self._pack_operand(val, val_bytes)]
                elif opcode == 0x42:
                    val, val_bytes = read_leb128_signed(instruction_bytes, instr_offset)
                    instr_offset += val_bytes
                    operand_int_list = [self._pack_operand(val, val_bytes)]

                elif opcode in [0x43, 0x44]:
                    size = 4 if opcode == 0x43 else 8
                    raw = instruction_bytes[instr_offset:instr_offset + size]
                    instr_offset += size
                    if opcode == 0x43:
                        val = struct.unpack('<f', raw)[0]
                    else:
                        val = struct.unpack('<d', raw)[0]
                    operand_int_list = [self._pack_operand(val, size)]

                elif 0x28 <= opcode <= 0x3E:
                    align, b1 = read_leb128_unsigned(instruction_bytes, instr_offset)
                    instr_offset += b1
                    offset_mem, b2 = read_leb128_unsigned(instruction_bytes, instr_offset)
                    instr_offset += b2
                    operand_int_list = [self._pack_operand(align, b1), self._pack_operand(offset_mem, b2)]

                elif opcode == 0xFC:
                    sub_opcode, sub_b = read_leb128_unsigned(instruction_bytes, instr_offset)
                    instr_offset += sub_b
                    args = []
                    # Simplified bulk memory handling
                    if sub_opcode in [10, 8]: # copy / init
                         d, b1 = read_leb128_unsigned(instruction_bytes, instr_offset)
                         instr_offset += b1
                         s, b2 = read_leb128_unsigned(instruction_bytes, instr_offset)
                         instr_offset += b2
                         args = [self._pack_operand(d, b1), self._pack_operand(s, b2)]
                    elif sub_opcode in [11, 9]: # fill / drop
                         v, b1 = read_leb128_unsigned(instruction_bytes, instr_offset)
                         instr_offset += b1
                         args = [self._pack_operand(v, b1)]
                     
                    # Map sub-opcode to name
                    if sub_opcode == 10: opcode_name = 'memory.copy'
                    elif sub_opcode == 11: opcode_name = 'memory.fill'
                    elif sub_opcode == 8: opcode_name = 'memory.init'
                    elif sub_opcode == 9: opcode_name = 'data.drop'
                    elif sub_opcode == 12: opcode_name = 'table.init'
                    elif sub_opcode == 13: opcode_name = 'elem.drop'
                    elif sub_opcode == 14: opcode_name = 'table.copy'
                    operand_int_list = [self._pack_operand(sub_opcode, sub_b), args]

                end_offset = instr_offset
                raw_bytes = instruction_bytes[start_offset:end_offset]
                function_code['code'].append([opcode_name, opcode, operand_int_list, raw_bytes])

            function_codes.append(function_code)

        return function_codes

    def encode_code_section(self, function_codes):
        final_buffer = bytearray()
        final_buffer.extend(write_leb128_unsigned(len(function_codes)))
        block_start_opcodes = [0x02, 0x03, 0x04]

        for func in function_codes:
            body_buffer = bytearray()
            locals_buffer = bytearray()
            
            locals_count_len = func.get('locals_count_len', 0)
            locals_buffer.extend(write_leb128_unsigned(len(func['locals']), min_bytes=locals_count_len))

            for local in func['locals']:
                local_len = local.get('len', 0)
                locals_buffer.extend(write_leb128_unsigned(local['count'], min_bytes=local_len))
                locals_buffer.append(local['type'])

            body_buffer.extend(locals_buffer)

            for instr in func['code']:
                opcode = instr[1]
                operands = instr[2]
                
                temp_buf = bytearray()
                temp_buf.append(opcode)

                if opcode in block_start_opcodes:
                    val, len_ = self._extract_operand(operands[0])
                    # Fix: Handle value types (0x7F=i32 etc) and 0x40 (void) as raw bytes
                    # If we use write_leb128_signed(127), we get 0xFF 0x00 (Index 127) which is wrong for i32
                    if val == 0x40 or (val >= 0x70 and val <= 0x7F):
                        temp_buf.append(val)
                    else:
                        temp_buf.extend(write_leb128_signed(val))

                elif opcode in [0x20, 0x21, 0x22, 0x23, 0x24, 0x10, 0x0C, 0x0D, 0x25, 0x26]:
                    val, length = self._extract_operand(operands[0])
                    temp_buf.extend(write_leb128_unsigned(val, min_bytes=length))

                elif opcode == 0x11:
                    val1, len1 = self._extract_operand(operands[0])
                    val2, len2 = self._extract_operand(operands[1])
                    temp_buf.extend(write_leb128_unsigned(val1, min_bytes=len1))
                    temp_buf.extend(write_leb128_unsigned(val2, min_bytes=len2))

                elif opcode == 0x0E:
                    cnt, cnt_len = self._extract_operand(operands[0])
                    temp_buf.extend(write_leb128_unsigned(cnt, min_bytes=cnt_len))
                    targets = operands[1:-1]
                    for t_op in targets:
                        t_val, t_len = self._extract_operand(t_op)
                        temp_buf.extend(write_leb128_unsigned(t_val, min_bytes=t_len))
                    def_val, def_len = self._extract_operand(operands[-1])
                    temp_buf.extend(write_leb128_unsigned(def_val, min_bytes=def_len))

                elif opcode in [0x3F, 0x40]:
                    val, length = self._extract_operand(operands[0] if operands else 0)
                    temp_buf.extend(write_leb128_unsigned(val, min_bytes=length))

                elif opcode in [0x41, 0x42]:
                    val, length = self._extract_operand(operands[0])
                    temp_buf.extend(write_leb128_signed(val, min_bytes=length))

                elif opcode in [0x43, 0x44]:
                    op = operands[0]
                    if isinstance(op, dict):
                        val = op['val']
                        if opcode == 0x43:
                            temp_buf.extend(struct.pack('<f', float(val)))
                        else:
                            temp_buf.extend(struct.pack('<d', float(val)))
                    else:
                        temp_buf.extend(op)

                elif 0x28 <= opcode <= 0x3E:
                    val1, len1 = self._extract_operand(operands[0])
                    val2, len2 = self._extract_operand(operands[1])
                    temp_buf.extend(write_leb128_unsigned(val1, min_bytes=len1))
                    temp_buf.extend(write_leb128_unsigned(val2, min_bytes=len2))

                elif opcode == 0xFC:
                    sub_val, sub_len = self._extract_operand(operands[0])
                    temp_buf.extend(write_leb128_unsigned(sub_val, min_bytes=sub_len))
                    args = operands[1]
                    for arg in args:
                        val, length = self._extract_operand(arg)
                        temp_buf.extend(write_leb128_unsigned(val, min_bytes=length))

                body_buffer.extend(temp_buf)

            final_buffer.extend(write_leb128_unsigned(len(body_buffer)))
            final_buffer.extend(body_buffer)

        return bytes(final_buffer)

    def decode_import_section(self, payload_data):
        count, bytes_read = read_leb128_unsigned(payload_data, 0)
        offset = bytes_read
        imports = []
        for i in range(count):
            if offset >= len(payload_data): break
            module_name, mb = read_utf8_string(payload_data, offset)
            offset += mb
            field_name, fb = read_utf8_string(payload_data, offset)
            offset += fb
            kind = payload_data[offset]
            offset += 1
            
            desc = {
                'index': i, 'module_name': module_name,
                'field_name': field_name, 'kind': kind,
                'kind_name': IMPORT_EXPORT_KIND_NAMES.get(kind, f"0x{kind:02x}")
            }
            if kind == EXTERNAL_FUNCTION:
                idx, b = read_leb128_unsigned(payload_data, offset)
                offset += b
                desc['type_index'] = idx
            elif kind == EXTERNAL_TABLE:
                offset += 1 # elem_type
                flags = payload_data[offset]
                offset += 1
                i_size, b = read_leb128_unsigned(payload_data, offset)
                offset += b
                if flags & 1:
                    m_size, b = read_leb128_unsigned(payload_data, offset)
                    offset += b
            elif kind == EXTERNAL_MEMORY:
                flags = payload_data[offset]
                offset += 1
                i_pages, b = read_leb128_unsigned(payload_data, offset)
                offset += b
                if flags & 1:
                    m_pages, b = read_leb128_unsigned(payload_data, offset)
                    offset += b
            elif kind == EXTERNAL_GLOBAL:
                g_type = payload_data[offset]
                offset += 1 # type
                g_mut = payload_data[offset]
                offset += 1 # mutable
                
                type_name = VALUE_TYPE_NAMES.get(g_type, f"0x{g_type:02x}")
                desc['global_type'] = g_type
                desc['global_type_name'] = type_name
                desc['global_mut'] = g_mut
            elif kind == EXTERNAL_TAG:
                 offset += 1 # attr
                 print("WARN: TAG skipped")
            
            imports.append(desc)
            
        self.imports = imports
        self.imported_func_count = sum(1 for imp in imports if imp['kind'] == EXTERNAL_FUNCTION)
        return imports

    def decode_export_section(self, payload_data):
        offset = 0
        if offset >= len(payload_data): return []
        count, b = read_leb128_unsigned(payload_data, offset)
        offset += b
        exports = []
        for i in range(count):
            name, b = read_utf8_string(payload_data, offset)
            offset += b
            kind = payload_data[offset]
            offset += 1
            idx, b = read_leb128_unsigned(payload_data, offset)
            offset += b
            
            export_info = {
                'index': i, 'name': name, 'kind': kind,
                'export_index': idx,
                'kind_name': IMPORT_EXPORT_KIND_NAMES.get(kind, f"0x{kind:02x}")
            }
            exports.append(export_info)
            
            if kind == EXTERNAL_FUNCTION:
                self.module_function_names[idx] = name
                
        return exports

    def ensure_memory_size(self, section_lists, required_size):
        PAGE_SIZE = 65536
        required_pages = (required_size + PAGE_SIZE - 1) // PAGE_SIZE

        mem_sec = next((s for s in section_lists if s['section_id'] == 5), None)
        
        if mem_sec:
            payload = bytearray(mem_sec['data'])
            offset = 0
            mem_count, bytes_read = read_leb128_unsigned(payload, offset)
            offset += bytes_read
            flags = payload[offset]
            offset += 1
            initial_pages, ib = read_leb128_unsigned(payload, offset)
            
            if initial_pages < required_pages:
                print(f"   [Memory] Increasing internal memory pages from {initial_pages} to {required_pages}")
                new_payload = bytearray()
                new_payload.extend(write_leb128_unsigned(mem_count))
                new_payload.append(flags)
                new_payload.extend(write_leb128_unsigned(required_pages))
                if flags & 0x01:
                    max_pages, maxb = read_leb128_unsigned(payload, offset + ib)
                    if max_pages < required_pages: max_pages = required_pages + 10
                    new_payload.extend(write_leb128_unsigned(max_pages))
                mem_sec['data'] = bytes(new_payload)

        # Check Import Section for External Memory
        imp_sec = next((s for s in section_lists if s['section_id'] == 2), None)
        if imp_sec:
            payload = bytearray(imp_sec['data'])
            offset = 0
            count, b = read_leb128_unsigned(payload, offset)
            offset += b
            
            # We need to reconstruct the section because we might change length of LEB128 numbers
            new_payload = bytearray()
            new_payload.extend(write_leb128_unsigned(count))
            
            modified = False
            
            for _ in range(count):
                if offset >= len(payload): break
                
                # Copy module name
                start = offset
                _, mb = read_utf8_string(payload, offset)
                offset += mb
                
                # Copy field name
                _, fb = read_utf8_string(payload, offset)
                offset += fb
                
                kind = payload[offset]
                offset += 1
                
                # Copy up to kind
                new_payload.extend(payload[start:offset])
                
                if kind == EXTERNAL_MEMORY:
                    flags = payload[offset]
                    offset += 1
                    i_pages, ib = read_leb128_unsigned(payload, offset)
                    offset += ib
                    
                    new_payload.append(flags)
                    
                    effective_pages = i_pages
                    if i_pages < required_pages:
                        print(f"   [Memory] Increasing IMPORTED memory pages from {i_pages} to {required_pages}")
                        effective_pages = required_pages
                        modified = True
                    
                    new_payload.extend(write_leb128_unsigned(effective_pages))
                    
                    if flags & 1:
                        m_pages, mb = read_leb128_unsigned(payload, offset)
                        offset += mb
                        if m_pages < effective_pages: m_pages = effective_pages + 10
                        new_payload.extend(write_leb128_unsigned(m_pages))
                        
                elif kind == EXTERNAL_FUNCTION:
                    idx, b = read_leb128_unsigned(payload, offset)
                    offset += b
                    new_payload.extend(write_leb128_unsigned(idx))
                elif kind == EXTERNAL_TABLE:
                    # elem_type(1) + flags(1) + initial(leb) + [max(leb)]
                    # Just copy raw bytes? Hard to know length without parsing
                    # Let's parse.
                    new_payload.append(payload[offset]) # elem_type
                    offset += 1
                    flags = payload[offset]
                    new_payload.append(flags)
                    offset += 1
                    i_size, b = read_leb128_unsigned(payload, offset)
                    offset += b
                    new_payload.extend(write_leb128_unsigned(i_size))
                    if flags & 1:
                        m_size, b = read_leb128_unsigned(payload, offset)
                        offset += b
                        new_payload.extend(write_leb128_unsigned(m_size))
                elif kind == EXTERNAL_GLOBAL:
                    # type(1) + mut(1)
                    new_payload.append(payload[offset])
                    offset += 1
                    new_payload.append(payload[offset])
                    offset += 1
                elif kind == EXTERNAL_TAG:
                    new_payload.append(payload[offset])
                    offset += 1 # attribute
                    # assuming tag type 0
                else:
                     print(f"WARN: Unknown Import Kind {kind}")
                     
            if modified:
                imp_sec['data'] = bytes(new_payload)


    def find_safe_data_offset(self, section_lists):
        data_sec = next((s for s in section_lists if s['section_id'] == 11), None)
        if not data_sec: return 1024
        
        payload = data_sec['data']
        offset = 0
        count, b = read_leb128_unsigned(payload, offset)
        offset += b
        max_limit = 0
        
        for _ in range(count):
            if offset >= len(payload): break
            mode = payload[offset]
            offset += 1
            mem_offset = 0
            is_active = False
            
            if mode == 0:
                is_active = True
                if payload[offset] == 0x41:
                    offset += 1
                    val, vb = read_leb128_signed(payload, offset)
                    mem_offset = val
                    offset += vb + 1
                else: is_active = False # complex expression
            elif mode == 2:
                is_active = True
                _, mb = read_leb128_unsigned(payload, offset)
                offset += mb
                if payload[offset] == 0x41:
                    offset += 1
                    val, vb = read_leb128_signed(payload, offset)
                    mem_offset = val
                    offset += vb + 1
            
            size, sb = read_leb128_unsigned(payload, offset)
            offset += sb + size
            
            if is_active:
                end = mem_offset + size
                if end > max_limit: max_limit = end
                
        safe = (max_limit + 15) & ~15
        return safe if safe > 0 else 1024
