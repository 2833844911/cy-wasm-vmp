from .utils import add_instr, pack_op

def define_instruction_blocks(allshuz, if_block_list, new_local_idx, duizhangmem, code_memsig_addr, code_memsig_new_addr, tmp_i32, tmp_i64):
    if_code_idx = allshuz.pop() # if 跳转
    if_block_list[if_code_idx] = [
        add_instr(0x20, pack_op(new_local_idx)),  # 0x20 local.get PC (获取当前状态)
        add_instr(0x41, pack_op(if_code_idx)),  # 0x41 i32.const ID (当前块ID)
        add_instr(0x46),  # 0x46 i32.eq (比较 PC == ID)


        add_instr(0x04,0x40),  # 0x04 IF (Dispatch 成功，进入执行)

        add_instr(0x20, pack_op(duizhangmem)), # get SP
        add_instr(0x41, pack_op(4)), # 4
        add_instr(0x6B), # sub
        add_instr(0x22, pack_op(duizhangmem)), # local.tee SP
        add_instr(0x28, [pack_op(0), pack_op(0)]), # i32.load -> Cond

        add_instr(0x04, 0x40),  # if (condition)
        add_instr(0x20, pack_op(code_memsig_addr)),  # 0x20 local.get code_memsig_addr
        add_instr(0x20, pack_op(code_memsig_new_addr)),  # 0x20 local.get code_memsig_new_addr
        add_instr(0x28, [pack_op(0), pack_op(0)]),  # i32.load (加载参数)
        add_instr(0x41, pack_op(4)),
        add_instr(0x6C),  # i32.mul (计算字节偏移)
        add_instr(0x6A),  # i32.add (基址加偏移)
        add_instr(0x21, pack_op(code_memsig_new_addr)),  # 0x20 local.set code_memsig_new_addr
        add_instr(0x05), # else
        add_instr(0x20, pack_op(code_memsig_addr)),  # 0x20 local.get code_memsig_addr
        add_instr(0x20, pack_op(code_memsig_new_addr)),  # 0x20 local.get code_memsig_new_addr
        add_instr(0x41, pack_op(4)),
        add_instr(0x6A),  # i32.add
        add_instr(0x28, [pack_op(0), pack_op(0)]),  # i32.load (加载参数)
        add_instr(0x41, pack_op(4)),
        add_instr(0x6C),  # i32.mul (计算字节偏移)
        add_instr(0x6A),  # i32.add (基址加偏移)
        add_instr(0x21, pack_op(code_memsig_new_addr)),  # 0x20 local.set code_memsig_new_addr
        add_instr(0x0B),  # 0x0B end
        add_instr(0x0B)  # 0x0B end
    ]
    
    goto_code_idx = allshuz.pop() # 强行跳转
    if_block_list[goto_code_idx] = [
        add_instr(0x20, pack_op(new_local_idx)),  # 0x20 local.get PC (获取当前状态)
        add_instr(0x41, pack_op(goto_code_idx)),  # 0x41 i32.const ID (当前块ID)
        add_instr(0x46),  # 0x46 i32.eq (比较 PC == ID)

        add_instr(0x04, 0x40),  # 0x04 IF (Dispatch 成功，进入执行)
        add_instr(0x20, pack_op(code_memsig_addr)),  # 0x20 local.get code_memsig_addr
        add_instr(0x20, pack_op(code_memsig_new_addr)),  # 0x20 local.get code_memsig_new_addr
        add_instr(0x28, [pack_op(0), pack_op(0)]),  # i32.load (加载参数)
        add_instr(0x41, pack_op(4)),
        add_instr(0x6C),  # i32.mul (计算字节偏移)
        add_instr(0x6A),  # i32.add (基址加偏移)
        add_instr(0x21, pack_op(code_memsig_new_addr)),  # 0x20 local.set code_memsig_new_addr
        add_instr(0x0B)  # 0x0B end
    ]

    null_code_idx = allshuz.pop() # 空指令
    if_block_list[null_code_idx] = [
        add_instr(0x20, pack_op(new_local_idx)),  # 0x20 local.get PC (获取当前状态)
        add_instr(0x41, pack_op(null_code_idx)),  # 0x41 i32.const ID (当前块ID)
        add_instr(0x46),  # 0x46 i32.eq (比较 PC == ID)

        add_instr(0x04, 0x40),  # 0x04 IF (Dispatch 成功，进入执行)
        add_instr(0x0B)  # 0x0B end
    ]

    i32_const_code_idx = allshuz.pop() # i32_const_code_idx
    if_block_list[i32_const_code_idx] = [
        add_instr(0x20, pack_op(new_local_idx)),  # 0x20 local.get PC (获取当前状态)
        add_instr(0x41, pack_op(i32_const_code_idx)),  # 0x41 i32.const ID (当前块ID)
        add_instr(0x46),  # 0x46 i32.eq (比较 PC == ID)

        add_instr(0x04, 0x40),  # 0x04 IF (Dispatch 成功，进入执行)
        add_instr(0x20, pack_op(duizhangmem)),  # get SP

        add_instr(0x20, pack_op(code_memsig_new_addr)),  # 0x20 local.get code_memsig_new_addr
        add_instr(0x28, [pack_op(0), pack_op(0)]),  # i32.load (加载参数)
        add_instr(0x36, [pack_op(0), pack_op(0)]),

        # 3. 更新 SP
        add_instr(0x20, pack_op(duizhangmem)),
        add_instr(0x41, pack_op(4)),
        add_instr(0x6A),
        add_instr(0x21, pack_op(duizhangmem)),

        add_instr(0x20, pack_op(code_memsig_new_addr)),  # 0x20 local.get code_memsig_new_addr
        add_instr(0x41, pack_op(4)),
        add_instr(0x6A),  # i32.add
        add_instr(0x21, pack_op(code_memsig_new_addr)),  # 0x20 local.set code_memsig_new_addr

        add_instr(0x0B)  # 0x0B end
    ]

    local_get_code_idx = allshuz.pop()
    t_list_local_get = [
        add_instr(0x20, pack_op(new_local_idx)), # get PC
        add_instr(0x41, pack_op(local_get_code_idx)),
        add_instr(0x46), # eq
        add_instr(0x04, 0x40), # IF
        
        # Load local index into tmp_i32
        add_instr(0x20, pack_op(code_memsig_new_addr)),
        add_instr(0x28, [pack_op(0), pack_op(0)]), # i32.load
        add_instr(0x21, pack_op(tmp_i32)), # set tmp_i32
        
        # Increment code ptr (skip operand)
        add_instr(0x20, pack_op(code_memsig_new_addr)),
        add_instr(0x41, pack_op(4)),
        add_instr(0x6A), # add
        add_instr(0x21, pack_op(code_memsig_new_addr))
    ]

    local_tee_code_idx = allshuz.pop()
    t_list_local_tee = [
        add_instr(0x20, pack_op(new_local_idx)), # get PC
        add_instr(0x41, pack_op(local_tee_code_idx)),
        add_instr(0x46), # eq
        add_instr(0x04, 0x40), # IF
        
        # Load local index into tmp_i32
        add_instr(0x20, pack_op(code_memsig_new_addr)),
        add_instr(0x28, [pack_op(0), pack_op(0)]), # i32.load
        add_instr(0x21, pack_op(tmp_i32)), # set tmp_i32
        
        # Increment code ptr (skip operand)
        add_instr(0x20, pack_op(code_memsig_new_addr)),
        add_instr(0x41, pack_op(4)),
        add_instr(0x6A), # add
        add_instr(0x21, pack_op(code_memsig_new_addr))
    ]
    
    # ==========================================
    # Helper: Create Binary Op Block (i32)
    # ==========================================
    def create_binary_op_block(op_code):
        idx = allshuz.pop()
        block = [
            add_instr(0x20, pack_op(new_local_idx)),  # get PC
            add_instr(0x41, pack_op(idx)),            # const ID
            add_instr(0x46),                          # eq
            add_instr(0x04, 0x40),                    # IF

            # 1. Load A (SP - 8)
            add_instr(0x20, pack_op(duizhangmem)),
            add_instr(0x41, pack_op(8)),
            add_instr(0x6B), # sub
            add_instr(0x28, [pack_op(0), pack_op(0)]), # load A

            # 2. Load B (SP - 4)
            add_instr(0x20, pack_op(duizhangmem)),
            add_instr(0x41, pack_op(4)),
            add_instr(0x6B), # sub
            add_instr(0x28, [pack_op(0), pack_op(0)]), # load B

            # 3. Perform Op
            add_instr(op_code), 

            # 4. Store Result (at SP - 8)
            add_instr(0x21, pack_op(tmp_i32)), # store result in tmp
            
            add_instr(0x20, pack_op(duizhangmem)),
            add_instr(0x41, pack_op(8)),
            add_instr(0x6B), # sub
            add_instr(0x20, pack_op(tmp_i32)), # get result
            add_instr(0x36, [pack_op(0), pack_op(0)]), # store

            # 5. Update SP (SP - 4)
            add_instr(0x20, pack_op(duizhangmem)),
            add_instr(0x41, pack_op(4)),
            add_instr(0x6B), # sub
            add_instr(0x21, pack_op(duizhangmem)),

            add_instr(0x0B) # End IF
        ]
        return idx, block

    # ==========================================
    # Helper: Create Binary Op Block (i64)
    # ==========================================
    def create_binary_op_block_i64(op_code):
        idx = allshuz.pop()
        block = [
            add_instr(0x20, pack_op(new_local_idx)),  # get PC
            add_instr(0x41, pack_op(idx)),            # const ID
            add_instr(0x46),                          # eq
            add_instr(0x04, 0x40),                    # IF

            # 1. Load A (SP - 16)
            add_instr(0x20, pack_op(duizhangmem)),
            add_instr(0x41, pack_op(16)),
            add_instr(0x6B), # sub
            add_instr(0x29, [pack_op(0), pack_op(0)]), # i64.load A

            # 2. Load B (SP - 8)
            add_instr(0x20, pack_op(duizhangmem)),
            add_instr(0x41, pack_op(8)),
            add_instr(0x6B), # sub
            add_instr(0x29, [pack_op(0), pack_op(0)]), # i64.load B

            # 3. Perform Op
            add_instr(op_code), 

            # 4. Store Result (at SP - 16)
            add_instr(0x21, pack_op(tmp_i64)), # store result in tmp
            
            add_instr(0x20, pack_op(duizhangmem)),
            add_instr(0x41, pack_op(16)),
            add_instr(0x6B), # sub
            add_instr(0x20, pack_op(tmp_i64)), # get result
            add_instr(0x37, [pack_op(0), pack_op(0)]), # i64.store

            # 5. Update SP (SP - 8)
            add_instr(0x20, pack_op(duizhangmem)),
            add_instr(0x41, pack_op(8)),
            add_instr(0x6B), # sub
            add_instr(0x21, pack_op(duizhangmem)),

            add_instr(0x0B) # End IF
        ]
        return idx, block

    # ==========================================
    # Helper: Create Binary Op Block (i64 Comparison)
    # ==========================================
    def create_binary_op_block_i64_cmp(op_code):
        idx = allshuz.pop()
        block = [
            add_instr(0x20, pack_op(new_local_idx)),  # get PC
            add_instr(0x41, pack_op(idx)),            # const ID
            add_instr(0x46),                          # eq
            add_instr(0x04, 0x40),                    # IF

            # 1. Load A (SP - 16)
            add_instr(0x20, pack_op(duizhangmem)),
            add_instr(0x41, pack_op(16)),
            add_instr(0x6B), # sub
            add_instr(0x29, [pack_op(0), pack_op(0)]), # i64.load A

            # 2. Load B (SP - 8)
            add_instr(0x20, pack_op(duizhangmem)),
            add_instr(0x41, pack_op(8)),
            add_instr(0x6B), # sub
            add_instr(0x29, [pack_op(0), pack_op(0)]), # i64.load B

            # 3. Perform Op (Returns i32)
            add_instr(op_code), 

            # 4. Store Result (at SP - 16)
            add_instr(0x21, pack_op(tmp_i32)), # store result in tmp_i32
            
            add_instr(0x20, pack_op(duizhangmem)),
            add_instr(0x41, pack_op(16)),
            add_instr(0x6B), # sub
            add_instr(0x20, pack_op(tmp_i32)), # get result
            add_instr(0x36, [pack_op(0), pack_op(0)]), # i32.store

            # 5. Update SP (SP - 12)
            # Pop 16 bytes (2 * i64), Push 4 bytes (1 * i32) -> Net -12
            add_instr(0x20, pack_op(duizhangmem)),
            add_instr(0x41, pack_op(12)),
            add_instr(0x6B), # sub
            add_instr(0x21, pack_op(duizhangmem)),

            add_instr(0x0B) # End IF
        ]
        return idx, block

    # ==========================================
    # Helper: Create Unary Op Block (i32)
    # ==========================================
    def create_unary_op_block(op_code):
        idx = allshuz.pop()
        block = [
            add_instr(0x20, pack_op(new_local_idx)),  # get PC
            add_instr(0x41, pack_op(idx)),            # const ID
            add_instr(0x46),                          # eq
            add_instr(0x04, 0x40),                    # IF

            # 1. Load A (SP - 4)
            add_instr(0x20, pack_op(duizhangmem)),
            add_instr(0x41, pack_op(4)),
            add_instr(0x6B), # sub
            add_instr(0x28, [pack_op(0), pack_op(0)]), # load A

            # 2. Perform Op
            add_instr(op_code), 

            # 3. Store Result (at SP - 4)
            add_instr(0x21, pack_op(tmp_i32)), # store result in tmp
            
            add_instr(0x20, pack_op(duizhangmem)),
            add_instr(0x41, pack_op(4)),
            add_instr(0x6B), # sub
            add_instr(0x20, pack_op(tmp_i32)), # get result
            add_instr(0x36, [pack_op(0), pack_op(0)]), # store

            # 4. SP No Change (Pop 4, Push 4)

            add_instr(0x0B) # End IF
        ]
        return idx, block

    # ==========================================
    # Helper: Create Unary Op Block (i64 -> i32)
    # ==========================================
    def create_unary_op_block_i64_to_i32(op_code):
        idx = allshuz.pop()
        block = [
            add_instr(0x20, pack_op(new_local_idx)),  # get PC
            add_instr(0x41, pack_op(idx)),            # const ID
            add_instr(0x46),                          # eq
            add_instr(0x04, 0x40),                    # IF

            # 1. Load A (SP - 8)
            add_instr(0x20, pack_op(duizhangmem)),
            add_instr(0x41, pack_op(8)),
            add_instr(0x6B), # sub
            add_instr(0x29, [pack_op(0), pack_op(0)]), # i64.load A

            # 2. Perform Op
            add_instr(op_code), 

            # 3. Store Result (at SP - 8)
            add_instr(0x21, pack_op(tmp_i32)), # store result in tmp
            
            add_instr(0x20, pack_op(duizhangmem)),
            add_instr(0x41, pack_op(8)),
            add_instr(0x6B), # sub
            add_instr(0x20, pack_op(tmp_i32)), # get result
            add_instr(0x36, [pack_op(0), pack_op(0)]), # i32.store

            # 4. Update SP (SP - 4)
            # Pop 8 bytes, Push 4 bytes -> Net -4
            add_instr(0x20, pack_op(duizhangmem)),
            add_instr(0x41, pack_op(4)),
            add_instr(0x6B), # sub
            add_instr(0x21, pack_op(duizhangmem)),

            add_instr(0x0B) # End IF
        ]
        return idx, block

    # i32 Ops
    i32_add_code_idx, i32_add_block = create_binary_op_block(0x6A) # i32.add
    if_block_list[i32_add_code_idx] = i32_add_block

    i32_sub_code_idx, i32_sub_block = create_binary_op_block(0x6B) # i32.sub
    if_block_list[i32_sub_code_idx] = i32_sub_block

    i32_mul_code_idx, i32_mul_block = create_binary_op_block(0x6C) # i32.mul
    if_block_list[i32_mul_code_idx] = i32_mul_block
    
    i32_eq_code_idx, i32_eq_block = create_binary_op_block(0x46) # i32.eq
    if_block_list[i32_eq_code_idx] = i32_eq_block

    # i32.eqz
    i32_eqz_code_idx, i32_eqz_block = create_unary_op_block(0x45) # i32.eqz
    if_block_list[i32_eqz_code_idx] = i32_eqz_block

    # Bitwise
    i32_and_code_idx, i32_and_block = create_binary_op_block(0x71)
    if_block_list[i32_and_code_idx] = i32_and_block
    
    i32_or_code_idx, i32_or_block = create_binary_op_block(0x72)
    if_block_list[i32_or_code_idx] = i32_or_block
    
    i32_xor_code_idx, i32_xor_block = create_binary_op_block(0x73)
    if_block_list[i32_xor_code_idx] = i32_xor_block

    # Shift
    i32_shl_code_idx, i32_shl_block = create_binary_op_block(0x74)
    if_block_list[i32_shl_code_idx] = i32_shl_block
    
    i32_shr_s_code_idx, i32_shr_s_block = create_binary_op_block(0x75)
    if_block_list[i32_shr_s_code_idx] = i32_shr_s_block
    
    i32_shr_u_code_idx, i32_shr_u_block = create_binary_op_block(0x76)
    if_block_list[i32_shr_u_code_idx] = i32_shr_u_block
    
    i32_rotl_code_idx, i32_rotl_block = create_binary_op_block(0x77)
    if_block_list[i32_rotl_code_idx] = i32_rotl_block
    
    i32_rotr_code_idx, i32_rotr_block = create_binary_op_block(0x78)
    if_block_list[i32_rotr_code_idx] = i32_rotr_block

    # Comparison
    i32_ne_code_idx, i32_ne_block = create_binary_op_block(0x47)
    if_block_list[i32_ne_code_idx] = i32_ne_block
    
    i32_lt_s_code_idx, i32_lt_s_block = create_binary_op_block(0x48)
    if_block_list[i32_lt_s_code_idx] = i32_lt_s_block
    
    i32_lt_u_code_idx, i32_lt_u_block = create_binary_op_block(0x49)
    if_block_list[i32_lt_u_code_idx] = i32_lt_u_block
    
    i32_gt_s_code_idx, i32_gt_s_block = create_binary_op_block(0x4A)
    if_block_list[i32_gt_s_code_idx] = i32_gt_s_block
    
    i32_gt_u_code_idx, i32_gt_u_block = create_binary_op_block(0x4B)
    if_block_list[i32_gt_u_code_idx] = i32_gt_u_block
    
    i32_le_s_code_idx, i32_le_s_block = create_binary_op_block(0x4C)
    if_block_list[i32_le_s_code_idx] = i32_le_s_block
    
    i32_le_u_code_idx, i32_le_u_block = create_binary_op_block(0x4D)
    if_block_list[i32_le_u_code_idx] = i32_le_u_block
    
    i32_ge_s_code_idx, i32_ge_s_block = create_binary_op_block(0x4E)
    if_block_list[i32_ge_s_code_idx] = i32_ge_s_block
    
    i32_ge_u_code_idx, i32_ge_u_block = create_binary_op_block(0x4F)
    if_block_list[i32_ge_u_code_idx] = i32_ge_u_block

    # i32.load
    i32_load_code_idx = allshuz.pop()
    if_block_list[i32_load_code_idx] = [
        add_instr(0x20, pack_op(new_local_idx)),  # get PC
        add_instr(0x41, pack_op(i32_load_code_idx)),
        add_instr(0x46), # eq
        add_instr(0x04, 0x40), # IF

        # 1. Get Offset from Bytecode (PC)
        add_instr(0x20, pack_op(code_memsig_new_addr)),
        add_instr(0x28, [pack_op(0), pack_op(0)]), # load offset
        add_instr(0x21, pack_op(tmp_i32)), # store offset in tmp

        # 2. Get Base Address from Stack (SP - 4)
        add_instr(0x20, pack_op(duizhangmem)),
        add_instr(0x41, pack_op(4)),
        add_instr(0x6B), # sub
        add_instr(0x28, [pack_op(0), pack_op(0)]), # load base addr

        # 3. Add Offset
        add_instr(0x20, pack_op(tmp_i32)),
        add_instr(0x6A), # add -> Effective Addr

        # 4. Perform Load
        add_instr(0x28, [pack_op(0), pack_op(0)]), # i32.load (from effective addr)

        # 5. Store Result back to Stack (SP - 4)
        add_instr(0x21, pack_op(tmp_i32)), # store result in tmp
        
        add_instr(0x20, pack_op(duizhangmem)),
        add_instr(0x41, pack_op(4)),
        add_instr(0x6B), # sub
        add_instr(0x20, pack_op(tmp_i32)), # get result
        add_instr(0x36, [pack_op(0), pack_op(0)]), # store result

        # 6. Increment PC (skip offset)
        add_instr(0x20, pack_op(code_memsig_new_addr)),
        add_instr(0x41, pack_op(4)),
        add_instr(0x6A),
        add_instr(0x21, pack_op(code_memsig_new_addr)),

        add_instr(0x0B) # End IF
    ]

    # ==========================================
    # i64 Ops
    # ==========================================
    i64_add_code_idx, i64_add_block = create_binary_op_block_i64(0x7C) # i64.add
    if_block_list[i64_add_code_idx] = i64_add_block
    
    i64_sub_code_idx, i64_sub_block = create_binary_op_block_i64(0x7D) # i64.sub
    if_block_list[i64_sub_code_idx] = i64_sub_block
    
    i64_mul_code_idx, i64_mul_block = create_binary_op_block_i64(0x7E) # i64.mul
    if_block_list[i64_mul_code_idx] = i64_mul_block
    
    # Comparisons (Use CMP helper)
    i64_eq_code_idx, i64_eq_block = create_binary_op_block_i64_cmp(0x51) # i64.eq
    if_block_list[i64_eq_code_idx] = i64_eq_block
    
    i64_ne_code_idx, i64_ne_block = create_binary_op_block_i64_cmp(0x52) # i64.ne
    if_block_list[i64_ne_code_idx] = i64_ne_block
    
    i64_lt_s_code_idx, i64_lt_s_block = create_binary_op_block_i64_cmp(0x53) # i64.lt_s
    if_block_list[i64_lt_s_code_idx] = i64_lt_s_block
    
    i64_lt_u_code_idx, i64_lt_u_block = create_binary_op_block_i64_cmp(0x54) # i64.lt_u
    if_block_list[i64_lt_u_code_idx] = i64_lt_u_block
    
    i64_gt_s_code_idx, i64_gt_s_block = create_binary_op_block_i64_cmp(0x55) # i64.gt_s
    if_block_list[i64_gt_s_code_idx] = i64_gt_s_block
    
    i64_gt_u_code_idx, i64_gt_u_block = create_binary_op_block_i64_cmp(0x56) # i64.gt_u
    if_block_list[i64_gt_u_code_idx] = i64_gt_u_block
    
    i64_le_s_code_idx, i64_le_s_block = create_binary_op_block_i64_cmp(0x57) # i64.le_s
    if_block_list[i64_le_s_code_idx] = i64_le_s_block
    
    i64_le_u_code_idx, i64_le_u_block = create_binary_op_block_i64_cmp(0x58) # i64.le_u
    if_block_list[i64_le_u_code_idx] = i64_le_u_block
    
    i64_ge_s_code_idx, i64_ge_s_block = create_binary_op_block_i64_cmp(0x59) # i64.ge_s
    if_block_list[i64_ge_s_code_idx] = i64_ge_s_block
    
    i64_ge_u_code_idx, i64_ge_u_block = create_binary_op_block_i64_cmp(0x5A) # i64.ge_u
    if_block_list[i64_ge_u_code_idx] = i64_ge_u_block

    # i64.eqz
    i64_eqz_code_idx, i64_eqz_block = create_unary_op_block_i64_to_i32(0x50) # i64.eqz
    if_block_list[i64_eqz_code_idx] = i64_eqz_block
    
    # Bitwise
    i64_and_code_idx, i64_and_block = create_binary_op_block_i64(0x83) # i64.and
    if_block_list[i64_and_code_idx] = i64_and_block
    
    i64_or_code_idx, i64_or_block = create_binary_op_block_i64(0x84) # i64.or
    if_block_list[i64_or_code_idx] = i64_or_block
    
    i64_xor_code_idx, i64_xor_block = create_binary_op_block_i64(0x85) # i64.xor
    if_block_list[i64_xor_code_idx] = i64_xor_block
    
    i64_shl_code_idx, i64_shl_block = create_binary_op_block_i64(0x86) # i64.shl
    if_block_list[i64_shl_code_idx] = i64_shl_block
    
    i64_shr_s_code_idx, i64_shr_s_block = create_binary_op_block_i64(0x87) # i64.shr_s
    if_block_list[i64_shr_s_code_idx] = i64_shr_s_block
    
    i64_shr_u_code_idx, i64_shr_u_block = create_binary_op_block_i64(0x88) # i64.shr_u
    if_block_list[i64_shr_u_code_idx] = i64_shr_u_block
    
    i64_rotl_code_idx, i64_rotl_block = create_binary_op_block_i64(0x89) # i64.rotl
    if_block_list[i64_rotl_code_idx] = i64_rotl_block
    
    i64_rotr_code_idx, i64_rotr_block = create_binary_op_block_i64(0x8A) # i64.rotr
    if_block_list[i64_rotr_code_idx] = i64_rotr_block

    # i64.load
    i64_load_code_idx = allshuz.pop()
    if_block_list[i64_load_code_idx] = [
        add_instr(0x20, pack_op(new_local_idx)),  # get PC
        add_instr(0x41, pack_op(i64_load_code_idx)),
        add_instr(0x46), # eq
        add_instr(0x04, 0x40), # IF

        # 1. Get Offset from Bytecode (PC)
        add_instr(0x20, pack_op(code_memsig_new_addr)),
        add_instr(0x28, [pack_op(0), pack_op(0)]), # load offset
        add_instr(0x21, pack_op(tmp_i32)), # store offset in tmp

        # 2. Get Base Address from Stack (SP - 4)
        add_instr(0x20, pack_op(duizhangmem)),
        add_instr(0x41, pack_op(4)),
        add_instr(0x6B), # sub
        add_instr(0x28, [pack_op(0), pack_op(0)]), # load base addr

        # 3. Add Offset
        add_instr(0x20, pack_op(tmp_i32)),
        add_instr(0x6A), # add -> Effective Addr

        # 4. Perform Load (i64)
        add_instr(0x29, [pack_op(0), pack_op(0)]), # i64.load (from effective addr)

        # 5. Store Result back to Stack (SP - 4)
        # We need to store 8 bytes starting at SP-4.
        # This will overwrite the base address and extend 4 bytes beyond.
        add_instr(0x21, pack_op(tmp_i64)), # store result in tmp
        
        add_instr(0x20, pack_op(duizhangmem)),
        add_instr(0x41, pack_op(4)),
        add_instr(0x6B), # sub
        add_instr(0x20, pack_op(tmp_i64)), # get result
        add_instr(0x37, [pack_op(0), pack_op(0)]), # i64.store

        # 6. Increment SP by 4 (Net change: -4 + 8 = +4)
        add_instr(0x20, pack_op(duizhangmem)),
        add_instr(0x41, pack_op(4)),
        add_instr(0x6A), # add
        add_instr(0x21, pack_op(duizhangmem)),

        # 7. Increment PC (skip offset)
        add_instr(0x20, pack_op(code_memsig_new_addr)),
        add_instr(0x41, pack_op(4)),
        add_instr(0x6A),
        add_instr(0x21, pack_op(code_memsig_new_addr)),

        add_instr(0x0B) # End IF
    ]

    return (if_code_idx, goto_code_idx, null_code_idx, i32_const_code_idx, local_get_code_idx, t_list_local_get, 
            i32_add_code_idx, i32_sub_code_idx, i32_mul_code_idx, i32_eq_code_idx,
            i32_and_code_idx, i32_or_code_idx, i32_xor_code_idx,
            i32_shl_code_idx, i32_shr_s_code_idx, i32_shr_u_code_idx, i32_rotl_code_idx, i32_rotr_code_idx,
            i32_ne_code_idx, i32_lt_s_code_idx, i32_lt_u_code_idx, i32_gt_s_code_idx, i32_gt_u_code_idx, 
            i32_le_s_code_idx, i32_le_u_code_idx, i32_ge_s_code_idx, i32_ge_u_code_idx,
            i32_load_code_idx,
            i64_add_code_idx, i64_sub_code_idx, i64_mul_code_idx, i64_eq_code_idx,
            i64_ne_code_idx, i64_lt_s_code_idx, i64_lt_u_code_idx, i64_gt_s_code_idx, i64_gt_u_code_idx,
            i64_le_s_code_idx, i64_le_u_code_idx, i64_ge_s_code_idx, i64_ge_u_code_idx,
            i64_and_code_idx, i64_or_code_idx, i64_xor_code_idx,
            i64_shl_code_idx, i64_shr_s_code_idx, i64_shr_u_code_idx, i64_rotl_code_idx, i64_rotr_code_idx,
            i64_load_code_idx,
            i32_eqz_code_idx, i64_eqz_code_idx, local_tee_code_idx, t_list_local_tee)
