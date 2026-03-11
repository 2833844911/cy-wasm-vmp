import os
from .consts import WASM_MAGIC, WASM_VERSION
from .codec import WasmCodec
from .analyzer import WasmAnalyzer
from .obfuscator import WasmObfuscator
from .utils import write_leb128_unsigned, write_leb128_signed, read_leb128_unsigned
from .wasmvmp import WasmVMP
from .preprocessor import preprocess_br_table
import random
from .instructions_expander import InstructionExpander

class JiexStart:
# ... (existing code)


    def __init__(self, wasm_file='base64_2.wasm'):
        if not os.path.exists(wasm_file):
            raise FileNotFoundError(f"File not found: {wasm_file}")

        with open(wasm_file, "rb") as f:
            self.wasm_data = f.read()

        self.codec = WasmCodec()
        # Analyzer initially has no signatures, will update if needed
        # Fix: Pass types to analyzer for call_indirect support
        self.analyzer = WasmAnalyzer(types=self.codec.types)
        self.obfuscator = WasmObfuscator(self.analyzer)

        self.section_lists = []
        self.imports = []
        self.exports = []
        self.functions = []
        self.globals = []
        self.function_codes = []

    def parse_module(self):
        if not self.wasm_data: return
        print(f"\n{'#' * 60}\n# Start Parsing WASM Module\n{'#' * 60}")

        offset = 0
        self.codec.decode_module_header(self.wasm_data, offset)
        offset += 8

        self.section_lists = []
        while offset < len(self.wasm_data):
            section_info, offset = self.codec.read_next_section(self.wasm_data, offset)
            if section_info == False: break
            self.section_lists.append(section_info)

        new_wasm = bytearray()
        new_wasm.extend(WASM_MAGIC)
        new_wasm.extend(WASM_VERSION)

        # === Config ===
        # ==============

        # 1. Analyze Sections
        for section_info in self.section_lists:
            sec_id = section_info['section_id']
            payload = section_info['data']


            if sec_id == 1:  # Export (Wait, ID 1 is Type)
                self.codec.decode_type_section(payload)
                self.analyzer.types = self.codec.types # [Fix] Update analyzer types reference
            elif sec_id == 2: # Import
                self.imports = self.codec.decode_import_section(payload)
                # Pass imports to obfuscator as it's needed for function index calculation
                self.obfuscator.imports = self.imports
            elif sec_id == 3: # Function
                self.functions = self.codec.decode_function_section(payload)

            elif sec_id == 6: # Global
                self.globals = self.codec.decode_global_section(payload)

            elif sec_id == 7: # Export
                self.exports = self.codec.decode_export_section(payload)
                # Codec collects names during export parsing
                self.obfuscator.module_function_names = self.codec.module_function_names

            elif sec_id == 10: # Code
                print(f"-> Processing CODE Section")
                self.function_codes = self.codec.decode_code_section(section_info)

            elif sec_id == 11: # Data
                pass # Process later


        # Build function signatures for Analyzer
        func_signatures = {}
        func_idx = 0

        # 1. Import Functions
        for imp in self.imports:
            if imp['kind'] == 0: # EXTERNAL_FUNCTION
                type_idx = imp['type_index']
                if type_idx < len(self.codec.types):
                    sig = self.codec.types[type_idx]
                    func_signatures[func_idx] = (sig['params'], sig['results'])
                func_idx += 1

        # 2. Internal Functions
        for func in self.functions:
            type_idx = func['type_index']
            if type_idx < len(self.codec.types):
                sig = self.codec.types[type_idx]
                func_signatures[func_idx] = (sig['params'], sig['results'])
            func_idx += 1

        self.analyzer.func_signatures = func_signatures
        print(f"-> Analyzer updated with {len(func_signatures)} function signatures")

        # Build global types for Analyzer
        global_types = {}
        global_idx = 0

        # 1. Import Globals
        for imp in self.imports:
            if imp['kind'] == 3: # EXTERNAL_GLOBAL
                # Note: Import section parsing now stores type for globals in 'desc'
                if 'global_type_name' in imp:
                    global_types[global_idx] = imp['global_type_name']
                else:
                    global_types[global_idx] = 'i32' # Fallback
                global_idx += 1

        # 2. Internal Globals
        for glob in self.globals:
            global_types[global_idx] = glob['type_name']
            global_idx += 1

        self.analyzer.global_types = global_types
        print(f"-> Analyzer updated with {len(global_types)} global variables")

    def encrypt_module(self, output_filename="output.wasm", not_jeb=False, selected_functions=None, instruction_expansion_factor=1):
        """
        :param selected_functions: List of global function indices to encrypt. If None, encrypt all (except last one as per original logic).
        :param instruction_expansion_factor: How many instruction variants to keep (N:M reduction).
        """
        print(f"\n{'#' * 60}\n# Start Encryption & Rebuilding\n{'#' * 60}")
        
        new_wasm = bytearray()
        new_wasm.extend(WASM_MAGIC)
        new_wasm.extend(WASM_VERSION)

        # === Config ===
        CONF_KEY = random.randint(20, 1000000)
        # ==============

        # 1.5 Inject Global SP (Stack Pointer) for VMP
        self.obfuscator.can_safe_mem = self.codec.find_safe_data_offset(self.section_lists)
        # Fix: Move VMP Data and Stack to high memory (10MB+) to avoid conflicts with original Stack/Heap
        # Original Stack/Heap is likely around 64KB-1MB.
        # 10MB is safe and within default 16MB memory.

        vmp_base_addr = 10 * 1024 * 1024 # 10MB
        # vmp_base_addr = self.obfuscator.can_safe_mem
        vmp_data_offset = vmp_base_addr

        # Reserve space for VMP Data (will be updated as we encode)
        # We'll put Stack AFTER VMP Data.
        # But we need SP init value NOW.
        # Let's assume VMP Data is < 1MB.
        # So put Stack at 11MB.
        sp_start_addr = vmp_base_addr + (1 * 1024 * 1024) # 11MB

        sp_global_idx = len(self.analyzer.global_types)

        print(f"-> Injecting Global SP at index {sp_global_idx} (init: {sp_start_addr})")

        new_global = {
             'index': len(self.globals),
             'type': 0x7F, # i32
             'type_name': 'i32',
             'mutability': 1, # var
             'init_val': sp_start_addr
        }
        self.globals.append(new_global)
        self.analyzer.global_types[sp_global_idx] = 'i32'
        
        # Re-encode Global Section immediately
        encoded_globals = self.codec.encode_global_section(self.globals)
        global_sec = next((s for s in self.section_lists if s['section_id'] == 6), None)
        if global_sec:
             global_sec['data'] = encoded_globals
        else:
             print("WARN: No Global Section found to inject SP. VMP might fail.")

        # [Instruction Expansion]
        # Perform expansion BEFORE scanning for VMP locals, so new locals are counted.
        # This modifies function bodies in-place.
        # expander = InstructionExpander()
        # for func in self.function_codes:
        #     expander.process_function(func)

        # Prepare locals_types for Function 16
        vmp_data_payload = bytearray()
        # vmp_data_offset is already set to vmp_base_addr
        max_parem = {'i32':0, 'i64':0, 'f32':0, 'f64':0}
        max_resul = {'i32':0, 'i64':0, 'f32':0, 'f64':0}
        local_dict = {
            'i32': {'count': 0, 'type_name': 'i32', 'type': 127, 'len': 1},
            'i64': {'count': 0, 'type_name': 'i64', 'type': 126, 'len': 1},
            'f32': {'count': 0, 'type_name': 'f32', 'type': 125, 'len': 1},
            'f64': {'count': 0, 'type_name': 'f64', 'type': 124, 'len': 1},
        }
        max_code = 0
        print(selected_functions)
        for funidx in range(len(self.function_codes) - 1):
            global_idx = self.codec.imported_func_count + funidx
            
            # Filter if selection is provided
            if selected_functions is not None:
                if global_idx not in selected_functions:
                    continue
        # for funidx in range(2,3):
            target_fun = self.function_codes[funidx]
            max_code += len(target_fun['code'])
            locals_types= {'i32':0, 'i64':0, 'f32':0, 'f64':0}
            for locals in target_fun['locals']:
                for _ in range(locals['count']):
                    locals_types[locals['type_name']] += 1
            if 'i32' in locals_types:
                if locals_types['i32'] > local_dict['i32']['count']:
                    local_dict['i32']['count'] = locals_types['i32']
            if 'i64' in locals_types:
                if locals_types['i64'] > local_dict['i64']['count']:
                    local_dict['i64']['count'] = locals_types['i64']
            if 'f32' in locals_types:
                if locals_types['f32'] > local_dict['f32']['count']:
                    local_dict['f32']['count'] = locals_types['f32']
            if 'f64' in locals_types:
                if locals_types['f64'] > local_dict['f64']['count']:
                    local_dict['f64']['count'] = locals_types['f64']


            arr = target_fun['signature']['params']

            # 使用字典手动计数
            count_dict = {}
            for element in arr:
                if element in count_dict:
                    count_dict[element] += 1
                else:
                    count_dict[element] = 1
            if 'i32' in count_dict:
                if count_dict['i32'] > max_parem['i32']:
                    max_parem['i32'] = count_dict['i32']
            if 'i64' in count_dict:
                if count_dict['i64'] > max_parem['i64']:
                    max_parem['i64'] = count_dict['i64']
            if 'f32' in count_dict:
                if count_dict['f32'] > max_parem['f32']:
                    max_parem['f32'] = count_dict['f32']
            if 'f64' in count_dict:
                if count_dict['f64'] > max_parem['f64']:
                    max_parem['f64'] = count_dict['f64']

            arr = target_fun['signature']['results']
            # 使用字典手动计数
            count_dict = {}
            for element in arr:
                if element in count_dict:
                    count_dict[element] += 1
                else:
                    count_dict[element] = 1
            if 'i32' in count_dict:
                if count_dict['i32'] > max_resul['i32']:
                    max_resul['i32'] = count_dict['i32']
            if 'i64' in count_dict:
                if count_dict['i64'] > max_resul['i64']:
                    max_resul['i64'] = count_dict['i64']
            if 'f32' in count_dict:
                if count_dict['f32'] > max_resul['f32']:
                    max_resul['f32'] = count_dict['f32']
            if 'f64' in count_dict:
                if count_dict['f64'] > max_resul['f64']:
                    max_resul['f64'] = count_dict['f64']


        wasmVmp = WasmVMP(max_parem, max_resul,local_dict,self.codec, max_code, len(self.function_codes),sp_global_idx=sp_global_idx, func_signatures=self.analyzer.func_signatures, global_types=self.analyzer.global_types, instruction_expansion_factor=instruction_expansion_factor)

        for funidx in range(len(self.function_codes) - 1):
            target_func = self.function_codes[funidx]
            
            # Calculate global index for checking against selection
            # internal index 'funidx' maps to global index: imported_func_count + funidx
            # But wait, self.function_codes is the list of code entries.
            # In parse_module, we didn't explicitly store imported_func_count in JiexStart, but codec has it.
            global_idx = self.codec.imported_func_count + funidx
            
            # Filter if selection is provided
            if selected_functions is not None:
                if global_idx not in selected_functions:
                    continue

            # iff = 1
            # for funidx in range(iff,200):


            # funidx = 3
            target_func = self.function_codes[funidx]
            # if len(target_func['code']) < 40:
            #     continue

            # [Preprocessor] Remove br_table
            preprocess_br_table(target_func)

            # if funidx == 95:
            #     print(f"[Core Debug] Post-Preprocess Func #95 Locals: {target_func['locals']}")

            codeoffun, mycodeshuz = wasmVmp.encode(target_func=target_func, initial_stack=[],  bytecode_offset=vmp_data_offset)
            for val in mycodeshuz:
                # Assuming val is i32, pack as 4 bytes little endian
                # Note: mycodeshuz contains integers (block IDs, etc.)
                # We need to ensure they fit in i32.
                # print(val)
                # Fix: Handle 32-bit wrapping to assume both negative and large unsigned values
                vmp_data_payload.extend((int(val) & 0xFFFFFFFF).to_bytes(4, byteorder='little', signed=False))

            vmp_data_offset += len(mycodeshuz) * 4
            target_func['code'] = codeoffun
        newfunction = wasmVmp.over()

        # [VMP Injection] Append the VMP Interpreter Function to the module
        print(f"-> Appending VMP Interpreter Function (Type: {newfunction['type_index']})")

        # 1. Add to Code Section
        self.function_codes.append(newfunction)

        # 2. Add to Function Section (Type Indices)
        self.functions.append({
            'index': len(self.functions),
            'type_index': newfunction['type_index']
        })

        # [FIX] Re-encode Function Section immediately so Obfuscator sees the updated internal count
        # This prevents it from pointing Start to the VMP function (which has params) instead of Decryption function.
        func_sec = next((s for s in self.section_lists if s['section_id'] == 3), None)
        if func_sec:
             func_sec['data'] = self.codec.encode_function_section(self.functions)

        # [Fix] Update __heap_base to avoid heap corruption
        # Find export named '__heap_base'
        heap_base_export = next((e for e in self.exports if e['name'] == '__heap_base'), None)
        if heap_base_export and heap_base_export['kind'] == 3: # EXTERNAL_GLOBAL
            heap_base_idx = heap_base_export['export_index']
            # Find the global
            # Note: export_index is the global index in the module (imports + internals)
            # self.globals only contains internal globals.
            # We need to map global index to internal global index.
            num_imported_globals = len([i for i in self.imports if i['kind'] == 3])
            internal_idx = heap_base_idx - num_imported_globals

            if 0 <= internal_idx < len(self.globals):
                print(f"-> Updating __heap_base (Global {heap_base_idx}) to {vmp_data_offset}")
                # Update init_val
                # We need to re-encode the global section later, so updating the dict is enough if we handle it.
                # But wait, self.globals entries have 'init_val' or 'init_raw'.
                # We should update 'init_val' and remove 'init_raw' to force re-encoding.
                self.globals[internal_idx]['init_val'] = vmp_data_offset
                if 'init_raw' in self.globals[internal_idx]:
                    del self.globals[internal_idx]['init_raw']
            else:
                print(f"WARN: __heap_base (Global {heap_base_idx}) is imported or invalid?")


        # 2. Obfuscation
        self.obfuscator.params = {} # Reset or init params if used

        stack_size = 1024 * 1024 * 1 # 1MB Stack
        self.codec.ensure_memory_size(self.section_lists, sp_start_addr + stack_size)
        #
        segment_configs = []
        for section_info in self.section_lists:
            if section_info['section_id'] == 11:
                print(f"-> Processing DATA Section (Obfuscation)")
                new_data, configs = self.obfuscator.obfuscate_data_section(section_info, CONF_KEY)
                section_info['data'] = new_data
                segment_configs.extend(configs)

        # Inject VMP Data Segment
        if len(vmp_data_payload) > 0:
            print(f"-> Injecting VMP Bytecode Data Segment (Size: {len(vmp_data_payload)} bytes) at {vmp_base_addr}")
            # Create a new active data segment
            # We need to construct the section entry manually or use codec helper if available.
            # Since we are modifying section_lists, we can append a new Data Section if it doesn't exist,
            # or append to the existing Data Section's payload?
            # Wait, Data Section contains a vector of Data Segments.
            # We need to find the Data Section and add a segment to it.

            # Construct Data Segment
            # Mode: Active (0)
            # Offset: i32.const addr
            # Content: bytes

            # We need to encode this segment.
            # The current codec.decode_data_section returns a list of segments?
            # No, decode_code_section returns code list.
            # decode_data_section is not explicitly called in loop, but we have 'section_lists'.
            # section_info['data'] is the raw bytes of the section.

            # To properly add a segment, we should probably use a helper or re-parse.
            # But here we are operating on raw section data in `section_lists`.
            # This is tricky because `section_lists` contains raw bytes for most sections except Code/Import/Export/Global/Function which we parsed.
            # Data section was NOT parsed into a list of segments in `self.data_segments`.
            # We only iterated it for obfuscation.

            # Let's look at `obfuscate_data_section`. It decodes, obfuscates, and re-encodes.
            # So we should probably inject our data BEFORE obfuscation if we want it obfuscated,
            # OR inject it as a cleartext segment AFTER obfuscation.
            # Given VMP bytecode is "code", maybe we don't need to encrypt it yet?
            # The user didn't ask for encryption, just storage.

            # Simplest way: Create a NEW Data Section if we can, or append to existing.
            # But WASM only allows one Data Section (ID 11).

            # Let's try to append to `vmp_data_payload` to the end of the LAST data segment?
            # No, that messes up offsets.
            # We should create a NEW segment.

            # We need to encode a Data Segment:
            # [Index: 0 (Active), OffsetExpr: (i32.const ADDR), Size: LEB128, Data: bytes]

            vm_seg_raw = bytearray()
            vm_seg_raw.append(0) # Mode 0: Active
            vm_seg_raw.extend(write_leb128_unsigned(0x41)) # i32.const
            vm_seg_raw.extend(write_leb128_signed(vmp_base_addr))
            vm_seg_raw.append(0x0B) # end
            vm_seg_raw.extend(write_leb128_unsigned(len(vmp_data_payload)))
            vm_seg_raw.extend(vmp_data_payload)

            # Now find Data Section
            data_sec = next((s for s in self.section_lists if s['section_id'] == 11), None)
            if data_sec:
                # We need to append this segment to the existing Data Section.
                # The Data Section is: [Count (LEB128), Segment1, Segment2, ...]
                # We need to parse the count, increment it, and append our segment bytes.

                old_data = data_sec['data']
                count, count_len = read_leb128_unsigned(old_data, 0) # This method is in utils, not codec instance?
                # Wait, read_leb128_unsigned is imported from utils in core.py? No, from .utils

                count, count_len = read_leb128_unsigned(old_data, 0)
                new_count = count + 1

                new_data_sec = bytearray()
                new_data_sec.extend(write_leb128_unsigned(new_count))
                new_data_sec.extend(old_data[count_len:]) # Existing segments
                new_data_sec.extend(vm_seg_raw) # New segment

                data_sec['data'] = new_data_sec
            else:
                # Create new Data Section
                # Count: 1
                new_data_sec = bytearray()
                new_data_sec.extend(write_leb128_unsigned(1))
                new_data_sec.extend(vm_seg_raw)

                self.section_lists.append({
                    'section_id': 11,
                    'data': new_data_sec
                })
                # Sort sections? WASM requires order. Data (11) is usually last.
                self.section_lists.sort(key=lambda x: x['section_id'])


            # Update Data Count Section (ID 12) if present
            data_count_sec = next((s for s in self.section_lists if s['section_id'] == 12), None)
            if data_count_sec:
                # Data Count section contains a single LEB128 u32
                old_count, _ = read_leb128_unsigned(data_count_sec['data'], 0)
                new_count = old_count + 1
                data_count_sec['data'] = bytearray(write_leb128_unsigned(new_count))
                print(f"-> Updated Data Count Section: {old_count} -> {new_count}")

        # 3. Inject Start
        if segment_configs:
            # 3.1 Adjust Headers (Type, Func, Start)
            new_func_idx, original_start_idx = self.obfuscator.inject_decryption_routine(
                self.section_lists, segment_configs, CONF_KEY, None
            )
            # Ensure the new type (void->void) used by injected function is registered in codec
            # so it doesn't get lost when we re-encode the Type section later.
            # so it doesn't get lost when we re-encode the Type section later.
            decryption_type_idx = self.codec.add_type([], [])

            # [FIX] Also update self.functions list because we re-encode it later
            # This ensures Function Section count matches Code Section count
            self.functions.append({
                'index': len(self.functions),
                'type_index': decryption_type_idx
            })

            # 3.2 Add Code body
            decryption_func_ast = self.obfuscator._gen_decryption_instrs(
                segment_configs, CONF_KEY, original_start_idx, not_jeb=not_jeb
            )[0]

            self.function_codes.append(decryption_func_ast)


        else:
            print("No valid Data segments found, skipping injection.")



        # 3.3 Re-encode Code Section
        encoded_code = self.codec.encode_code_section(self.function_codes)

        # Find Code Section and update data
        code_sec = next((s for s in self.section_lists if s['section_id'] == 10), None)
        if code_sec:
            code_sec['data'] = encoded_code
        final_wasm = bytearray()
        final_wasm.extend(WASM_MAGIC)
        final_wasm.extend(WASM_VERSION)

        # Re-encode all sections
        # Note: If Code section was modified (in memory structure self.function_codes),
        # we need to make sure `self.section_lists` has the encoded data.

        # Re-encode Type Section (in case new types were added)
        type_sec = next((s for s in self.section_lists if s['section_id'] == 1), None)
        if type_sec:
             type_sec['data'] = self.codec.encode_type_section()

        # Re-encode Function Section
        func_sec = next((s for s in self.section_lists if s['section_id'] == 3), None)
        if func_sec:
             func_sec['data'] = self.codec.encode_function_section(self.functions)


        for section_info in self.section_lists:
            sec_id = section_info['section_id']
            payload = section_info['data']

            final_wasm.append(sec_id)
            final_wasm.extend(write_leb128_unsigned(len(payload)))
            final_wasm.extend(payload)

        with open(output_filename, "wb") as f:
            f.write(final_wasm)
        print(f"\n[SUCCESS] Successfully generated: {output_filename}")
