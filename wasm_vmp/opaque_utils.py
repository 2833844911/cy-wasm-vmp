import random
from .utils import add_instr, pack_op

def to_s32(val):
    """
    Converts a Python integer (which might be large positive like 0xFFFFFFFF)
    into a signed 32-bit integer range (-2^31 to 2^31-1).
    This ensures write_leb128_signed generates valid 5-byte s32 sequences.
    """
    val = val & 0xFFFFFFFF
    if val > 0x7FFFFFFF:
        val -= 0x100000000
    return val

def _emit_mixed_const(target_val, local_pc_idx):
    """
    Emits code to generate `target_val` on the stack using a local variable (PC)
    to avoid pure numeric constants.
    Pattern: (PC - PC) + target_val
             or (PC ^ PC) + target_val
             or (PC * 0) + target_val
    """
    code = []
    
    if local_pc_idx is None:
        # Fallback if no local available
        code.append(add_instr(0x41, pack_op(to_s32(target_val))))
        return code

    strategy = random.choice(['sub', 'xor', 'mul'])
    
    if strategy == 'sub':
        # (PC - PC) + K
        code.append(add_instr(0x20, pack_op(local_pc_idx))) # PC
        code.append(add_instr(0x20, pack_op(local_pc_idx))) # PC
        code.append(add_instr(0x6B)) # sub (0)
        code.append(add_instr(0x41, pack_op(to_s32(target_val)))) # K
        code.append(add_instr(0x6A)) # add
        
    elif strategy == 'xor':
        # (PC ^ PC) + K
        code.append(add_instr(0x20, pack_op(local_pc_idx))) # PC
        code.append(add_instr(0x20, pack_op(local_pc_idx))) # PC
        code.append(add_instr(0x73)) # xor (0)
        code.append(add_instr(0x41, pack_op(to_s32(target_val)))) # K
        code.append(add_instr(0x6A)) # add
        
    elif strategy == 'mul':
        # (PC * 0) + K
        # Maybe slightly riskier if PC is huge and overflows? Mul by 0 is always 0.
        code.append(add_instr(0x20, pack_op(local_pc_idx))) # PC
        code.append(add_instr(0x41, pack_op(0))) # 0
        code.append(add_instr(0x6C)) # mul (0)
        code.append(add_instr(0x41, pack_op(to_s32(target_val)))) # K
        code.append(add_instr(0x6A)) # add

    return code

def generate_obfuscated_constant(target_val, local_pc_idx=None):
    """
    Generates a sequence of instructions that results in `target_val` on the stack.
    Choosing between:
    1. Linear Complex Chain (Variable Splitting / Arithmetic).
    2. Opaque Branching (True Path = Correct, False Path = Incorrect).
    """
    # 50% chance to use Branching if PC is available (needed for good predicates)
    if local_pc_idx is not None and random.random() < 0.5:
        return _generate_branching_constant(target_val, local_pc_idx)
    else:
        return _generate_linear_constant(target_val, local_pc_idx)

def _generate_branching_constant(target_val, local_pc_idx):
    """
    if (Always True Predicate) { Correct } else { Corrupt }
    """
    code = []
    
    # 1. Generate Always True Predicate (using PC)
    #    Example: (PC * (PC + 1)) % 2 == 0
    #    We use _emit_mixed_const for literals to avoid naked const 1, 2.
    
    # Push PC
    code.append(add_instr(0x20, pack_op(local_pc_idx))) # local.get PC
    # Push PC
    code.append(add_instr(0x20, pack_op(local_pc_idx))) # local.get PC
    # Add 1
    code.extend(_emit_mixed_const(1, local_pc_idx)) # 1 (Mixed)
    code.append(add_instr(0x6A)) # add
    # Mul
    code.append(add_instr(0x6C)) # mul
    # Push 2
    code.extend(_emit_mixed_const(2, local_pc_idx)) # 2 (Mixed)
    # Rem U
    code.append(add_instr(0x6F)) # rem_u
    # Push 0
    code.extend(_emit_mixed_const(0, local_pc_idx)) # 0 (Mixed)
    # Check Equal (True)
    code.append(add_instr(0x46)) # eq
    
    # 2. IF (True)
    code.append(add_instr(0x04, 0x7F)) # if i32 (returns i32)
    
    # --- TRUE PATH (Correct) ---
    code.extend(_generate_linear_constant(target_val, local_pc_idx))
    
    # --- ELSE (False Path - Corrupt) ---
    code.append(add_instr(0x05)) # else
    
    # Generate Corrupt constant (Target + Random Error)
    fake_target = (target_val + random.randint(1, 100)) & 0xFFFFFFFF
    code.extend(_generate_linear_constant(fake_target, local_pc_idx))
    
    code.append(add_instr(0x0B)) # end
    
    return code

def _generate_linear_constant(target_val, local_pc_idx=None):
    """
    Linear generation. Uses mixed constants for seed and operands.
    """
    code = []
    
    use_pc_masking = (local_pc_idx is not None) and (random.random() < 0.6)
    
    # 1. Initialization
    current_val = random.randint(0, 10000)
    # Use Mixed Const for Seed
    code.extend(_emit_mixed_const(current_val, local_pc_idx))
    
    if use_pc_masking:
        code.append(add_instr(0x20, pack_op(local_pc_idx))) 
        code.append(add_instr(0x6A)) # i32.add
        pass

    # 2. Random Operations
    steps = random.randint(2, 5)
    
    if use_pc_masking:
        # PC Masking Logic - Slightly different structure (loop already safe?)
        # Let's verify loop. Original code had unconditional push here too?
        # In Step 296 dump, `if use_pc_masking` block had uncoditional push.
        # But `else` block (standard complex) was the one I refactored.
        # Let's fix use_pc_masking block too to be safe/consistent, OR leave it if it works.
        # Wait, if `if use_pc_masking` block uses `_emit_mixed_const(operand)`, it pushes operand.
        # Then `add`/`sub` consumes. It looks like `if use_pc_masking` block was ALREADY correctly doing one push per op?
        # Step 296 dump for `if use_pc_masking`:
        # `code.extend(_emit_mixed_const(operand, local_pc_idx))`
        # `if op_type == 'add': ... append(add) ...`
        # This seems correct (Push 1, Consumes 2? No.)
        # If we have [Val].
        # Push Operand [Val, Op].
        # Add [Val+Op].
        # So YES, the unconditional push IS CORRECT for `add`/`sub`.
        # The problem in `else` block was `and` logic doing EXTRA push.
        
        # So `if use_pc_masking` block is fine.
        for _ in range(steps):
             if random.random() < 0.2:
                 code.extend(generate_opaque_predicate_block(local_pc_idx))
                 
             op_type = random.choice(['add', 'sub'])
             operand = random.randint(1, 1000)
             
             # Operand must be mixed
             code.extend(_emit_mixed_const(operand, local_pc_idx))
             
             if op_type == 'add':
                 code.append(add_instr(0x6A)) 
                 current_val = (current_val + operand) & 0xFFFFFFFF
             elif op_type == 'sub':
                 code.append(add_instr(0x6B))
                 current_val = (current_val - operand) & 0xFFFFFFFF
        
        # Unmask
        code.append(add_instr(0x20, pack_op(local_pc_idx)))
        code.append(add_instr(0x6B)) # i32.sub
        
    else:
        # Standard complex chain
        extended_ops = ['add', 'sub', 'xor', 'mul', 'shl', 'and', 'or']
        for _ in range(steps):
            if local_pc_idx is not None and random.random() < 0.2:
                 code.extend(generate_opaque_predicate_block(local_pc_idx))

            op_type = random.choice(extended_ops)
            operand = random.randint(1, 1000)
            
            # NO Unconditional Push here. We do it inside branches.
            
            if op_type == 'add':
                code.extend(_emit_mixed_const(operand, local_pc_idx))
                code.append(add_instr(0x6A)) # i32.add
                current_val = (current_val + operand) & 0xFFFFFFFF
            elif op_type == 'sub':
                code.extend(_emit_mixed_const(operand, local_pc_idx))
                code.append(add_instr(0x6B)) # i32.sub
                current_val = (current_val - operand) & 0xFFFFFFFF
            elif op_type == 'xor':
                code.extend(_emit_mixed_const(operand, local_pc_idx))
                code.append(add_instr(0x73)) # i32.xor
                current_val = current_val ^ operand
            elif op_type == 'mul':
                code.extend(_emit_mixed_const(operand, local_pc_idx))
                code.append(add_instr(0x6C)) # i32.mul
                current_val = (current_val * operand) & 0xFFFFFFFF
            elif op_type == 'shl':
                shift_amt = operand % 32
                code.extend(_emit_mixed_const(shift_amt, local_pc_idx))
                code.append(add_instr(0x74)) # i32.shl
                current_val = (current_val << shift_amt) & 0xFFFFFFFF
            elif op_type == 'and':
                operand = operand | 0x80000000
                code.extend(_emit_mixed_const(operand, local_pc_idx))
                code.append(add_instr(0x71)) # i32.and
                current_val = current_val & operand
            elif op_type == 'or':
                code.extend(_emit_mixed_const(operand, local_pc_idx))
                code.append(add_instr(0x72)) # i32.or
                current_val = current_val | operand

    # 3. Final Fixup
    diff = (target_val - current_val) & 0xFFFFFFFF
    
    code.extend(_emit_mixed_const(diff, local_pc_idx))
    code.append(add_instr(0x6A)) # i32.add
    
    return code

def generate_opaque_predicate_block(local_pc_idx=None):
    """
    Generates an Opaque Predicate block (Always False) with Fake Math.
    """
    code = []
    
    # Strategy: (x * (x+1)) % 2 != 0  (Always False)
    # x can be PC or a random constant or mixed.
    
    use_pc = (local_pc_idx is not None)
    
    # 1. Push x
    if use_pc:
        code.append(add_instr(0x20, pack_op(local_pc_idx))) 
    else:
        code.extend(_emit_mixed_const(random.randint(100,5000), local_pc_idx))

    # 2. Push x again
    if use_pc:
        code.append(add_instr(0x20, pack_op(local_pc_idx)))
    else:
        # Re-emit random for simplicity in unreachable (or dup if we had it)
        # Using Mixed const again
        code.extend(_emit_mixed_const(random.randint(100,5000), local_pc_idx))

    # 3. Calculate (x+1)
    code.extend(_emit_mixed_const(1, local_pc_idx))
    code.append(add_instr(0x6A)) # add
    
    # 4. Multiply x * (x+1)
    code.append(add_instr(0x6C)) # mul
    
    # 5. Mod 2
    code.extend(_emit_mixed_const(2, local_pc_idx))
    code.append(add_instr(0x6F)) # rem_u
    
    # 6. Check != 0
    code.extend(_emit_mixed_const(0, local_pc_idx))
    code.append(add_instr(0x47)) # ne
    
    # 7. if (Always False)
    code.append(add_instr(0x04, 0x40)) # if void
    
    # 8. Junk Code (Realistic)
    code.extend(generate_junk_code(local_pc_idx))
    
    code.append(add_instr(0x0B)) # end
    
    return code

def generate_junk_code(local_pc_idx=None):
    """
    Generates junk code.
    """
    code = []
    
    # Length of junk sequence
    seq_len = random.randint(2, 5)
    
    for _ in range(seq_len):
        # Push a operand
        if local_pc_idx is not None and random.random() < 0.5:
            code.append(add_instr(0x20, pack_op(local_pc_idx))) 
        else:
            # Emit mixed const for junk too
            code.extend(_emit_mixed_const(random.randint(0,9999), local_pc_idx))
            
    # Do some operations to consume them
    # We pushed `seq_len` items. We need to reduce to 0.
    
    current_stack_height = seq_len
    
    while current_stack_height > 0:
        if current_stack_height >= 2:
            op = random.choice(['add', 'sub', 'mul', 'xor', 'and', 'or', 'drop_only'])
            if op == 'drop_only':
                code.append(add_instr(0x1A)) # drop
                current_stack_height -= 1
            else:
                # Binop
                if op == 'add': code.append(add_instr(0x6A))
                elif op == 'sub': code.append(add_instr(0x6B))
                elif op == 'mul': code.append(add_instr(0x6C))
                elif op == 'xor': code.append(add_instr(0x73))
                elif op == 'and': code.append(add_instr(0x71))
                elif op == 'or': code.append(add_instr(0x72))
                # Binop consumes 2, pushes 1 -> net -1
                current_stack_height -= 1
        else:
            # Height 1, must drop
            code.append(add_instr(0x1A))
            current_stack_height -= 1
            
    return code

def generate_always_true_check(local_pc_idx):
    """
    Generates an Always True condition for virtual branching.
    Result on stack: 1 (True)
    Math: (PC * (PC + 1)) % 2 == 0
    """
    code = []
    
    # 1. Push PC
    code.append(add_instr(0x20, pack_op(local_pc_idx))) 
    
    # 2. Push PC (for x+1)
    code.append(add_instr(0x20, pack_op(local_pc_idx))) 
    
    # 3. Add 1 -> PC+1
    code.extend(_emit_mixed_const(1, local_pc_idx))
    code.append(add_instr(0x6A)) # add
    
    # 4. Multiply
    code.append(add_instr(0x6C)) # mul
    
    # 5. Mod 2
    code.extend(_emit_mixed_const(2, local_pc_idx))
    code.append(add_instr(0x6F)) # rem_u
    
    # 6. Check == 0 (True)
    code.extend(_emit_mixed_const(0, local_pc_idx))
    code.append(add_instr(0x46)) # eq
    
    return code

def generate_fake_vmp_block(sp_local_idx, local_pc_idx=None):
    """
    Generates fake VMP logic (Stack Machine Operations) for the False branch.
    Mimics: SP access, Load, arithmetic, Store.
    """
    code = []
    
    # Sequence length
    seq_len = random.randint(3, 6)
    
    # Helper to push an address based on SP
    def _push_sp_addr():
        code.append(add_instr(0x20, pack_op(sp_local_idx))) # local.get SP
        offset = random.randint(0, 64) * 4 # Random aligned offset
        code.extend(_emit_mixed_const(offset, local_pc_idx))
        code.append(add_instr(0x6A)) # i32.add (SP + Offset)

    for _ in range(seq_len):
        op_type = random.choice(['load_calc', 'store', 'update_sp'])
        
        if op_type == 'load_calc':
            # Load something, do math, drop
            _push_sp_addr()
            # i32.load (align=2, offset=0)
            code.append(add_instr(0x28, [pack_op(2), pack_op(0)])) 
            
            # Math
            code.extend(_emit_mixed_const(random.randint(1, 100), local_pc_idx))
            code.append(add_instr(0x6A)) # add
            code.append(add_instr(0x1A)) # drop
            
        elif op_type == 'store':
            # Store random value to stack (dangerous if real, but this is dead code)
            _push_sp_addr()
            code.extend(_emit_mixed_const(random.randint(1, 9999), local_pc_idx)) # Value
            # i32.store (align=2, offset=0)
            code.append(add_instr(0x36, [pack_op(2), pack_op(0)])) 
            
        elif op_type == 'update_sp':
            # local.set SP (fake update)
            code.append(add_instr(0x20, pack_op(sp_local_idx)))
            code.extend(_emit_mixed_const(4, local_pc_idx))
            code.append(add_instr(0x6A)) # add
            code.append(add_instr(0x21, pack_op(sp_local_idx))) # local.set SP

    return code
