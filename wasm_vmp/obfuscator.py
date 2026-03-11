from .consts import VALUE_TYPE_NAMES
from .utils import (
    add_instr, pack_op, write_leb128_unsigned, write_leb128_signed,
    read_leb128_unsigned, read_leb128_signed, get_opcode_name
)
import random

class WasmObfuscator:
    def __init__(self, analyzer=None, imports=None, module_function_names=None):
        self.analyzer = analyzer
        self.imports = imports or []
        self.module_function_names = module_function_names or {}
        self.can_safe_mem = 1024

    def is_metadata_segment(self, segment_data):
        metadata_keywords = [
            b'std::', b'emscripten', b'unsigned', b'basic_string',
            b'exception', b'typeinfo', b'double', b'float', b'bool',
            b'void', b'catching',
        ]
        if len(segment_data) < 100: return False
        sample = segment_data
        keyword_count = sum(1 for kw in metadata_keywords if kw in sample)
        return keyword_count >= 3

    def obfuscate_data_section(self, section_info, xor_key):
        print(f"\n{'=' * 20} Starting Data Obfuscation {'=' * 20}")
        payload = bytearray(section_info['data'])
        offset = 0
        segment_configs = []

        count, read_len = read_leb128_unsigned(payload, offset)
        offset += read_len
        print(f"-> Found {count} data segments")

        for i in range(count):
            if offset >= len(payload): break
            mode = payload[offset]
            offset += 1
            mem_offset_val = 0
            is_active = False

            if mode == 0:  # Active
                is_active = True
                if payload[offset] == 0x41:  # i32.const
                    offset += 1
                    val, val_len = read_leb128_signed(payload, offset)
                    mem_offset_val = val
                    offset += val_len
                    if payload[offset] == 0x0B: offset += 1
                    else: is_active = False
                else: is_active = False

            elif mode == 1:
                is_active = False

            elif mode == 2:
                is_active = True
                _, mem_idx_len = read_leb128_unsigned(payload, offset)
                offset += mem_idx_len
                if payload[offset] == 0x41:
                    offset += 1
                    val, val_len = read_leb128_signed(payload, offset)
                    mem_offset_val = val
                    offset += val_len
                    offset += 1
                else: is_active = False

            data_size, size_len = read_leb128_unsigned(payload, offset)
            offset += size_len
            
            segment_data = payload[offset:offset + data_size]

            if is_active and data_size > 0:
                current_key = xor_key & 0xFF
                for j in range(data_size):
                    # 1. XOR
                    payload[offset + j] ^= current_key
                    # 2. Add 7
                    payload[offset + j] = (payload[offset + j] + 7) & 0xFF
                    # 3. Update Key
                    current_key = (current_key + 14) & 0xFF

                segment_configs.append({
                    'start': offset,
                    'len': data_size,
                    'mem_offset': mem_offset_val
                })
                break # Only encrypt one supported segment for now
            else:
                if is_active:
                    print(f"   [Obfuscator] Empty or skipped Segment {i}")

            offset += data_size

        return bytes(payload), segment_configs

    def kozhilc(self, code, jbbl):
        code_len = len(code)
        new_code = []
        allshuz = [i for i in range(0+5, code_len + 1+5)]
        random.shuffle(allshuz)
        ying_code = []
        shangyib_code = allshuz.pop()
        need_jbbl = jbbl-2
        temp_val_local = jbbl-3
        save_start_addr_local = jbbl - 1
        save_idx_addr_local = jbbl
        frist_come_code = shangyib_code
        
        for code_l in code:
            shan_code = shangyib_code
            shangyib_code = allshuz.pop()
            ying_code.append([shan_code, code_l, shangyib_code])
        ying_code.append([shangyib_code, add_instr(0x0C, pack_op(2)) , 0, "end"]) # br 2 (跳转到block外)
        random.shuffle(ying_code)

        new_code.append(add_instr(0x02, 0x40)) # block
        new_code.append(add_instr(0x41, pack_op(frist_come_code))) # i32.const (初始状态值)
        new_code.append(add_instr(0x21, pack_op(need_jbbl))) # local.set (设置状态变量)

        new_code.append(add_instr(0x41, pack_op(self.can_safe_mem))) # i32.const (安全内存起始地址)
        new_code.append(add_instr(0x21, pack_op(save_start_addr_local))) # local.set (保存起始地址)

        new_code.append(add_instr(0x41, pack_op(0))) # i32.const 0
        new_code.append(add_instr(0x21, pack_op(save_idx_addr_local))) # local.set (保存索引地址)

        new_code.append(add_instr(0x03, 0x40)) # loop
        len_ying_code = len(ying_code)

        def get_else(myshuz, idx_ying_code):
            if idx_ying_code >= len_ying_code: return
            ying_cd = ying_code[idx_ying_code]
            myshuz.append(add_instr(0x20, pack_op(need_jbbl))) # local.get (获取当前状态)
            myshuz.append(add_instr(0x41, pack_op(ying_cd[0]))) # i32.const (目标状态)
            myshuz.append(add_instr(0x46)) # i32.eq (比较状态)

            starck_list, need_param = self.analyzer.analyze_wasm_stack_types([ying_cd[1]])
            myshuz.append(add_instr(0x04, 0x40)) # if (状态匹配)

            # Removed flawed stack protection/check logic that caused infinite loop

            if ying_cd[-1] != 'end':
                myshuz.append(add_instr(0x41, pack_op(ying_cd[2]))) # i32.const (下一个状态值)
                myshuz.append(add_instr(0x21, pack_op(need_jbbl))) # local.set (更新状态)
            
            # Param retrieval logic
            for param_i in range(need_param):
                myshuz.append(add_instr(0x20, pack_op(save_idx_addr_local))) # local.get
                myshuz.append(add_instr(0x41, pack_op(need_param - param_i))) # i32.const
                myshuz.append(add_instr(0x6B)) # i32.sub (计算偏移)
                
                myshuz.append(add_instr(0x41, pack_op(4))) # i32.const 4
                myshuz.append(add_instr(0x6C)) # i32.mul (计算字节偏移)
                myshuz.append(add_instr(0x20, pack_op(save_start_addr_local))) # local.get
                myshuz.append(add_instr(0x6A)) # i32.add (基址加偏移)
                myshuz.append(add_instr(0x28, [pack_op(0), pack_op(0)])) # i32.load (加载参数)

            if need_param > 0:
                myshuz.append(add_instr(0x20, pack_op(save_idx_addr_local))) # local.get
                myshuz.append(add_instr(0x41, pack_op(need_param))) # i32.const
                myshuz.append(add_instr(0x6B)) # i32.sub
                myshuz.append(add_instr(0x21, pack_op(save_idx_addr_local))) # local.set (更新索引)

            if ying_cd[-1] != 'end':
                myshuz.append(ying_cd[1])
            else:
                myshuz.append(add_instr(0x0C, pack_op(2 + idx_ying_code))) # br (跳转)

            for i in range(len(starck_list)):
                val_type = starck_list[i]
                myshuz.append(add_instr(0x21, pack_op(temp_val_local))) # local.set (保存临时值)
                myshuz.append(add_instr(0x20, pack_op(save_start_addr_local))) # local.get
                myshuz.append(add_instr(0x20, pack_op(save_idx_addr_local))) # local.get
                myshuz.append(add_instr(0x41, pack_op(4))) # i32.const 4
                myshuz.append(add_instr(0x6C)) # i32.mul
                myshuz.append(add_instr(0x6A)) # i32.add
                myshuz.append(add_instr(0x20, pack_op(temp_val_local))) # local.get
                myshuz.append(add_instr(0x36, [pack_op(0), pack_op(0)])) # i32.store (存储结果)
                myshuz.append(add_instr(0x20, pack_op(save_idx_addr_local))) # local.get
                myshuz.append(add_instr(0x41, pack_op(1))) # i32.const 1
                myshuz.append(add_instr(0x6A)) # i32.add
                myshuz.append(add_instr(0x21, pack_op(save_idx_addr_local))) # local.set

            myshuz.append(add_instr(0x05)) # else
            get_else(myshuz, idx_ying_code+1)
            myshuz.append(add_instr(0x0B)) # end

        get_else(new_code, 0)
        new_code.append(add_instr(0x0C, pack_op(0))) # br 0 (继续循环)
        new_code.append(add_instr(0x0B)) # end loop
        new_code.append(add_instr(0x0B)) # end block
        return new_code, need_jbbl

    def _gen_decryption_instrs(self, segment_configs, xor_key, original_start_idx=None, not_jeb=False):
        instructions_all = []


        locals_list = [{'count': 8, 'type': 0x7F, 'len': 1}] # ptr, len, temp, key, ...

        def add_local_instr_all(opcode, operands=None):
            # Wrapper to reuse utils logic but append to local list
            instr = add_instr(opcode, operands)
            instructions_all.append(instr)
        for seg in segment_configs:
            instructions = []
            def add_local_instr(opcode, operands=None):
                # Wrapper to reuse utils logic but append to local list
                instr = add_instr(opcode, operands)
                instructions.append(instr)
            start_addr = seg['start']
            length = seg['len']
            mem_offset = seg['mem_offset']

            add_local_instr(0x41, pack_op(mem_offset)) # i32.const (数据段虚拟内存起始地址)
            add_local_instr(0x21, pack_op(0)) # local.set 0 (ptr)

            add_local_instr(0x41, pack_op(length)) # i32.const (数据长度)
            add_local_instr(0x21, pack_op(1)) # local.set 1 (len)

            add_local_instr(0x41, pack_op(xor_key)) # i32.const (Initial Key)
            add_local_instr(0x21, pack_op(3)) # local.set 3 (key)

            add_local_instr(0x02, 0x40) # block
            add_local_instr(0x03, 0x40) # loop

            # Wrapper to match new_jiex.py structure (depth adjustment)
            add_local_instr(0x41, pack_op(1)) # i32.const 1
            add_local_instr(0x41, pack_op(1)) # i32.const 1
            add_local_instr(0x04, 0x40) # if

            add_local_instr(0x20, pack_op(1)) # local.get 1 (len)
            add_local_instr(0x45) # i32.eqz (检查是否为0)
            add_local_instr(0x0D, pack_op(2)) # br_if 2 (如果len==0则跳出循环)


            
            add_local_instr(0x0C, pack_op(0)) # br 0 (exit if)
            if not_jeb == True:
                # jeb崩溃
                add_local_instr(0x21, pack_op(2));  # local.set 2
                add_local_instr(0x21, pack_op(2));  # local.set 2
                add_local_instr(0x21, pack_op(2));  # local.set 2

            add_local_instr(0x0B) # end if
            
            # Core Decryption
            add_local_instr(0x20, pack_op(0)) # local.get 0 (ptr)
            add_local_instr(0x20, pack_op(0)) # local.get 0 (ptr)
            add_local_instr(0x2D, [pack_op(0), pack_op(0)]) # i32.load8_u (读取字节)
            
            # 1. Sub 7
            add_local_instr(0x41, pack_op(7)) # i32.const 7
            add_local_instr(0x6B) # i32.sub
            add_local_instr(0x41, pack_op(0xFF)) # i32.const 0xFF
            add_local_instr(0x71) # i32.and

            # 2. XOR with key
            add_local_instr(0x20, pack_op(3)) # local.get 3 (key)
            add_local_instr(0x73) # i32.xor (异或解密)
            
            add_local_instr(0x3A, [pack_op(0), pack_op(0)]) # i32.store8 (写回字节)

            # 3. Update Key
            add_local_instr(0x20, pack_op(3)) # local.get 3 (key)
            add_local_instr(0x41, pack_op(14)) # i32.const 14
            add_local_instr(0x6A) # i32.add
            add_local_instr(0x41, pack_op(0xFF)) # i32.const 0xFF
            add_local_instr(0x71) # i32.and
            add_local_instr(0x21, pack_op(3)) # local.set 3 (key)

            add_local_instr(0x20, pack_op(0)) # local.get 0 (ptr)
            add_local_instr(0x41, pack_op(1)) # i32.const 1
            add_local_instr(0x6A) # i32.add (ptr++)
            add_local_instr(0x21, pack_op(0)) # local.set 0

            add_local_instr(0x20, pack_op(1)) # local.get 1 (len)
            add_local_instr(0x41, pack_op(1)) # i32.const 1
            add_local_instr(0x6B) # i32.sub (len--)
            add_local_instr(0x21, pack_op(1)) # local.set 1

            add_local_instr(0x0C, pack_op(0)) # br 0 (继续循环)
            add_local_instr(0x0B) # end loop
            add_local_instr(0x0B) # end block
        
            # Apply Kozhilc to the decryption loop if possible
            # instructions[16:32] roughly (adjusted for new instructions)
            # Original range was roughly 6 instructions. Now we have added:
            # - Sub 7 (3 instr)
            # - Key update (5 instr)
            # - Key load instead of const (0 diff in count, just opcode change)
            # Total core instructions increased significantly.
            
            strt_idx = 0
            if not_jeb == True:
                strt_idx = 3

            # The core decryption block starts after the 'if' block (which ends at index 13 + strt_idx)
            # Previous code assumed fixed indices. Let's make it relative or just update indices.
            # The 'if' block ends at index 13 (without not_jeb).
            # 0-13: setup and if check
            # 14: local.get 0 (ptr) -> Start of core
            # ...
            # End of core is before ptr++ (local.get 0, const 1, add, set 0)
            # ptr++ starts at:
            # 14 + 3(load) + 3(sub) + 1(and) + 2(xor) + 1(store) + 5(key update) = 14 + 15 = 29
            
            core_start = 14 + strt_idx + 2 # +2 for key init instructions added before block
            core_end = core_start + 16 # 16 instructions for decryption and key update

            core_instructions = instructions[core_start:core_end] if len(instructions) > core_end else []
            if False and core_instructions:
                print("   [Obfuscator] Flattening decryption loop...")
                jmzl, locals_new = self.kozhilc(core_instructions, locals_list[0]['count']-1)
                instructions_new = instructions[0:core_start] + jmzl + instructions[core_end:]
                instructions = instructions_new
            instructions_all += instructions


        if original_start_idx is not None:
            add_local_instr_all(0x10, pack_op(original_start_idx)) # call (调用原始start函数)

        add_local_instr_all(0x0B) # end

        return [{
            'index': 0,
            'locals': locals_list,
            'locals_count_len': 1,
            'code': instructions_all
        }]

    def inject_decryption_routine(self, section_lists, segment_configs, xor_key, encode_code_sec_func):
        print(f"\n{'=' * 20} Injecting Start Routine {'=' * 20}")
        
        # 1. Type Section Check
        type_sec = next((s for s in section_lists if s['section_id'] == 1), None)
        void_type_idx = 0
        target_sig = b'\x60\x00\x00' # ()->void
        if type_sec:
            cnt, lb = read_leb128_unsigned(type_sec['data'], 0)
            void_type_idx = cnt
            new_data = bytearray()
            new_data.extend(write_leb128_unsigned(cnt + 1))
            new_data.extend(type_sec['data'][lb:])
            new_data.extend(target_sig)
            type_sec['data'] = new_data
        else:
            payload = bytearray(write_leb128_unsigned(1)) + target_sig
            section_lists.insert(0, {'section_id': 1, 'data': payload})
            
        # 2. Func Index
        imported_funcs = len(self.imports)
        func_sec = next((s for s in section_lists if s['section_id'] == 3), None)
        internal_count = 0
        if func_sec:
            internal_count, _ = read_leb128_unsigned(func_sec['data'], 0)
        
        new_func_idx = imported_funcs + internal_count
        print(f"-> New Start Function Index: {new_func_idx}")
        
        # 3. Update Func Section
        if func_sec:
            cnt, lb = read_leb128_unsigned(func_sec['data'], 0)
            new_data = bytearray()
            new_data.extend(write_leb128_unsigned(cnt + 1))
            new_data.extend(func_sec['data'][lb:])
            new_data.extend(write_leb128_unsigned(void_type_idx))
            func_sec['data'] = new_data
        else:
            payload = bytearray(write_leb128_unsigned(1)) + write_leb128_unsigned(void_type_idx)
            # Find insert pos
            section_lists.insert(1, {'section_id': 3, 'data': payload})

        # 4. Start Section
        start_sec = next((s for s in section_lists if s['section_id'] == 8), None)
        original_start_idx = None
        
        if start_sec:
            original_start_idx, _ = read_leb128_unsigned(start_sec['data'], 0)
            print(f"-> Hijacking existing Start: {original_start_idx}")
            start_sec['data'] = write_leb128_unsigned(new_func_idx)
        else:
            print(f"-> Creating new Start Section: {new_func_idx}")
            payload = write_leb128_unsigned(new_func_idx)
            
            # Find correct insert position (Standard: Type(1)..Export(7) < Start(8) < Element(9)..Data(11))
            # Custom sections (0) can be ignored/skipped? 
            # Logic: Insert before the first section with ID > 8. 
            # If no such section, append.
            insert_pos = len(section_lists)
            for i, s in enumerate(section_lists):
                if s['section_id'] > 8:
                    insert_pos = i
                    break
            
            section_lists.insert(insert_pos, {'section_id': 8, 'data': payload})

        # 5. Inject Code
        code_sec = next((s for s in section_lists if s['section_id'] == 10), None)
        if code_sec:
            # We assume code_sec['parsed_funcs'] exists or we need to pass parsed functions
            # Actually, the caller should have decoded it.
            # Here we assume the caller will handle the decoding of existing code section
            # But wait, inject_decryption_routine in original code did:
            # parsed_funcs = self.function_codes (which is state)
            # So I should pass parsed_funcs here
            pass
        else:
            raise ValueError("No Code Section found")

        return new_func_idx, original_start_idx
