from .utils import add_instr, pack_op

def preprocess_br_table(func_code_data):
    """
    Remove br_table instructions and replace them with a series of if/else blocks.
    This simplifies the VMP interpretation logic.
    """
    if not func_code_data or 'code' not in func_code_data:
        return

    code_list = func_code_data['code']
    new_code = []
    
    # Check if we need to add a temporary local for the br_table index
    # We'll add it only if we find a br_table
    has_br_table = False
    for instr in code_list:
        if instr[1] == 0x0E: # br_table
            has_br_table = True
            break
            
    if not has_br_table:
        return

    # Add a temp local (i32) at the end of locals
    # func_code_data['locals'] is a list of dicts: {'count': 1, 'type': 127}
    # We'll just assume we can append to the last group if it's i32, or create a new one.
    # For simplicity, create a new entry.
    # We need the index of this new local.
    
    total_locals = 0
    # Add params to count?
    # Wasm locals index space = params + locals
    # We need to know the param count to calculate absolute index.
    # Passed func_code_data usually has 'signature' attached by codec.decode_code_section
    
    param_count = 0
    if 'signature' in func_code_data and func_code_data['signature']:
         param_count = len(func_code_data['signature']['params'])
         
    for loc_group in func_code_data['locals']:
        total_locals += loc_group['count']
        
    temp_idx = param_count + total_locals
    
    # Register the new local
    # 0x7F = i32
    func_code_data['locals'].append({'count': 1, 'type': 0x7F, 'len': 1, 'type_name': 'i32'})
    
    for instr in code_list:
        opcode = instr[1]
        operands = instr[2] # list of operands
        
        if opcode != 0x0E: # Not br_table
            new_code.append(instr)
            continue
            
        # Handle br_table
        # Operands structure for 0x0E in codec.py:
        # [cnt (pack), target_0 (pack), target_1 (pack), ..., default (pack)]
        # Actually codec.py decode loop:
        #   operand_int_list.append(target_cnt)
        #   for _ in range: append(target)
        #   append(def_idx)
        
        # So: operands[0] is count
        # operands[1:-1] are targets
        # operands[-1] is default
        
        targets_count_pack = operands[0]
        targets_count = targets_count_pack['val']
        
        # All operands between [1] and [-1]
        target_packs = operands[1:-1]
        default_pack = operands[-1]
        
        # Logic: 
        # local.set $temp (pop index)
        # block $default_target_block (optional? No, br doesn't need block target if we just fall through)
        # Actually br_table is a terminator.
        
        # Re-verify Stack Effect: [index] -> br_table -> [jumps]
        # So we pop index first.
        
        new_code.append(add_instr(0x21, pack_op(temp_idx))) # local.set $temp
        
        # Generate IF checks for each index
        for i, target_pack in enumerate(target_packs):
            target_depth = target_pack['val']
            
            # Check: if ($temp == i) br (target_depth + 1)
            # Why +1? Because we wrap this in an 'if ... end' block.
            
            new_code.append(add_instr(0x20, pack_op(temp_idx))) # local.get $temp
            new_code.append(add_instr(0x41, pack_op(i)))        # i32.const i
            new_code.append(add_instr(0x46))                  # i32.eq
            
            new_code.append(add_instr(0x04, 0x40))            # if (void)
            new_code.append(add_instr(0x0C, pack_op(target_depth + 1))) # br (depth+1)
            new_code.append(add_instr(0x0B))                  # end
            
        # Default Case
        # If none matched, we fall through to here.
        # Just branch to default target.
        # No 'if' wrapper here, so depth is ORIGINAL depth.
        default_depth = default_pack['val']
        new_code.append(add_instr(0x0C, pack_op(default_depth))) # br default
        
    func_code_data['code'] = new_code
    print(f"   [Preprocessor] Replaced br_table in function {func_code_data.get('index', '?')}")
