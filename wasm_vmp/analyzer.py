from .consts import VALUE_TYPE_NAMES

class WasmAnalyzer:
    def __init__(self, func_signatures=None, global_types=None, types=None):
        self.func_signatures = func_signatures or {}
        self.global_types = global_types or {}
        self.types = types or []

    def _get_op_stack_effect(self, opcode_name, operands, locals_types=None):
        """
        Calculate stack effect (pops, pushes) of an instruction.
        """
        name = opcode_name
        parts = name.split('.')
        category = parts[0] # i32, f64, local, memory, etc.
        
        # 1. Constants
        if 'const' in name:
            return [], [category]
            
        # 2. Variable Operations
        elif name == 'local.get':
            idx = operands[0]['val'] if isinstance(operands[0], dict) else operands[0]
            if locals_types and idx in locals_types:
                return [], [locals_types[idx]]
            return [], ['unknown']
            
        elif name == 'local.set':
            idx = operands[0]['val'] if isinstance(operands[0], dict) else operands[0]
            if locals_types and idx in locals_types:
                return [locals_types[idx]], []
            return ['any'], [] # Allow matching any top of stack
            
        elif name == 'local.tee':
            idx = operands[0]['val'] if isinstance(operands[0], dict) else operands[0]
            t = 'any'
            if locals_types and idx in locals_types:
                t = locals_types[idx]
            return [t], [t]
            
        elif name == 'global.get':
            idx = operands[0]['val'] if isinstance(operands[0], dict) else operands[0]
            val_type = self.global_types.get(idx, 'unknown')
            return [], [val_type]
        elif name == 'global.set':
            idx = operands[0]['val'] if isinstance(operands[0], dict) else operands[0]
            val_type = self.global_types.get(idx, 'unknown')
            return [val_type], []
            
        # 3. Memory Operations
        elif 'load' in name:
            return ['i32'], [category]
            
        elif name in ['unreachable', 'nop']:
            return [], []

        elif 'store' in name:
            return ['i32', category], []
            
        elif name == 'memory.size':
            return [], ['i32']
        elif name == 'memory.grow':
            return ['i32'], ['i32']
        elif name == 'memory.copy':
            return ['i32', 'i32', 'i32'], []
        elif name == 'memory.fill':
            return ['i32', 'i32', 'i32'], []
        elif name == 'memory.init':
            return ['i32', 'i32', 'i32'], []
        elif name == 'data.drop':
            return [], []
            
        # 4. Control Flow
        elif name in ['block', 'loop', 'if']:
            op0 = operands[0] if operands else 0x40
            block_type = op0['val'] if isinstance(op0, dict) else op0
            
            pops = []
            pushes = []
            
            if name == 'if':
                pops.append('i32') # condition
                
            if block_type == 0x40: # void
                pass
            elif block_type in VALUE_TYPE_NAMES: # Single return value
                pushes.append(VALUE_TYPE_NAMES[block_type])
            else:
                pass
                
            return pops, pushes
                
        elif name in ['br', 'br_if', 'br_table']:
            pops = []
            if name == 'br_if':
                pops.append('i32')
            elif name == 'br_table':
                pops.append('i32')
            return pops, []
            
        elif name == 'drop':
            return ['any'], []
        elif name == 'select':
            return ['any', 'any', 'i32'], ['any']
            
        elif name == 'call':
            func_idx = operands[0]['val'] if isinstance(operands[0], dict) else (operands[0] if operands else 0)
            if self.func_signatures:
                params, returns = self.func_signatures.get(func_idx, ([], []))
                return list(params), list(returns)
            return [], []
                
        elif name == 'call_indirect':
            type_idx = operands[0]['val'] if isinstance(operands[0], dict) else operands[0]
            params = []
            results = []
            if self.types and type_idx < len(self.types):
                type_entry = self.types[type_idx]
                params = type_entry.get('params', [])
                results = type_entry.get('results', [])
            
            # pops = params + [table_index(i32)]
            pops = list(params) + ['i32']
            return pops, list(results)
            
        # Add explicit handling for bulk_memory - MOVED UP due to fuzzy match conflict
        elif name == 'bulk_memory':
            sub_opcode = operands[0]['val'] if isinstance(operands[0], dict) else operands[0]
            
            # Saturating truncation (0x00 - 0x07)
            if sub_opcode == 0x00: return ['f32'], ['i32'] # i32.trunc_sat_f32_s
            elif sub_opcode == 0x01: return ['f32'], ['i32'] # i32.trunc_sat_f32_u
            elif sub_opcode == 0x02: return ['f64'], ['i32'] # i32.trunc_sat_f64_s
            elif sub_opcode == 0x03: return ['f64'], ['i32'] # i32.trunc_sat_f64_u
            elif sub_opcode == 0x04: return ['f32'], ['i64'] # i64.trunc_sat_f32_s
            elif sub_opcode == 0x05: return ['f32'], ['i64'] # i64.trunc_sat_f32_u
            elif sub_opcode == 0x06: return ['f64'], ['i64'] # i64.trunc_sat_f64_s
            elif sub_opcode == 0x07: return ['f64'], ['i64'] # i64.trunc_sat_f64_u
            
            # Memory ops
            elif sub_opcode == 0x08: return ['i32', 'i32', 'i32'], [] # memory.init (dest, src, size) NOTE: src is in data segment
            elif sub_opcode == 0x09: return [], [] # data.drop
            elif sub_opcode == 0x0A: return ['i32', 'i32', 'i32'], [] # memory.copy
            elif sub_opcode == 0x0B: return ['i32', 'i32', 'i32'], [] # memory.fill
            
            return [], []

        # 4. Unary / Conversions
        # Specialized Unary
        elif any(x in name for x in ['clz', 'ctz', 'popcnt', 'abs', 'neg', 'ceil', 'floor', 'sqrt', 'nearest']):
            return [category], [category]
            
        elif 'copysign' in name: # Binary but fuzzy match often misses it or confuses it?
            # copysign takes 2 args of 'category' type and returns 1
            return [category, category], [category]
            
        elif 'min' in name or 'max' in name: # Binary
            return [category, category], [category]
            
        elif 'trunc' in name:
            # Special case: trunc can be f32.trunc (preserve) or i32.trunc_f64_s (conversion)
            if 'trunc_' in name: # Conversion
                 src_str = name.split('trunc_')[1] # e.g. f64_s -> f64
                 src = 'f64' if 'f64' in src_str else ('f32' if 'f32' in src_str else 'unknown')
                 return [src], [category]
            else: # Unary (f32.trunc)
                 return [category], [category]

        # 8. Converts - MOVED UP
        elif 'wrap' in name: return ['i64'], ['i32']
        elif 'extend' in name:
            if category == 'i32': # i32.extend8_s, i32.extend16_s
                 return ['i32'], ['i32']
            return ['i32'], ['i64'] # i64.extend_i32_s/u
        elif 'promote' in name: return ['f32'], ['f64']
        elif 'demote' in name: return ['f64'], ['f32']
        elif 'convert' in name:
            # e.g. f64.convert_i32_s
            src = 'i32' if 'i32' in name.split('convert_')[1] else 'i64'
            return [src], [category]
        elif 'reinterpret' in name:
            src = 'i32' if 'i32' in name else ('i64' if 'i64' in name else ('f32' if 'f32' in name else 'f64'))
            if category == 'f32': src = 'i32'
            elif category == 'i32': src = 'f32'
            elif category == 'f64': src = 'i64'
            elif category == 'i64': src = 'f64'
            return [src], [category]

        # 5. Comparisons
        elif any(x in name for x in ['eq', 'ne', 'lt', 'gt', 'le', 'ge']):
            if 'eqz' in name:
                return [category], ['i32']
            return [category, category], ['i32']
            
        # 6. Arithmetic/Bitwise
        elif any(x in name for x in ['add', 'sub', 'mul', 'div', 'rem', 'and', 'or', 'xor', 'shl', 'shr', 'rot']):
            return [category, category], [category]
            

            
        return [], []

    def analyze_wasm_stack_types(self, instructions, initial_locals=None, debug=False):
        """
        Analyze WASM instructions return remaining stack and missing count.
        """
        stack = []
        missing_count = 0
        locals_map = initial_locals.copy() if initial_locals else {}

        def pop_stack(n=1):
            nonlocal missing_count
            popped = []
            for _ in range(n):
                if not stack:
                    missing_count += 1
                    if debug: print(f"  -> Stack underflow! Missing req: {missing_count}")
                    popped.append('underflow_val')
                else:
                    popped.append(stack.pop())
            return popped

        if debug:
            print(f"{'Instruction':<25} | {'Op Inputs':<15} | {'Stack After'}")
            print("-" * 65)

        for inst in instructions:
            opcode = inst[0]
            parts = opcode.split('.')
            category = parts[0]

            if 'const' in opcode:
                stack.append(category)

            elif opcode == 'local.get':
                idx = inst[1]['val'] if isinstance(inst[1], dict) else inst[1]
                val_type = locals_map.get(idx, 'unknown')
                stack.append(val_type)

            elif opcode == 'local.set':
                idx = inst[1]['val'] if isinstance(inst[1], dict) else inst[1]
                vals = pop_stack(1)
                val_type = vals[0]
                if val_type != 'underflow_val':
                    locals_map[idx] = val_type
            elif opcode == 'global.get':
                stack.append('i32') # Assumed i32, needs Global Section parsing for accuracy
            elif opcode == 'call':
                func_index = inst[1]['val'] if isinstance(inst[1], dict) else inst[1]
                params, returns = self.func_signatures.get(func_index, ([], []))
                pop_stack(len(params))
                for ret_type in returns:
                    stack.append(ret_type)
            elif opcode == 'local.tee':
                val_type = stack[-1] if stack else 'unknown'
                if not stack:
                    vals = pop_stack(1)
                    stack.append(vals[0])
                    val_type = vals[0]
                idx = inst[1]['val'] if isinstance(inst[1], dict) else inst[1]
                locals_map[idx] = val_type

            elif opcode == 'drop':
                pop_stack(1)

            elif opcode == 'select':
                popped = pop_stack(3)
                result_type = popped[2] if len(popped) >= 3 else 'unknown'
                if result_type == 'underflow_val': result_type = 'unknown'
                stack.append(result_type)

            elif 'load' in opcode:
                pop_stack(1)
                stack.append(category)

            elif 'store' in opcode:
                pop_stack(2)

            elif any(x in opcode for x in ['eqz', 'eq', 'ne', 'lt', 'gt', 'le', 'ge']):
                if 'eqz' in opcode: pop_stack(1)
                else: pop_stack(2)
                stack.append('i32')

            elif any(x in opcode for x in ['add', 'sub', 'mul', 'div', 'rem', 'and', 'or', 'xor', 'shl', 'shr', 'rot']):
                pop_stack(2)
                stack.append(category)

            elif any(x in opcode for x in ['clz', 'ctz', 'popcnt', 'abs', 'neg', 'ceil', 'floor', 'sqrt']):
                pop_stack(1)
                stack.append(category)

            elif 'wrap' in opcode or 'extend' in opcode or 'convert' in opcode or 'trunc' in opcode:
                pop_stack(1)
                stack.append(category)

            elif opcode == 'if':
                pop_stack(1)
            elif opcode == 'br_if':
                pop_stack(1)
            elif opcode == 'br_table':
                pop_stack(1)

            if debug:
                print(f"{opcode:<25} | {str(stack[-3:]):<15} (top)")

        return stack, missing_count

    def analyze_wasm_ast(self, instructions, locals_types=None, initial_stack=None, locals_yingshe=None):
        """
        Parse flat instructions into AST and perform 2-pass analysis.
        Pass 1: Inference
        Pass 2: AST Generation
        """
        
        # --- Pre-pass: Apply Local Variable Mapping ---
        if locals_yingshe:
            # Normalize mapping to integer keys/values for easier lookup
            mapping = {}
            for k, v in locals_yingshe.items():
                try:
                    k_int = int(k)
                    v_int = int(v)
                    mapping[k_int] = v_int
                except ValueError:
                    pass # Ignore non-integer keys/values if any

            if mapping:
                for inst in instructions:
                    name = inst[0]
                    if name in ['local.get', 'local.set', 'local.tee']:
                        operands = inst[2]
                        # Operands are typically a list. For locals, it's usually [idx] or [{'val': idx, ...}]
                        if operands:
                            op = operands[0]
                            current_idx = -1
                            is_dict = False
                            
                            if isinstance(op, dict):
                                current_idx = op.get('val', -1)
                                is_dict = True
                            else:
                                current_idx = op
                            
                            if current_idx in mapping:
                                new_idx = mapping[current_idx]
                                if is_dict:
                                    operands[0]['val'] = new_idx
                                else:
                                    operands[0] = new_idx

        # --- Pass 1: Inference ---
        inferred_locals = locals_types.copy() if locals_types else {}
        
        class StackValue:
            def __init__(self, type_name, sources=None):
                self.type = type_name
                self.sources = sources or set()
                
        cursor = 0
        total_instrs = len(instructions)
        
        def run_inference(current_stack, stop_at_else=False):
            nonlocal cursor
            
            while cursor < total_instrs:
                inst = instructions[cursor]
                cursor += 1
                name = inst[0]
                operands = inst[2]
                
                static_pops, static_pushes = self._get_op_stack_effect(name, operands, inferred_locals)
                
                # Pop Phase
                popped_values = []
                for required_type in reversed(static_pops):
                    val = None
                    if current_stack:
                        val = current_stack.pop()
                    else:
                        val = StackValue('unknown')
                        
                    popped_values.insert(0, val)
                    
                    if required_type != 'any' and required_type != 'unknown':
                        if val.type == 'unknown' or val.type == 'any':
                            for src_local in val.sources:
                                if src_local not in inferred_locals:
                                    inferred_locals[src_local] = required_type
                                    
                # Producer Constraints
                if name == 'local.set' or name == 'local.tee':
                    idx = operands[0]['val'] if isinstance(operands[0], dict) else operands[0]
                    if popped_values:
                        val = popped_values[0]
                        if val.type != 'unknown' and val.type != 'any':
                            if idx not in inferred_locals:
                                inferred_locals[idx] = val.type
                                
                # Push Phase
                for t in static_pushes:
                    sources = set()
                    if name == 'local.get':
                        idx = operands[0]['val'] if isinstance(operands[0], dict) else operands[0]
                        sources.add(idx)
                        if idx in inferred_locals:
                            t = inferred_locals[idx]
                    elif name == 'local.tee':
                        if popped_values:
                            sources = popped_values[0].sources
                    elif name == 'select':
                        pass
                    current_stack.append(StackValue(t, sources))
                    
                # Recursion
                if name in ['block', 'loop', 'if']:
                    if name == 'if':
                        stack_snapshot = list(current_stack)
                        run_inference(current_stack, stop_at_else=True)
                        last_inst = instructions[cursor-1]
                        if last_inst[0] == 'else':
                            current_stack[:] = list(stack_snapshot)
                            run_inference(current_stack)
                    else:
                        run_inference(current_stack)
                elif name == 'end':
                    return
                elif name == 'else':
                    if stop_at_else: return
                    
        saved_cursor = cursor
        
        inference_stack = []
        if initial_stack:
            for t in initial_stack:
                inference_stack.append(StackValue(t))

        try:
            run_inference(inference_stack)
        except Exception as e:
            print(f"Inference warning: {e}")
            
        # --- Pass 2: Generation ---
        cursor = 0 
        
        def parse_sequence(current_stack, stop_at_else=False):
            nonlocal cursor
            nodes = []
            
            while cursor < total_instrs:
                inst = instructions[cursor]
                cursor += 1
                
                name = inst[0]
                opcode = inst[1]
                operands = inst[2]
                
                static_pops, static_pushes = self._get_op_stack_effect(name, operands, inferred_locals)
                
                actual_pops = []
                for required_type in reversed(static_pops):
                    if current_stack:
                        val_type = current_stack.pop()
                        if required_type == 'any' or required_type == 'unknown':
                            actual_pops.insert(0, val_type)
                        else:
                            actual_pops.insert(0, required_type)
                    else:
                        t = 'unknown' if required_type == 'any' else required_type
                        actual_pops.insert(0, t)
                
                actual_pushes = []
                if name == 'select':
                    res_type = 'unknown'
                    if len(actual_pops) >= 2:
                        val1 = actual_pops[0]
                        val2 = actual_pops[1]

                        # Fix: Unify types if one is unknown
                        if val1 in ('unknown', 'any') and val2 not in ('unknown', 'any'):
                            val1 = val2
                            actual_pops[0] = val2
                        elif val2 in ('unknown', 'any') and val1 not in ('unknown', 'any'):
                            val2 = val1
                            actual_pops[1] = val1
                        
                        if val1 not in ('unknown', 'any'):
                            res_type = val1
                        elif val2 not in ('unknown', 'any'):
                            res_type = val2
                        else:
                            res_type = val1 if val1 != 'unknown' else 'any'
                    elif len(actual_pops) >= 1:
                        res_type = actual_pops[0]
                    
                    actual_pushes.append(res_type)
                    current_stack.append(res_type)
                elif name == 'local.tee':
                    if len(actual_pops) >= 1:
                        res_type = actual_pops[0]
                        actual_pushes.append(res_type)
                        current_stack.append(res_type)
                    else:
                        actual_pushes.append('unknown')
                        current_stack.append('unknown')
                else:
                    for t in static_pushes:
                        pt = 'unknown' if t == 'any' else t
                        actual_pushes.append(pt)
                        current_stack.append(pt)
                
                node = {
                    'name': name,
                    'opcode': opcode,
                    'operands': operands,
                    'pops': actual_pops,
                    'pushes': actual_pushes,
                    'children': [],
                    'else_children': [],
                    'original_instruction': inst
                }
                
                if name in ['block', 'loop', 'if']:
                    if name == 'if':
                        stack_snapshot = list(current_stack)
                        node['children'] = parse_sequence(current_stack, stop_at_else=True)
                        last_inst = instructions[cursor-1]
                        if last_inst[0] == 'else':
                            current_stack[:] = list(stack_snapshot)
                            node['else_children'] = parse_sequence(current_stack)
                        else:
                            block_type = operands[0] if operands else 0x40
                            if block_type == 0x40:
                                current_stack[:] = list(stack_snapshot)
                    else:
                        node['children'] = parse_sequence(current_stack)
                        
                elif name == 'end':
                    return nodes
                elif name == 'else':
                    if stop_at_else:
                        return nodes
                    pass
                    
                nodes.append(node)
                
            return nodes

        generation_stack = list(initial_stack) if initial_stack else []
        return parse_sequence(generation_stack)
