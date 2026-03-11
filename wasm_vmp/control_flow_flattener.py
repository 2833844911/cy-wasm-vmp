from .utils import add_instr, pack_op
from .opaque_utils import generate_obfuscated_constant

def build_bst_dispatch(block_dict, local_pc_idx):
    """
    Builds a Binary Search Tree (BST) based dispatch mechanism for the given blocks.
    block_dict: { block_id (int): [instructions] }
    local_pc_idx: Index of the local variable holding the Virtual PC.
    """
    block_ids = sorted(block_dict.keys())
    return _build_bst_recursive(block_ids, block_dict, local_pc_idx, 0)

def _build_bst_recursive(block_ids, block_dict, local_pc_idx, depth):
    code = []
    
    if not block_ids:
        return code

    # Base case: Leaf node (Single Block)
    if len(block_ids) == 1:
        blk_id = block_ids[0]
        original_block = block_dict[blk_id]
        
        # Optimization: Strip the redundant control flow if it exists
        # In linear dispatch, blocks might look like:
        #   block
        #   br/br_if ...
        #   end
        # But here they are naturally inside nested IFs.
        # We need to preserve the instructions but fix jump depths.
        
        # We assume original_block contains:
        # [BLOCK, ..., BR/BR_IF/END, END]
        # We strip the outer BLOCK/END wrapper if present or just take content.
        # The typical VMP block structure provided by WasmVMP is raw instructions.
        
        # We need to adjust 'br' instructions because we are now deeply nested in 'if's.
        # For every level of recursion, we are inside an "if/else" block.
        # depth = recursion depth.
        
        adjusted_block = []
        
        # Heuristic: The standard VMP block usually starts with some preamble? 
        # Actually in `wasmvmp.py`, it constructs "putongcodeInfo" content.
        # Let's assume we just copy instructions but increment BR depth by `depth`.
        
        for instr in original_block:
            name = instr[0]
            opcode = instr[1]
            
            if name in ['br', 'br_if']:
                # Adjust depth
                # The operand is LEB128 encoded. We need to parse it, add `depth`, repack.
                # `instr[2]` is ops_list. `instr[2][0]` should be the depth.
                # BUT `instr` structure from `utils.py` is [name, opcode, [operands], raw_bytes].
                
                ops_list = instr[2]
                if ops_list:
                    op_item = ops_list[0]
                    if isinstance(op_item, dict):
                        original_depth = op_item['val']
                    else:
                        original_depth = op_item
                        
                    # If it's targeting the Loop (usually depth 1 or something), we add `depth`.
                    # VMP loop is usually around the whole dispatch.
                    # If we are inside 5 IFs, the loop is 5 levels further out.
                    new_depth = original_depth + depth
                    adjusted_block.append(add_instr(opcode, pack_op(new_depth)))
                else:
                    # Should not happen for br/br_if
                    adjusted_block.append(instr)
            else:
                adjusted_block.append(instr)
                
        return adjusted_block

    # Recursive Step
    mid_idx = len(block_ids) // 2
    mid_val = block_ids[mid_idx]
    
    # Split: Left < mid_val, Right >= mid_val
    # Note: block_ids[mid_idx] is the pivot.
    # We want: if PC < mid_val: Left (0..mid-1) else: Right (mid..end)
    
    left_ids = block_ids[:mid_idx]
    right_ids = block_ids[mid_idx:]
    
    # Generate Comparison: if (PC < mid_val)
    code.append(add_instr(0x20, pack_op(local_pc_idx))) # local.get PC
    
    # Use Obfuscated Constant for the Pivot Value
    code.extend(generate_obfuscated_constant(mid_val, local_pc_idx))
    
    code.append(add_instr(0x48)) # i32.lt_s (Use Signed comparison for safety, though IDs are usually positive)
    
    code.append(add_instr(0x04, 0x40)) # if (void)
    
    # Left Branch
    code.extend(_build_bst_recursive(left_ids, block_dict, local_pc_idx, depth + 1))
    
    code.append(add_instr(0x05)) # else
    
    # Right Branch
    code.extend(_build_bst_recursive(right_ids, block_dict, local_pc_idx, depth + 1))
    
    code.append(add_instr(0x0B)) # end
    
    return code
