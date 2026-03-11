import random
from symbol import continue_stmt

from .consts import WASM_OPCODES

class InstructionExpander:
    def __init__(self):
        self.OPCODE_NAME_TO_ID = {v: k for k, v in WASM_OPCODES.items()}
        
    def _make_instr(self, name, operands_list=None):
        opcode = self.OPCODE_NAME_TO_ID.get(name)
        if opcode is None:
            raise ValueError(f"Unknown opcode: {name}")
            
        packed_operands = []
        if operands_list:
            for op in operands_list:
                if isinstance(op, dict):
                    packed_operands.append(op)
                else:
                    packed_operands.append({'val': op, 'len': 0})
                    
        return [name, opcode, packed_operands, b'']

    def process_function(self, func):
        code = func['code']
        
        needed_i32 = False
        needed_i64 = False
        
        # Scan for opcodes we handle
        # i32.xor(0x73), i64.xor(0x85)
        # i32.mul(0x6C), i64.mul(0x7E)
        
        for instr in code:
            op = instr[1]
            if op in [0x6A, 0x6B, 0x6C, 0x6D, 0x6E, 0x6F, 0x70, 0x71, 0x72, 0x73]: needed_i32 = True
            elif op in [0x7C, 0x7D, 0x7E, 0x7F, 0x80, 0x81, 0x82, 0x83, 0x84, 0x85]: needed_i64 = True
                
        if not (needed_i32 or needed_i64):
            return
        if random.random() < 0.7:
            return

        # 1. Identify existing locals (same as before)
        params = func['signature']['params']
        existing_locals_i32 = []
        existing_locals_i64 = []
        
        current_idx = 0
        for p_type in params:
            if p_type == 'i32': existing_locals_i32.append(current_idx)
            elif p_type == 'i64': existing_locals_i64.append(current_idx)
            current_idx += 1
        for l in func['locals']:
            count = l['count']
            t_name = l['type_name']
            for _ in range(count):
                if t_name == 'i32': existing_locals_i32.append(current_idx)
                elif t_name == 'i64': existing_locals_i64.append(current_idx)
                current_idx += 1
        
        def alloc_locals(count, type_name):
            t_code = 0x7F if type_name == 'i32' else 0x7E
            start_l = current_idx
            func['locals'].append({
                'count': count,
                'type': t_code,
                'type_name': type_name,
                'len': 1
            })
            return [start_l + i for i in range(count)]

        # Determine Strategy for i32
        strategy_i32 = None 
        if needed_i32:
            available = len(existing_locals_i32)
            if available >= 2:
                # Reuse 2, Alloc 2 Swaps (S1, S2)
                op_locs = existing_locals_i32[:2]
                swaps = alloc_locals(2, 'i32')
                current_idx += 2
                strategy_i32 = ('reuse_2', op_locs, swaps)
            elif available == 1:
                # Reuse 1, Alloc 1 op, 1 swap
                op_reuse = existing_locals_i32[0]
                new_all = alloc_locals(2, 'i32')
                current_idx += 2
                op_locs = [op_reuse, new_all[0]]
                strategy_i32 = ('reuse_1', op_locs, new_all[1])
            else:
                # Alloc 2 op
                op_locs = alloc_locals(2, 'i32')
                current_idx += 2
                strategy_i32 = ('new_2', op_locs, None)

        # Determine Strategy for i64
        strategy_i64 = None 
        if needed_i64:
            available = len(existing_locals_i64)
            if available >= 2:
                op_locs = existing_locals_i64[:2]
                swaps = alloc_locals(2, 'i64')
                current_idx += 2
                strategy_i64 = ('reuse_2', op_locs, swaps)
            elif available == 1:
                op_reuse = existing_locals_i64[0]
                new_all = alloc_locals(2, 'i64')
                current_idx += 2
                op_locs = [op_reuse, new_all[0]]
                strategy_i64 = ('reuse_1', op_locs, new_all[1])
            else:
                op_locs = alloc_locals(2, 'i64')
                current_idx += 2
                strategy_i64 = ('new_2', op_locs, None)
        
        # 4. Process Code
        new_code = []
        
        # Helper to get strategy by type
        def get_strat(is_64): return strategy_i64 if is_64 else strategy_i32

        for instr in code:
            opcode = instr[1]
            
            # Division Opcodes
            # i32.div_s=0x6D, i32.div_u=0x6E
            # i64.div_s=0x7F, i64.div_u=0x80
            if opcode in [0x6D, 0x6E, 0x7F, 0x80]: 
                is_64 = opcode in [0x7F, 0x80]
                is_signed = opcode in [0x6D, 0x7F]
                
                # Check for constant divisor in new_code
                prev_const = None
                if new_code:
                    last_op = new_code[-1]
                    # i32.const=0x41, i64.const=0x42
                    if not is_64 and last_op[1] == 0x41:
                        prev_const = last_op[2][0]['val']
                    elif is_64 and last_op[1] == 0x42:
                        prev_const = last_op[2][0]['val']
                
                if prev_const is not None:
                    # Constant Divisor Strategy
                    new_code.pop() # Remove the const instruction
                    new_code.extend(self._expand_div_const(prev_const, is_signed, is_64, alloc_locals))
                else:
                    # Variable Divisor Strategy
                    strat = get_strat(is_64)
                    if not strat:
                        # If strat is None (e.g. alloc failed or skipped), just keep original
                        new_code.append(instr)
                    else:
                        new_code.extend(self._expand_binary_with_strategy(strat, 'div', is_64, is_signed=is_signed, alloc_func=alloc_locals))

            # elif opcode in [0x74, 0x86]: # i32.shl, i64.shl
            #     is_64 = (opcode == 0x86)
            #
            #     # Check for constant shift amount
            #     prev_const = None
            #     if new_code:
            #         last_op = new_code[-1]
            #         if not is_64 and last_op[1] == 0x41:
            #             prev_const = last_op[2][0]['val']
            #         elif is_64 and last_op[1] == 0x42:
            #             prev_const = last_op[2][0]['val']
            #
            #     strat = get_strat(is_64)
            #
            #     if not strat:
            #         new_code.append(instr)
            #     elif prev_const is not None:
            #          # Mask the shift amount to emulate WASM semantics
            #          orig_const = prev_const
            #          if is_64: prev_const &= 63
            #          else: prev_const &= 31
            #
            #          new_code.pop() # Remove const
            #          # 1. Addition Chain (Small const)
            #          if prev_const <= 3:
            #              new_code.extend(self._gen_shl_add_chain(strat, prev_const, is_64, alloc_locals))
            #          # 2. Multiplication (Large const)
            #          else:
            #              new_code.extend(self._gen_shl_as_mul(strat, prev_const, is_64, alloc_locals))
            #     else:
            #         # 3. Variable Loop
            #         new_code.extend(self._gen_shl_loop(strat, is_64, alloc_locals))

            elif opcode in [0x71, 0x83]: # i32.and, i64.and
                is_64 = (opcode == 0x83)
                strat = get_strat(is_64)
                if not strat:
                    new_code.append(instr)
                else:
                    new_code.extend(self._expand_binary_with_strategy(strat, 'and', is_64, is_signed=False, alloc_func=alloc_locals))

            elif opcode in [0x72, 0x84]: # i32.or, i64.or
                is_64 = (opcode == 0x84)
                strat = get_strat(is_64)
                if not strat:
                    new_code.append(instr)
                else:
                    new_code.extend(self._expand_binary_with_strategy(strat, 'or', is_64, is_signed=False, alloc_func=alloc_locals))

            elif opcode in [0x6B, 0x7D]: # i32.sub, i64.sub
                is_64 = (opcode == 0x7D)
                strat = get_strat(is_64)
                if not strat:
                    new_code.append(instr)
                else:
                    new_code.extend(self._expand_binary_with_strategy(strat, 'sub', is_64, is_signed=True, alloc_func=alloc_locals))

            elif opcode in [0x6A, 0x7C]: # i32.add, i64.add
                is_64 = (opcode == 0x7C)
                strat = get_strat(is_64)
                if not strat:
                    new_code.append(instr)
                else:
                    new_code.extend(self._expand_binary_with_strategy(strat, 'add', is_64, is_signed=False, alloc_func=alloc_locals))

            elif opcode == 0x73: # i32.xor
                strat = get_strat(False)
                if not strat: new_code.append(instr)
                else: new_code.extend(self._expand_binary_with_strategy(strat, 'xor', is_64=False))
            elif opcode == 0x85: # i64.xor
                strat = get_strat(True)
                if not strat: new_code.append(instr)
                else: new_code.extend(self._expand_binary_with_strategy(strat, 'xor', is_64=True))
            elif opcode == 0x6C: # i32.mul
                strat = get_strat(False)
                if not strat: new_code.append(instr)
                else: new_code.extend(self._expand_binary_with_strategy(strat, 'mul', is_64=False))
            elif opcode == 0x7E: # i64.mul
                strat = get_strat(True)
                if not strat: new_code.append(instr)
                else: new_code.extend(self._expand_binary_with_strategy(strat, 'mul', is_64=True))
            else:
                new_code.append(instr)
        
        func['code'] = new_code
    
    # ... existing _gen_shl* methods ...
    
    def _gen_add_seq(self, loc_a, loc_b, swap_loc, suffix, alloc_func):
        def instr(name, *args): return self._make_instr(name, args if args else None)
        def op(name): return self._make_instr(f"{suffix}.{name}")
        def const(val): return self._make_instr(f"{suffix}.const", [val])
        def get(l): return self._make_instr("local.get", [l])
        def set_l(l): return self._make_instr("local.set", [l])
        
        # Strategy 1: Negated Subtraction
        # a + b = a - (~b) - 1
        # ~b = b ^ -1
        def f_NegSub():
            return [
                get(loc_a),
                get(loc_b), const(-1), op("xor"), # ~b
                op("sub"), # a - ~b
                const(1), op("sub") # - 1
            ]
            
        # Strategy 2: MBA (Or + And)
        # a + b = (a | b) + (a & b)
        # We need an 'add' for this. To avoid infinite recursion, 
        # we can recursively use f_NegSub for the inner add!
        def f_MBA():
            # (a | b)
            seq = [get(loc_a), get(loc_b), op("or")]
            # (a & b)
            seq.extend([get(loc_a), get(loc_b), op("and")])
            # Add them using NegSub logic inline:
            # x + y = x - ~y - 1
            # Stack top is y, below is x.
            seq.append(const(-1))
            seq.append(op("xor")) # ~y
            seq.append(op("sub")) # x - ~y
            seq.append(const(1))
            seq.append(op("sub"))
            return seq
            
        # Strategy 3: Hardware Loop (Carry)
        # while b != 0:
        #   carry = (a & b) << 1
        #   a = a ^ b
        #   b = carry
        # Use swap_loc as carry temp? 
        # Actually we have loc_a, loc_b. We need a temp for carry because a is updated.
        # If reuse_2, we have swap_loc available?
        # Check calling convention: swap_loc is passed.
        # If None (new_2), we might need to alloc?
        # But wait, alloc_func is passed!
        def f_HardwareLoop():
            temp_carry = swap_loc
            if temp_carry is None:
                # Alloc new temp if not provided
                temp_carry = alloc_func(1, suffix)[0]
                
            seq = []
            # Loop
            seq.append(instr("block", 0x40))
            seq.append(instr("loop", 0x40))
            
            # check b == 0
            seq.append(get(loc_b))
            seq.append(op("eqz"))
            seq.append(instr("br_if", 1)) 
            
            # carry = (a & b) << 1
            seq.append(get(loc_a))
            seq.append(get(loc_b))
            seq.append(op("and"))
            seq.append(const(1))
            seq.append(op("shl"))
            seq.append(set_l(temp_carry))
            
            # a = a ^ b
            seq.append(get(loc_a))
            seq.append(get(loc_b))
            seq.append(op("xor"))
            seq.append(set_l(loc_a))
            
            # b = carry
            seq.append(get(temp_carry))
            seq.append(set_l(loc_b))
            
            seq.append(instr("br", 0))
            seq.append(instr("end")); seq.append(instr("end"))
            
            seq.append(get(loc_a))
            return seq

        choices = [f_NegSub, f_MBA, f_HardwareLoop]
        # Weighted choice?
        r = random.random()
        if r < 0.5: return f_NegSub()
        elif r < 0.8: return f_MBA()
        else: return f_HardwareLoop()


    def _gen_sub_seq(self, loc_a, loc_b, swap_loc, suffix, alloc_func):
        def instr(name, *args): return self._make_instr(name, args if args else None)
        def op(name): return self._make_instr(f"{suffix}.{name}")
        def const(val): return self._make_instr(f"{suffix}.const", [val])
        def get(l): return self._make_instr("local.get", [l])
        def set_l(l): return self._make_instr("local.set", [l])

        # Strategy 1: Adder Conversion (TO_ADD)
        # a - b = a + ~b + 1
        def f_ToAdd():
            return [
                get(loc_a),
                get(loc_b), const(-1), op("xor"), # ~b
                op("add"),                        # a + ~b
                const(1), op("add")               # + 1
            ]

        # Strategy 2: Set Theory Difference (SET_THEORY)
        # a - b = (a & ~b) - (~a & b)
        # Uses 'sub' recursively (but instruction level, so safe from infinite expansion in this pass)
        def f_SetTheory():
            seq = []
            # Part 1: a & ~b
            seq.append(get(loc_a))
            seq.append(get(loc_b))
            seq.append(const(-1)); seq.append(op("xor")) # ~b
            seq.append(op("and"))
            
            # Part 2: ~a & b
            seq.append(get(loc_a))
            seq.append(const(-1)); seq.append(op("xor")) # ~a
            seq.append(get(loc_b))
            seq.append(op("and"))
            
            # Sub
            seq.append(op("sub"))
            return seq

        # Strategy 3: Hardware Borrower Loop (BORROW_LOOP)
        # while b != 0:
        #   borrow = (~a & b) << 1
        #   a = a ^ b
        #   b = borrow
        def f_BorrowLoop():
            temp_borrow = swap_loc
            if temp_borrow is None:
                temp_borrow = alloc_func(1, suffix)[0]

            seq = []
            seq.append(instr("block", 0x40))
            seq.append(instr("loop", 0x40))

            # if b == 0 break
            seq.append(get(loc_b))
            seq.append(op("eqz"))
            seq.append(instr("br_if", 1))

            # borrow = (~a & b) << 1
            seq.append(get(loc_a))
            seq.append(const(-1)); seq.append(op("xor")) # ~a
            seq.append(get(loc_b))
            seq.append(op("and"))
            seq.append(const(1)); seq.append(op("shl"))
            seq.append(set_l(temp_borrow))

            # a = a ^ b
            seq.append(get(loc_a))
            seq.append(get(loc_b))
            seq.append(op("xor"))
            seq.append(set_l(loc_a))

            # b = borrow
            seq.append(get(temp_borrow))
            seq.append(set_l(loc_b))

            seq.append(instr("br", 0))
            seq.append(instr("end")); seq.append(instr("end"))

            seq.append(get(loc_a))
            return seq

        # Strategy 4: MBA Not (MBA_NOT)
        # a - b = ~(~a + b)
        def f_MbaNot():
            return [
                get(loc_a), const(-1), op("xor"), # ~a
                get(loc_b), op("add"),            # ~a + b
                const(-1), op("xor")              # ~(...)
            ]

        choices = ['TO_ADD', 'SET_THEORY', 'BORROW_LOOP', 'MBA_NOT']
        # Weighted: TO_ADD is preferred (matches user suggestion)
        # 40% TO_ADD, 20% others
        r = random.random()
        if r < 0.4: return f_ToAdd()
        elif r < 0.6: return f_SetTheory()
        elif r < 0.8: return f_BorrowLoop()
        else: return f_MbaNot()

    def _gen_and_seq(self, loc_a, loc_b, swap_loc, suffix, alloc_func):
        def instr(name, *args): return self._make_instr(name, args if args else None)
        def op(name): return self._make_instr(f"{suffix}.{name}")
        def const(val): return self._make_instr(f"{suffix}.const", [val])
        def get(l): return self._make_instr("local.get", [l])
        
        # Strategy 1: De Morgan (DE_MORGAN)
        # a & b = ~(~a | ~b)
        def f_DeMorgan():
            return [
                get(loc_a), const(-1), op("xor"), # ~a
                get(loc_b), const(-1), op("xor"), # ~b
                op("or"),
                const(-1), op("xor")
            ]

        # Strategy 2: Set Theory XOR (SET_XOR)
        # a & b = (a | b) ^ (a ^ b)
        def f_SetXor():
            return [
                get(loc_a), get(loc_b), op("or"),
                get(loc_a), get(loc_b), op("xor"),
                op("xor")
            ]

        # Strategy 3: MBA Add (MBA_ADD)
        # a & b = (a + b) - (a | b)
        def f_MbaAdd():
            return [
                get(loc_a), get(loc_b), op("add"),
                get(loc_a), get(loc_b), op("or"),
                op("sub")
            ]

        # Strategy 4: MBA Carry (MBA_CARRY)
        # a & b = ((a + b) - (a ^ b)) >> 1
        def f_MbaCarry():
            return [
                get(loc_a), get(loc_b), op("add"),
                get(loc_a), get(loc_b), op("xor"),
                op("sub"),
                const(1), op("shr_u")
            ]
            
        choices = ['DE_MORGAN', 'SET_XOR', 'MBA_ADD', 'MBA_CARRY']
        # Preferred: SET_XOR (Strategy 2) and MBA (Strategy 3/4)
        r = random.random()
        if r < 0.2: return f_DeMorgan()
        elif r < 0.6: return f_SetXor() # 40%
        elif r < 0.8: return f_MbaAdd() # 20%
        else: return f_MbaCarry()       # 20%

    def _gen_or_seq(self, loc_a, loc_b, swap_loc, suffix, alloc_func):
        def instr(name, *args): return self._make_instr(name, args if args else None)
        def op(name): return self._make_instr(f"{suffix}.{name}")
        def const(val): return self._make_instr(f"{suffix}.const", [val])
        def get(l): return self._make_instr("local.get", [l])

        # Strategy 1: Arithmetic Mixed (ARITH_SUB)
        # a | b = (a + b) - (a & b)
        def f_ArithSub():
            return [
                get(loc_a), get(loc_b), op("add"),
                get(loc_a), get(loc_b), op("and"),
                op("sub")
            ]
        
        # Strategy 2: Logic XOR (LOGIC_XOR)
        # a | b = (a ^ b) ^ (a & b)
        def f_LogicXor():
            return [
                get(loc_a), get(loc_b), op("xor"),
                get(loc_a), get(loc_b), op("and"),
                op("xor")
            ]

        # Strategy 3: Mixed Add (MIXED_ADD)
        # a | b = (a ^ b) + (a & b)
        def f_MixedAdd():
            return [
                get(loc_a), get(loc_b), op("xor"),
                get(loc_a), get(loc_b), op("and"),
                op("add")
            ]

        # Strategy 4: De Morgan (DE_MORGAN)
        # a | b = ~(~a & ~b)
        def f_DeMorgan():
            return [
                get(loc_a), const(-1), op("xor"), # ~a
                get(loc_b), const(-1), op("xor"), # ~b
                op("and"),
                const(-1), op("xor")
            ]
        
        choices = ['ARITH_SUB', 'LOGIC_XOR', 'MIXED_ADD', 'DE_MORGAN']
        r = random.random()
        # Weighted: ARITH_SUB (40%), LOGIC_XOR (30%), Others (30%)
        if r < 0.4: return f_ArithSub()
        elif r < 0.7: return f_LogicXor()
        elif r < 0.9: return f_MixedAdd()
        else: return f_DeMorgan()


    def _gen_shl_add_chain(self, strategy, shift_n, is_64, alloc_func):
        if shift_n == 0: return [] 
        # Stack: [val]
        # We need to double 'val' shift_n times.
        # Strategy: Use binary calc strategy with 'add' repeatedly?
        # Efficient way: 
        #   reuse_2: Op A, Op B. 
        #   But here we effectively have 1 operand 'val'.
        #   We can treat it as 'add val, val'.
        
        # Simplified approach: Just use standard arithmetic op expansion?
        # But 'add' is not yet expanded.
        # And we want to chain them. 
        # Let's implement specific chain logic.
        
        suffix = "i64" if is_64 else "i32"
        seq = []
        
        # We need to manipulate 'val' on stack.
        # For shift=1: [val] -> [val, val] -> add -> [res]
        # For shift=2: [res] -> [res, res] -> add -> [res2]
        
        # If we just emit 'add' instructions, they are plain.
        # User wants obfuscation.
        # We can use our _expand_binary_with_strategy(..., 'add') logic?
        # But I haven't implemented 'add' expansion yet. 
        # User prompt mentions: "confuse add with MBA". 
        # Since I don't have 'add' expansion, I will implement a basic `add` sequence 
        # but maybe wrap it in a local set/get to look busy if I had time.
        # For now, simplest chain:
        
        for _ in range(shift_n):
            # [val] -> [val, val]
            # To duplicate top of stack without pop? 'local.tee' if we have a local?
            # Or just assumes we have a strategy.
            # Actually, let's use the local reuse strategy to load 'val' into a local, 
            # then add it to itself.
            
            # Since shift is small (1-3), expanding huge blocks is fine (instruction bloat).
            # We can treat "val << 1" as "val + val".
            # We need 2 operands on stack for "val + val".
            # Currently stack has [val].
            # We need [val, val].
            
            # Helper to dupe stack top using a temp local
            # We can alloc 1 temp.
            tmp = alloc_func(1, suffix)[0]
            seq.append(self._make_instr("local.tee", [{'val': tmp, 'len':0}]))
            seq.append(self._make_instr("local.get", [{'val': tmp, 'len':0}]))
            # Now [val, val]
            
            if suffix == 'i32':
                seq.append(self._make_instr(f"{suffix}.add"))
            else:
                seq.append(self._make_instr(f"{suffix}.add"))
                
        return seq

    def _to_signed_32(self, n):
        n = n & 0xFFFFFFFF
        return (n ^ 0x80000000) - 0x80000000

    def _to_signed_64(self, n):
        n = n & 0xFFFFFFFFFFFFFFFF
        return (n ^ 0x8000000000000000) - 0x8000000000000000

    def _gen_shl_as_mul(self, strategy, shift_n, is_64, alloc_func):
        # Mask shift amount (WASM semantics)
        if is_64: shift_n &= 63
        else: shift_n &= 31

        # Convert to val * (2^n)
        multiplier = 1 << shift_n
        suffix = "i64" if is_64 else "i32"
        
        # Ensure correct signed representation for WASM
        if is_64:
            multiplier = self._to_signed_64(multiplier)
        else:
            multiplier = self._to_signed_32(multiplier)

        # Inject const
        seq = []
        seq.append(self._make_instr(f"{suffix}.const", [{'val': multiplier, 'len':0}]))
        # Stack: [val, const]
        
        # Call existing mul expansion
        # Note: operands are on stack. _expand_binary_with_strategy expects operands on stack.
        mul_seq = self._expand_binary_with_strategy(strategy, 'mul', is_64)
        return seq + mul_seq

    def _gen_shl_loop(self, strategy, is_64, alloc_func):
        # Variable shift. Stack: [val, shift_amount]
        # Use Doubling Loop.
        # Need locals: L_val, L_cnt
        
        suffix = "i64" if is_64 else "i32"
        l_val, l_cnt = alloc_func(2, suffix)
        
        def instr(n, *v): return self._make_instr(n, [{'val': x, 'len':0} for x in v] if v else None)
        
        seq = []
        seq.append(instr("local.set", l_cnt)) # Pop shift
        seq.append(instr("local.set", l_val)) # Pop val
        
        # Mask shift amount (WASM semantics)
        seq.append(instr("local.get", l_cnt))
        mask = 63 if is_64 else 31
        seq.append(instr(f"{suffix}.const", mask))
        seq.append(instr(f"{suffix}.and"))
        seq.append(instr("local.set", l_cnt))
        
        # Block/Loop
        seq.append(instr("block", 0x40))
        seq.append(instr("loop", 0x40))
        
        # Check cnt == 0
        seq.append(instr("local.get", l_cnt))
        seq.append(instr(f"{suffix}.eqz"))
        seq.append(instr("br_if", 1)) # Break to block end
        
        # val = val + val
        seq.append(instr("local.get", l_val))
        seq.append(instr("local.get", l_val))
        seq.append(instr(f"{suffix}.add"))
        seq.append(instr("local.set", l_val))
        
        # cnt--
        seq.append(instr("local.get", l_cnt))
        seq.append(instr(f"{suffix}.const", 1))
        seq.append(instr(f"{suffix}.sub"))
        seq.append(instr("local.set", l_cnt))
        
        seq.append(instr("br", 0)) # Repeat
        
        seq.append(instr("end")); seq.append(instr("end"))
        
        seq.append(instr("local.get", l_val))
        return seq

    def _expand_div_const(self, divisor, is_signed, is_64, alloc_func):
        if divisor == 0: return [] # Trap anyway
        
        # Magic Number for Unsigned
        if not is_signed:
            import math
            bit_width = 64 if is_64 else 32
            
            # Simple magic number optimization for i32.div_u
            if not is_64:
                p = 31
                try:
                    q = math.ceil(math.log2(divisor))
                except ValueError: q=0
                
                # m = (2**(p+q)) // divisor (approx)
                # Note: Correct algo is nuanced. Using approx for PoC or 
                # (2**(32+q)) // divisor
                m = int((2**(32 + q)) / divisor)
                
                seq = []
                seq.append(self._make_instr("i64.extend_i32_u"))
                seq.append(self._make_instr("i64.const", [{'val': m, 'len':0}]))
                seq.append(self._make_instr("i64.mul"))
                seq.append(self._make_instr("i64.const", [{'val': 32 + q, 'len':0}]))
                seq.append(self._make_instr("i64.shr_u"))
                seq.append(self._make_instr("i32.wrap_i64"))
                return seq

        # Fallback to Float Bridge for signed or hard cases
        suffix = "f64" if is_64 else "f32"
        conv_to = f"{suffix}.convert_i64_s" if is_64 else f"{suffix}.convert_i32_s"
        conv_from = f"i64.trunc_{suffix}_s" if is_64 else f"i32.trunc_{suffix}_s"
        
        seq = []
        seq.append(self._make_instr(conv_to))
        # Push divisor as float
        seq.append(self._make_instr(f"{suffix}.const", [{'val': float(divisor), 'len':0}]))
        seq.append(self._make_instr(f"{suffix}.div"))
        seq.append(self._make_instr(conv_from))
        return seq

    def _gen_div_seq(self, loc_n, loc_d, swap_loc, suffix, alloc_func, is_signed=False):
        # Variable Divisor
        # Strategy: Float Bridge (Simple, Obfuscated) or Binary Long Division
        
        # Float Bridge
        def f_FloatBridge():
            fsuffix = "f64" if suffix == "i64" else "f32"
            conv_to = f"{fsuffix}.convert_{suffix}_s"
            trunc = f"{suffix}.trunc_{fsuffix}_s" # signed truncation
            if not is_signed:
                conv_to = f"{fsuffix}.convert_{suffix}_u"
                trunc = f"{suffix}.trunc_{fsuffix}_u"
                
            def get(l): return self._make_instr("local.get", [{'val': l, 'len':0}])
            def op(n): return self._make_instr(n)
            
            return [
                get(loc_n), op(conv_to),
                get(loc_d), op(conv_to),
                op(f"{fsuffix}.div"),
                op(trunc)
            ]
            
        # Binary Long Division (Unsigned)
        # N=loc_n, D=loc_d. Need Q, R, I.
        # Alloc 3 new locals.
        def f_LongDiv():
            # Only implementing for i32 for simplicity and safety, fall back to Float for i64 or signed
            if suffix != "i32" or is_signed: return f_FloatBridge()
            
            q, r, i = alloc_func(3, 'i32')
            
            def instr(n, *v): return self._make_instr(n, [{'val': x, 'len':0} for x in v] if v else None)
            
            seq = []
            # Init Locals
            seq.append(instr("i32.const", 0)); seq.append(instr("local.set", q))
            seq.append(instr("i32.const", 0)); seq.append(instr("local.set", r))
            seq.append(instr("i32.const", 31)); seq.append(instr("local.set", i))
            
            # Block/Loop
            seq.append(instr("block", 0x40))
            seq.append(instr("loop", 0x40))
            
            # 1. r = r << 1
            seq.append(instr("local.get", r))
            seq.append(instr("i32.const", 1))
            seq.append(instr("i32.shl"))
            seq.append(instr("local.set", r))
            
            # 2. bit = (N >> i) & 1; r = r | bit
            seq.append(instr("local.get", r))
            seq.append(instr("local.get", loc_n))
            seq.append(instr("local.get", i))
            seq.append(instr("i32.shr_u"))
            seq.append(instr("i32.const", 1))
            seq.append(instr("i32.and"))
            seq.append(instr("i32.or"))
            seq.append(instr("local.set", r))
            
            # 3. if r >= D
            seq.append(instr("local.get", r))
            seq.append(instr("local.get", loc_d))
            seq.append(instr("i32.ge_u"))
            seq.append(instr("if", 0x40))
                # r = r - d
            seq.append(instr("local.get", r))
            seq.append(instr("local.get", loc_d))
            seq.append(instr("i32.sub"))
            seq.append(instr("local.set", r))
                # q = q | (1 << i)
            seq.append(instr("local.get", q))
            seq.append(instr("i32.const", 1))
            seq.append(instr("local.get", i))
            seq.append(instr("i32.shl"))
            seq.append(instr("i32.or"))
            seq.append(instr("local.set", q))
            seq.append(instr("end"))
            
            # 4. i--
            seq.append(instr("local.get", i))
            seq.append(instr("i32.const", 1))
            seq.append(instr("i32.sub"))
            seq.append(instr("local.tee", i))
            seq.append(instr("i32.const", 0)); seq.append(instr("i32.ge_s")) # Loop while i >= 0
            seq.append(instr("br_if", 0))
            
            seq.append(instr("end")); seq.append(instr("end"))
            
            seq.append(instr("local.get", q))
            return seq

        if suffix == 'i32' and not is_signed:
            # Random choice
            return random.choice([f_FloatBridge, f_LongDiv])()
        else:
            return f_FloatBridge()

        
    def _expand_binary_with_strategy(self, strategy, op_type, is_64=False, **kwargs):
        mode, op_locs, swap_or_swaps = strategy
        loc_a, loc_b = op_locs
        
        # Extract extra args if needed
        alloc_func = kwargs.get('alloc_func')
        is_signed = kwargs.get('is_signed', False)
        
        suffix = "i64" if is_64 else "i32"
        
        def instr(name, *args):
            return self._make_instr(name, args if args else None)
        
        # 1. Save Sequence
        save_seq = []
        
        if mode == 'new_2':
            # Stack: [a, b] -> loc_a=a, loc_b=b
            save_seq.append(instr("local.set", loc_b))
            save_seq.append(instr("local.set", loc_a))
        
        elif mode == 'reuse_2':
            # Stack [a, b]. Reuse loc_a, loc_b.
            # Convert to: Stack [L0_old, L1_old]. loc_a=a, loc_b=b.
            # Use S1, S2 transients.
            s1, s2 = swap_or_swaps
            
            save_seq.append(instr("local.set", s1)) # S1=b, Stack [a]
            save_seq.append(instr("local.set", s2)) # S2=a, Stack []
            
            save_seq.append(instr("local.get", loc_a)) # Push L0_old
            save_seq.append(instr("local.get", loc_b)) # Push L1_old
            # Stack: [L0_old, L1_old]
            
            save_seq.append(instr("local.get", s2)) # Push a
            save_seq.append(instr("local.set", loc_a)) # L0=a
            
            save_seq.append(instr("local.get", s1)) # Push b
            save_seq.append(instr("local.set", loc_b)) # L1=b
            
        elif mode == 'reuse_1':
            # Stack [a, b]. Reuse loc_a. New loc_b. Swap T.
            # Convert to: Stack [L0_old]. loc_a=a, loc_b=b.
            swap_loc = swap_or_swaps
            
            save_seq.append(instr("local.set", loc_b))    # loc_b=b (it's new, so just set). Stack [a]
            save_seq.append(instr("local.get", loc_a))    # Push L0_old. Stack [a, L0_old]
            save_seq.append(instr("local.set", swap_loc)) # T=L0_old. Stack [a]
            save_seq.append(instr("local.set", loc_a))    # L0=a. Stack []
            save_seq.append(instr("local.get", swap_loc)) # Push L0_old. Stack [L0_old]
        
        # 2. Calculation
        # loc_a=a, loc_b=b.
        # Pass a temp local if available for algos like Russian Peasant.
        # reuse_2: we have s1, s2 free (they hold a,b but we moved them to L0,L1).
        # reuse_1: we have swap_loc free (held L0_old, but we pushed to stack).
        # new_2: no extra temp?
        
        calc_temp = None
        if mode == 'reuse_2':
            calc_temp = swap_or_swaps[0]
        elif mode == 'reuse_1':
            calc_temp = swap_or_swaps
            
        calc_seq = []
        if op_type == 'xor':
            calc_seq = self._gen_xor_seq(loc_a, loc_b, suffix)
        elif op_type == 'mul':
            calc_seq = self._gen_mul_seq(loc_a, loc_b, calc_temp, suffix)
        elif op_type == 'div':
            calc_seq = self._gen_div_seq(loc_a, loc_b, calc_temp, suffix, alloc_func, is_signed=is_signed)
        elif op_type == 'add':
            calc_seq = self._gen_add_seq(loc_a, loc_b, calc_temp, suffix, alloc_func)
        elif op_type == 'sub':
            calc_seq = self._gen_sub_seq(loc_a, loc_b, calc_temp, suffix, alloc_func)
        elif op_type == 'and':
            calc_seq = self._gen_and_seq(loc_a, loc_b, calc_temp, suffix, alloc_func)
        elif op_type == 'or':
            calc_seq = self._gen_or_seq(loc_a, loc_b, calc_temp, suffix, alloc_func)
        
        # 3. Restore Sequence
        restore_seq = []
        
        if mode == 'new_2':
            pass
            
        elif mode == 'reuse_2':
            # Stack [L0_old, L1_old, Res].
            # Goal: Restore L0, L1. Leave Res on stack.
            s1, s2 = swap_or_swaps
            
            restore_seq.append(instr("local.set", s1)) # S1=Res. Stack [L0_old, L1_old]
            restore_seq.append(instr("local.set", loc_b)) # L1=L1_old
            restore_seq.append(instr("local.set", loc_a)) # L0=L0_old
            restore_seq.append(instr("local.get", s1)) # Push Res
            
        elif mode == 'reuse_1':
            # Stack [L0_old, Res]
            swap_loc = swap_or_swaps
            
            restore_seq.append(instr("local.set", loc_b)) # loc_b=Res (temp holding res). Stack [L0_old]
            restore_seq.append(instr("local.set", loc_a)) # L0=L0_old
            restore_seq.append(instr("local.get", loc_b)) # Push Res
            
        return save_seq + calc_seq + restore_seq

    def _gen_xor_seq(self, loc_a, loc_b, suffix):
        def op(name): return self._make_instr(f"{suffix}.{name}")
        def const(val): return self._make_instr(f"{suffix}.const", [val])
        def get_a(): return self._make_instr("local.get", [loc_a])
        def get_b(): return self._make_instr("local.get", [loc_b])
        
        # Formulas from previous step...
        def f_A1(): return [get_a(), get_b(), op("or"), get_a(), get_b(), op("and"), op("sub")]
        def f_A2(): return [get_a(), get_b(), op("add"), get_a(), get_b(), op("and"), const(1), op("shl"), op("sub")]
        # ... include others. To save space, using subset + C3
        def f_C3():
            return [
                get_a(), const(-1), get_b(), op("sub"), op("and"),
                const(-1), get_a(), op("sub"), get_b(), op("and"),
                op("add")
            ]
        
        choices = [f_A1, f_A2, f_C3]
        return random.choice(choices)()

    def _gen_mul_seq(self, loc_a, loc_b, loc_res, suffix):
        def instr(name, *args): return self._make_instr(name, args if args else None)
        def op(name): return self._make_instr(f"{suffix}.{name}")
        def const(val): return self._make_instr(f"{suffix}.const", [val])
        def get_a(): return self._make_instr("local.get", [loc_a])
        def get_b(): return self._make_instr("local.get", [loc_b])
        def get_res(): return self._make_instr("local.get", [loc_res])
        def set_res(): return self._make_instr("local.set", [loc_res])
        def set_a(): return self._make_instr("local.set", [loc_a])
        def set_b(): return self._make_instr("local.set", [loc_b])
        
        # Strategy A: Russian Peasant
        # Requires loc_res. If None (new_2 case), fall back to B.
        def f_RussianPeasant():
            if loc_res is None: return f_ConstantSplit()
            
            # Init Res = 0
            seq = [const(0), set_res()]
            
            # Block End, Loop Head
            seq.append(instr("block", 0x40)) # End label
            seq.append(instr("loop", 0x40))  # Head label
            
            # Check b == 0
            seq.append(get_b())
            seq.append(op("eqz"))
            seq.append(instr("br_if", 1)) # Break to Block End (depth 1)
            
            # Check b & 1
            seq.append(get_b())
            seq.append(const(1))
            seq.append(op("and"))
            seq.append(instr("if", 0x40)) # If odd
            seq.append(get_res())
            seq.append(get_a())
            seq.append(op("add"))
            seq.append(set_res())
            seq.append(instr("end"))
            
            # a <<= 1
            seq.append(get_a())
            seq.append(const(1))
            seq.append(op("shl"))
            seq.append(set_a())
            
            # b >>= 1 (unsigned)
            seq.append(get_b())
            seq.append(const(1))
            seq.append(op("shr_u"))
            seq.append(set_b())
            
            seq.append(instr("br", 0)) # Jump to Loop Head
            
            seq.append(instr("end")) # Close Loop
            seq.append(instr("end")) # Close Block
            
            seq.append(get_res())
            return seq
            
        # Strategy B: Constant Split
        # a * b = a * (b - K) + a * K
        # a * K is expanded to shifts.
        def f_ConstantSplit():
            # Pick K as sum of two powers of 2 for simplicity
            shifts = random.sample(range(1, 30), 2)
            K = (1 << shifts[0]) + (1 << shifts[1])
            
            # Term 1: a * (b - K)
            seq = []
            seq.append(get_a())
            
            seq.append(get_b())
            seq.append(const(K))
            seq.append(op("sub"))
            
            seq.append(op("mul")) # Keep this mul
            
            # Term 2: a * K = (a << s1) + (a << s2)
            # Calc a << s1
            seq.append(get_a())
            seq.append(const(shifts[0]))
            seq.append(op("shl"))
            
            # Calc a << s2
            seq.append(get_a())
            seq.append(const(shifts[1]))
            seq.append(op("shl"))
            
            seq.append(op("add"))
            
            # Result
            seq.append(op("add"))
            return seq
            
        choices = [f_RussianPeasant, f_ConstantSplit]
        # Prefer RP if possible
        if loc_res is None: return f_ConstantSplit()
        
        return random.choice(choices)()
