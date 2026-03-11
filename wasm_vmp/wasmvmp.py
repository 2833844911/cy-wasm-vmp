from operator import index

from .analyzer import WasmAnalyzer
from .utils import (
    add_instr, pack_op, write_leb128_unsigned, write_leb128_signed,
    read_leb128_unsigned, read_leb128_signed, get_opcode_name
)
import random
from .block_definitions import define_instruction_blocks
from .control_flow_flattener import build_bst_dispatch
from .opaque_utils import generate_obfuscated_constant, generate_always_true_check, generate_fake_vmp_block

off = 0


class WasmVMP:
    def __init__(self,max_parem, max_resul,local_dict,codec,max_code, index=0,sp_global_idx=None, func_signatures={ 0: ([], []) },global_types={}, instruction_expansion_factor=1):
        self.vmp_fun = {
            'index': index,
            'signature' : {"params":[], 'results':[]},
            'locals':[],


        }



        for _ in range(max_parem['i32']):
            self.vmp_fun['signature']['params'].append('i32')
        self.len_can_i32 = len(self.vmp_fun['signature']['params'])
        for _ in range(max_parem['i64']):
            self.vmp_fun['signature']['params'].append('i64')
        self.len_can_i64 = len(self.vmp_fun['signature']['params'])
        for _ in range(max_parem['f32']):
            self.vmp_fun['signature']['params'].append('f32')
        self.len_can_f32 = len(self.vmp_fun['signature']['params'])
        for _ in range(max_parem['f64']):
            self.vmp_fun['signature']['params'].append('f64')
        self.len_can_f64 = len(self.vmp_fun['signature']['params'])

        self.bytecode_offset_idx = len(self.vmp_fun['signature']['params'])

        self.vmp_fun['signature']['params'].append('i32')
        self.return_idx = self.bytecode_offset_idx +1
        self.vmp_fun['signature']['params'].append('i32')
        len_cans = len(self.vmp_fun['signature']['params'])


        self.start_i32 = len_cans
        if local_dict['i32']['count'] != 0:
            self.vmp_fun['locals'].append(local_dict['i32'])
        len_cans += local_dict['i32']['count']
        self.start_i64 = len_cans
        if local_dict['i64']['count'] != 0:
            self.vmp_fun['locals'].append(local_dict['i64'])

        len_cans += local_dict['i64']['count']
        self.start_f32 = len_cans

        if local_dict['f32']['count'] != 0:
            self.vmp_fun['locals'].append(local_dict['f32'])

        len_cans += local_dict['f32']['count']
        self.start_f64 = len_cans

        if local_dict['f64']['count'] != 0:
            self.vmp_fun['locals'].append(local_dict['f64'])
        self.sp_global_idx = sp_global_idx


        self.allshuz = [i for i in range(0 + 5, max_code + 500000)]
        self.allreturntype = [i for i in range(0 + 5, max_code + 500000)]
        random.shuffle(self.allshuz)
        random.shuffle(self.allreturntype)
        self.codec = codec
        self.analyzer = WasmAnalyzer(func_signatures=func_signatures, global_types=global_types, types=self.codec.types)

        self.locals_types = []


        for params in self.vmp_fun['signature']['params']:
            self.locals_types.append(params)

        for locals in self.vmp_fun['locals']:
            for _ in range(locals['count']):
                self.locals_types.append(locals['type_name'])
        new_local_idx = len(self.locals_types)


        self.duizhangmem = new_local_idx+1
        self.duizhangmem_idx = new_local_idx+2

        # Define temp vars
        self.tmp_i32 = new_local_idx + 3
        self.tmp_i64 = new_local_idx + 4
        self.tmp_f32 = new_local_idx + 5
        self.tmp_f64 = new_local_idx + 6
        self.code_memsig_addr = new_local_idx + 7
        self.code_memsig_new_addr = new_local_idx + 8
        self.saved_sp = new_local_idx + 9
        self.new_local_idx = new_local_idx
        self.instruction_expansion_factor = instruction_expansion_factor

        duizhangmem = self.duizhangmem
        duizhangmem_idx = self.duizhangmem_idx
        saved_sp = self.saved_sp

        # Define temp vars
        tmp_i32 = self.tmp_i32
        code_memsig_addr = self.code_memsig_addr
        code_memsig_new_addr = self.code_memsig_new_addr

        self.locals_types.extend([ 'i32', 'i32','i32','i32', 'i64', 'f32', 'f64', 'i32', 'i32', 'i32'])
        self.vmp_fun['locals'].append({'count': 3, 'type_name': 'i32', 'type': 127, 'len': 1}) # duizhangmem, idx, saved_sp
        self.vmp_fun['locals'].append({'count': 1, 'type_name': 'i32', 'type': 127, 'len': 1})
        self.vmp_fun['locals'].append({'count': 1, 'type_name': 'i64', 'type': 126, 'len': 1})
        self.vmp_fun['locals'].append({'count': 1, 'type_name': 'f32', 'type': 125, 'len': 1})
        self.vmp_fun['locals'].append({'count': 1, 'type_name': 'f64', 'type': 124, 'len': 1})
        self.vmp_fun['locals'].append({'count': 1, 'type_name': 'i32', 'type': 127, 'len': 1})
        self.vmp_fun['locals'].append({'count': 1, 'type_name': 'i32', 'type': 127, 'len': 1})
        self.vmp_fun['locals'].append({'count': 1, 'type_name': 'i32', 'type': 127, 'len': 1})


        self.len_results_i32 = len(self.locals_types)
        for _ in range(max_resul['i32']):
            self.vmp_fun['signature']['results'].append('i32')
            self.locals_types.append('i32')
            self.vmp_fun['locals'].append({'count': 1, 'type_name': 'i32', 'type': 127, 'len': 1})
        self.len_results_i64 = len(self.locals_types)
        for _ in range(max_resul['i64']):
            self.vmp_fun['signature']['results'].append('i64')
            self.locals_types.append('i64')
            self.vmp_fun['locals'].append({'count': 1, 'type_name': 'i64', 'type': 126, 'len': 1})

        self.len_results_f32 = len(self.locals_types)
        for _ in range(max_resul['f32']):
            self.vmp_fun['signature']['results'].append('f32')
            self.locals_types.append('f32')
            self.vmp_fun['locals'].append({'count': 1, 'type_name': 'f32', 'type': 125, 'len': 1})

        self.len_results_f64 = len(self.locals_types)
        for _ in range(max_resul['f64']):
            self.vmp_fun['signature']['results'].append('f64')
            self.locals_types.append('f64')
            self.vmp_fun['locals'].append({'count': 1, 'type_name': 'f64', 'type': 124, 'len': 1})



        self.putongcodeInfo = {}
        self.new_code = []
        new_code = self.new_code
        self.if_block_list = {}
        if_block_list= self.if_block_list

        self.if_code_idx, self.goto_code_idx, self.null_code_idx, self.i32_const_code_idx, local_get_code_idx, t_list_local_get, i32_add_code_idx, i32_sub_code_idx, i32_mul_code_idx, i32_eq_code_idx, i32_and_code_idx, i32_or_code_idx, i32_xor_code_idx, i32_shl_code_idx, i32_shr_s_code_idx, i32_shr_u_code_idx, i32_rotl_code_idx, i32_rotr_code_idx, i32_ne_code_idx, i32_lt_s_code_idx, i32_lt_u_code_idx, i32_gt_s_code_idx, i32_gt_u_code_idx, i32_le_s_code_idx, i32_le_u_code_idx, i32_ge_s_code_idx, i32_ge_u_code_idx, self.i32_load_code_idx, i64_add_code_idx, i64_sub_code_idx, i64_mul_code_idx, i64_eq_code_idx, i64_ne_code_idx, i64_lt_s_code_idx, i64_lt_u_code_idx, i64_gt_s_code_idx, i64_gt_u_code_idx, i64_le_s_code_idx, i64_le_u_code_idx, i64_ge_s_code_idx, i64_ge_u_code_idx, i64_and_code_idx, i64_or_code_idx, i64_xor_code_idx, i64_shl_code_idx, i64_shr_s_code_idx, i64_shr_u_code_idx, i64_rotl_code_idx, i64_rotr_code_idx, i64_load_code_idx,i32_eqz_code_idx, i64_eqz_code_idx, local_tee_code_idx, t_list_local_tee = define_instruction_blocks(
            self.allshuz, self.if_block_list, new_local_idx, self.duizhangmem, self.code_memsig_addr, self.code_memsig_new_addr, self.tmp_i32, self.tmp_i64
        )
        func_type_idx = 0x40  # 0x40 表示 void (无参无返)

        # Generate Checks
        for i in range(new_local_idx):
            type_name = self.locals_types[i]

            # Check if tmp_i32 == i
            t_list_local_get.append(add_instr(0x20, pack_op(tmp_i32)))
            t_list_local_get.append(add_instr(0x41, pack_op(i)))
            t_list_local_get.append(add_instr(0x46))  # eq
            t_list_local_get.append(add_instr(0x04, 0x40))  # if

            # Body
            t_list_local_get.append(add_instr(0x20, pack_op(duizhangmem)))  # get SP
            t_list_local_get.append(add_instr(0x20, pack_op(i)))  # local.get i

            if type_name == 'i32':
                t_list_local_get.append(add_instr(0x36, [pack_op(0), pack_op(0)]))
                sz = 4
            elif type_name == 'i64':
                t_list_local_get.append(add_instr(0x37, [pack_op(0), pack_op(0)]))
                sz = 8
            elif type_name == 'f32':
                t_list_local_get.append(add_instr(0x38, [pack_op(0), pack_op(0)]))
                sz = 4
            elif type_name == 'f64':
                t_list_local_get.append(add_instr(0x39, [pack_op(0), pack_op(0)]))
                sz = 8
            else:
                # Should not happen for standard locals
                sz = 4

                # Increment SP
            t_list_local_get.append(add_instr(0x20, pack_op(duizhangmem)))
            t_list_local_get.append(add_instr(0x41, pack_op(sz)))
            t_list_local_get.append(add_instr(0x6A))
            t_list_local_get.append(add_instr(0x21, pack_op(duizhangmem)))

            t_list_local_get.append(add_instr(0x0B))  # end if

        t_list_local_get.append(add_instr(0x0B))  # End of Dispatch IF
        if_block_list[local_get_code_idx] = t_list_local_get
        self.local_get_code_idx = local_get_code_idx

        # Generate Checks for local.tee
        for i in range(new_local_idx):
            type_name = self.locals_types[i]

            # Check if tmp_i32 == i
            t_list_local_tee.append(add_instr(0x20, pack_op(tmp_i32)))
            t_list_local_tee.append(add_instr(0x41, pack_op(i)))
            t_list_local_tee.append(add_instr(0x46))  # eq
            t_list_local_tee.append(add_instr(0x04, 0x40))  # if

            # Body
            # 1. Load Value from Stack (Peek)
            t_list_local_tee.append(add_instr(0x20, pack_op(duizhangmem)))  # get SP

            if type_name == 'i32':
                sz = 4
                t_list_local_tee.append(add_instr(0x41, pack_op(4)))
                t_list_local_tee.append(add_instr(0x6B))  # sub
                t_list_local_tee.append(add_instr(0x28, [pack_op(0), pack_op(0)]))  # i32.load (peek)
                # Store to local
                t_list_local_tee.append(add_instr(0x21, pack_op(i)))  # local.set i

            elif type_name == 'i64':
                sz = 8
                t_list_local_tee.append(add_instr(0x41, pack_op(8)))
                t_list_local_tee.append(add_instr(0x6B))  # sub
                t_list_local_tee.append(add_instr(0x29, [pack_op(0), pack_op(0)]))  # i64.load (peek)
                # Store to local
                t_list_local_tee.append(add_instr(0x21, pack_op(i)))  # local.set i

            elif type_name == 'f32':
                sz = 4
                t_list_local_tee.append(add_instr(0x41, pack_op(4)))
                t_list_local_tee.append(add_instr(0x6B))  # sub
                t_list_local_tee.append(add_instr(0x2A, [pack_op(0), pack_op(0)]))  # f32.load (peek)
                # Store to local
                t_list_local_tee.append(add_instr(0x21, pack_op(i)))  # local.set i

            elif type_name == 'f64':
                sz = 8
                t_list_local_tee.append(add_instr(0x41, pack_op(8)))
                t_list_local_tee.append(add_instr(0x6B))  # sub
                t_list_local_tee.append(add_instr(0x2B, [pack_op(0), pack_op(0)]))  # f64.load (peek)
                # Store to local
                t_list_local_tee.append(add_instr(0x21, pack_op(i)))  # local.set i

            else:
                sz = 4

                # SP No Change (Peek)

            t_list_local_tee.append(add_instr(0x0B))  # end if

        t_list_local_tee.append(add_instr(0x0B))  # End of Dispatch IF
        if_block_list[local_tee_code_idx] = t_list_local_tee
        self.local_tee_code_idx = local_tee_code_idx

        # ==========================================
        # 2. 构建 VMP 虚拟机外壳
        # ==========================================

        # [Block Start] 最外层块，用于跳出函数
        new_code.append(add_instr(0x02, func_type_idx))



        # [Stack Allocation]
        # [Stack Allocation]
        if self.sp_global_idx is not None:
            # duizhangmem = global.get(sp) - 1024
            new_code.append(add_instr(0x23, pack_op(self.sp_global_idx)))
            new_code.append(add_instr(0x22, pack_op(self.saved_sp)))  # local.tee saved_sp (Save Original SP)
            
            new_code.append(add_instr(0x41, pack_op(1024)))
            new_code.append(add_instr(0x6B))  # i32.sub
            new_code.append(add_instr(0x22, pack_op(duizhangmem)))  # local.tee duizhangmem
            
            new_code.append(add_instr(0x24, pack_op(self.sp_global_idx)))  # global.set sp (Update Global SP to New SP)
        else:
            # Fallback
            new_code.append(add_instr(0x41, pack_op(1024 * 6)))  # 0x41 i32.const 内存地址
            new_code.append(add_instr(0x21, pack_op(duizhangmem)))  # 0x21 local.set local

        new_code.append(add_instr(0x41, pack_op(0)))  # 0x41 i32.const idx
        new_code.append(add_instr(0x21, pack_op(duizhangmem_idx)))  # 0x21 local.set local

        new_code.append(add_instr(0x20, pack_op(self.bytecode_offset_idx)))
        new_code.append(add_instr(0x21, pack_op(code_memsig_addr)))

        new_code.append(add_instr(0x20, pack_op(code_memsig_addr)))
        new_code.append(add_instr(0x21, pack_op(code_memsig_new_addr)))

        # [Loop Start] 虚拟机主循环
        new_code.append(add_instr(0x03, func_type_idx))

        # 循环就让指令位置+1
        new_code.append(add_instr(0x20, pack_op(code_memsig_new_addr)))
        new_code.append(add_instr(0x20, pack_op(code_memsig_new_addr)))
        new_code.append(add_instr(0x28, [pack_op(0), pack_op(0)]))  # i32.load (加载参数)
        new_code.append(add_instr(0x21, pack_op(new_local_idx)))
        new_code.append(add_instr(0x41, pack_op(4)))
        new_code.append(add_instr(0x6A))  # i32.add
        new_code.append(add_instr(0x21, pack_op(code_memsig_new_addr)))

        self.used_blocks = set()
        self.op_map = {
            'i32.add': i32_add_code_idx, 'i32.sub': i32_sub_code_idx, 'i32.mul': i32_mul_code_idx,
            'i32.eq': i32_eq_code_idx,
            'i32.and': i32_and_code_idx, 'i32.or': i32_or_code_idx, 'i32.xor': i32_xor_code_idx,
            'i32.shl': i32_shl_code_idx, 'i32.shr_s': i32_shr_s_code_idx, 'i32.shr_u': i32_shr_u_code_idx,
            'i32.rotl': i32_rotl_code_idx, 'i32.rotr': i32_rotr_code_idx,
            'i32.ne': i32_ne_code_idx, 'i32.eqz': i32_eqz_code_idx,
            'i32.lt_s': i32_lt_s_code_idx, 'i32.lt_u': i32_lt_u_code_idx,
            'i32.gt_s': i32_gt_s_code_idx, 'i32.gt_u': i32_gt_u_code_idx,
            'i32.le_s': i32_le_s_code_idx, 'i32.le_u': i32_le_u_code_idx,
            'i32.ge_s': i32_ge_s_code_idx, 'i32.ge_u': i32_ge_u_code_idx,

            'i64.add': i64_add_code_idx, 'i64.sub': i64_sub_code_idx, 'i64.mul': i64_mul_code_idx,
            'i64.eq': i64_eq_code_idx,
            'i64.ne': i64_ne_code_idx, 'i64.eqz': i64_eqz_code_idx,
            'i64.lt_s': i64_lt_s_code_idx, 'i64.lt_u': i64_lt_u_code_idx,
            'i64.gt_s': i64_gt_s_code_idx, 'i64.gt_u': i64_gt_u_code_idx,
            'i64.le_s': i64_le_s_code_idx, 'i64.le_u': i64_le_u_code_idx,
            'i64.ge_s': i64_ge_s_code_idx, 'i64.ge_u': i64_ge_u_code_idx,
            'i64.and': i64_and_code_idx, 'i64.or': i64_or_code_idx, 'i64.xor': i64_xor_code_idx,
            'i64.shl': i64_shl_code_idx, 'i64.shr_s': i64_shr_s_code_idx, 'i64.shr_u': i64_shr_u_code_idx,
            'i64.rotl': i64_rotl_code_idx, 'i64.rotr': i64_rotr_code_idx,
            'i64.load': i64_load_code_idx
        }
        self.i64_load_code_idx = i64_load_code_idx
        self.return_type = {}
        self.return_dict = {}

    def find_type(self, params, results):
        for type_data in self.codec.types:
            off = 1
            if len(params) == len(type_data['params']):
                for idx, dt in enumerate(type_data['params']):

                    if params[idx] != dt:
                        off = 0
                        break
            else:
                off = 0
            if len(results) == len(type_data['results']):
                for idx, dt in enumerate(type_data['results']):
                    if results[idx] != dt:
                        off = 0
                        break
            else:
                off = 0
            if off:
                return type_data['index']
        return "no"

    def encode(self, target_func=None, initial_stack=[],bytecode_offset=0):
        target_func = target_func
        code_list = target_func['code']

        this_fun = []



        locals_yingshe = {}
        locals_params = {'i32':0, 'i64':0, 'f32':0, 'f64':0}


        # 1. Collect original parameter indices by type
        params_by_type = {'i32': [], 'i64': [], 'f32': [], 'f64': []}
        for idx, p_type in enumerate(target_func['signature']['params']):
            if p_type in params_by_type:
                params_by_type[p_type].append(idx)

        # 2. Push i32 params (VMP i32 slots: 0 to len_can_i32)
        count_i32 = self.len_can_i32
        for i in range(count_i32):
            if i < len(params_by_type['i32']):
                orig_idx = params_by_type['i32'][i]
                locals_yingshe[orig_idx] = i
                this_fun.append(add_instr(0x20, pack_op(orig_idx))) # local.get
            else:
                this_fun.append(add_instr(0x41, pack_op(0))) # i32.const 0

        # 3. Push i64 params
        count_i64 = self.len_can_i64 - self.len_can_i32
        for i in range(count_i64):
            vmp_idx = self.len_can_i32 + i
            if i < len(params_by_type['i64']):
                orig_idx = params_by_type['i64'][i]
                locals_yingshe[orig_idx] = vmp_idx
                this_fun.append(add_instr(0x20, pack_op(orig_idx))) # local.get
            else:
                this_fun.append(add_instr(0x42, pack_op(0))) # i64.const 0

        # 4. Push f32 params
        count_f32 = self.len_can_f32 - self.len_can_i64
        for i in range(count_f32):
            vmp_idx = self.len_can_i64 + i
            if i < len(params_by_type['f32']):
                orig_idx = params_by_type['f32'][i]
                locals_yingshe[orig_idx] = vmp_idx
                this_fun.append(add_instr(0x20, pack_op(orig_idx))) # local.get
            else:
                this_fun.append(add_instr(0x43, pack_op(0))) # f32.const 0

        # 5. Push f64 params
        count_f64 = self.len_can_f64 - self.len_can_f32
        for i in range(count_f64):
            vmp_idx = self.len_can_f32 + i
            if i < len(params_by_type['f64']):
                orig_idx = params_by_type['f64'][i]
                locals_yingshe[orig_idx] = vmp_idx
                this_fun.append(add_instr(0x20, pack_op(orig_idx))) # local.get
            else:
                this_fun.append(add_instr(0x44, pack_op(0))) # f64.const 0

        jc_par = len(target_func['signature']['params'])
        this_fun.append(add_instr(0x41, pack_op(bytecode_offset)))
        this_fun.append('return') # 本来是return
        this_fun.append(add_instr(0x10, pack_op(self.codec.imported_func_count + self.vmp_fun['index'])))

        locals_params = {'i32': 0, 'i64': 0, 'f32': 0, 'f64': 0}
        myidx = -1
        for locals in target_func['locals']:
            for _ in range(locals['count']):
                myidx += 1
                if locals['type_name'] == 'i32':
                    locals_yingshe[myidx+jc_par] = self.start_i32 + locals_params['i32']
                    locals_params['i32'] = locals_params['i32'] + 1
                elif locals['type_name'] == 'i64':
                    locals_yingshe[myidx+jc_par] = self.start_i64 + locals_params['i64']
                    locals_params['i64'] = locals_params['i64'] + 1
                elif locals['type_name'] == 'f32':
                    locals_yingshe[myidx+jc_par] = self.start_f32 + locals_params['f32']
                    locals_params['f32'] = locals_params['f32'] + 1
                elif locals['type_name'] == 'f64':
                    locals_yingshe[myidx+jc_par] = self.start_f64 + locals_params['f64']
                    locals_params['f64'] = locals_params['f64'] + 1
        results_ret = {'i32': [], 'i64': [], 'f32': [], 'f64': []}
        new_idx_local = myidx+jc_par+1

        for results in self.vmp_fun['signature']['results'][::-1]:
            if results == 'i32':
                target_func['locals'].append({'count': 1, 'type_name': 'i32', 'type': 127, 'len': 1})
                results_ret['i32'].insert(0,new_idx_local)
                this_fun.append(add_instr(0x21, pack_op(new_idx_local)))  # local.set
                new_idx_local += 1
            elif results == 'i64':
                target_func['locals'].append({'count': 1, 'type_name': 'i64', 'type': 126, 'len': 1})
                results_ret['i64'].insert(0,new_idx_local)
                this_fun.append(add_instr(0x21, pack_op(new_idx_local)))  # local.set
                new_idx_local += 1
            elif results == 'f32':
                target_func['locals'].append({'count': 1, 'type_name': 'f32', 'type': 125, 'len': 1})
                results_ret['f32'].insert(0,new_idx_local)
                this_fun.append(add_instr(0x21, pack_op(new_idx_local)))  # local.set
                new_idx_local += 1
            elif results == 'f64':
                target_func['locals'].append({'count': 1, 'type_name': 'f64', 'type': 124, 'len': 1})
                results_ret['f64'].insert(0,new_idx_local)
                this_fun.append(add_instr(0x21, pack_op(new_idx_local)))  # local.set
                new_idx_local += 1

        for myre in target_func['signature']['results']:
            if myre == 'i32':
                this_fun.append(add_instr(0x20, pack_op( results_ret['i32'].pop(0))))  # local.get
            if myre == 'i64':
                this_fun.append(add_instr(0x20, pack_op( results_ret['i64'].pop(0))))  # local.get
            if myre == 'f32':
                this_fun.append(add_instr(0x20, pack_op( results_ret['f32'].pop(0))))  # local.get
            if myre == 'f64':
                this_fun.append(add_instr(0x20, pack_op( results_ret['f64'].pop(0))))  # local.get
        results_ret = {'i32': [], 'i64': [], 'f32': [], 'f64': []}
        return_type_list = []

        results_sig = target_func['signature']['results']
        if len(results_sig) > 0:
            # 1. 计算总大小
            total_res_size = 0
            for r_type in results_sig:
                if r_type in ['i32', 'f32']:
                    total_res_size += 4
                elif r_type in ['i64', 'f64']:
                    total_res_size += 8

            # 2. 依次加载结果
            # 结果在内存中的顺序是 [R0, R1, ...] (地址从小到大)
            # SP 指向结果的“后面” (High Address)
            # 所以 R0 的地址 = SP - TotalSize

            current_res_offset = 0
            for r_type in results_sig:
                # Addr = SP - Total + Current
                # 相当于 SP - (Total - Current)

                offset_from_sp = total_res_size - current_res_offset

                return_type_list.append(add_instr(0x20, pack_op(self.duizhangmem)))  # local.get SP
                return_type_list.append(add_instr(0x41, pack_op(offset_from_sp)))
                return_type_list.append(add_instr(0x6B))  # i32.sub -> Addr

                if r_type == 'i32':
                    return_type_list.append(add_instr(0x28, [pack_op(0), pack_op(0)]))  # i32.load
                    current_res_offset += 4
                elif r_type == 'i64':
                    return_type_list.append(add_instr(0x29, [pack_op(0), pack_op(0)]))  # i64.load
                    current_res_offset += 8
                elif r_type == 'f32':
                    return_type_list.append(add_instr(0x2A, [pack_op(0), pack_op(0)]))  # f32.load
                    current_res_offset += 4
                elif r_type == 'f64':
                    return_type_list.append(add_instr(0x2B, [pack_op(0), pack_op(0)]))  # f64.load
                    current_res_offset += 8

        for myre in target_func['signature']['results'][::-1]:
            if myre == 'i32':
                return_type_list.append(add_instr(0x21, pack_op(self.len_results_i32+len(results_ret['i32']))))  # local.set
                results_ret['i32'].insert(0,self.len_results_i32+len(results_ret['i32']) )
            if myre == 'i64':
                return_type_list.append(add_instr(0x21, pack_op(self.len_results_i64+len(results_ret['i64']))))  # local.set
                results_ret['i64'].insert(0, self.len_results_i64 + len(results_ret['i64']))
            if myre == 'f32':
                return_type_list.append(
                    add_instr(0x21, pack_op(self.len_results_f32 + len(results_ret['f32']))))  # local.set
                results_ret['f32'].insert(0, self.len_results_f32 + len(results_ret['f32']))
            if myre == 'f64':
                return_type_list.append(
                    add_instr(0x21, pack_op(self.len_results_f64 + len(results_ret['f64']))))  # local.set
                results_ret['f64'].insert(0, self.len_results_f64 + len(results_ret['f64']))
        new_idx_local = self.len_results_i32
        for results in self.vmp_fun['signature']['results']:
            if results == 'i32':
                if len(results_ret['i32']) == 0:
                    return_type_list.append(add_instr(0x41, pack_op(10)))  # local.get
                else:
                    dttt = results_ret['i32'].pop(0)
                    return_type_list.append(add_instr(0x20, pack_op(dttt)))  # local.get
                new_idx_local += 1
            elif results == 'i64':
                if len(results_ret['i64']) == 0:
                    return_type_list.append(add_instr(0x42, pack_op(10)))  # local.get
                else:
                    dttt = results_ret['i64'].pop(0)
                    return_type_list.append(add_instr(0x20, pack_op(dttt)))  # local.get
                new_idx_local += 1
            elif results == 'f32':
                if len(results_ret['f32']) == 0:
                    return_type_list.append(add_instr(0x43, pack_op(10)))  # local.get
                else:
                    dttt = results_ret['f32'].pop(0)
                    return_type_list.append(add_instr(0x20, pack_op(dttt)))  # local.get
                new_idx_local += 1
            elif results == 'f64':
                if len(results_ret['f64']) == 0:
                    return_type_list.append(add_instr(0x44, pack_op(10)))  # local.get
                else:
                    dttt = results_ret['f64'].pop(0)
                    return_type_list.append(add_instr(0x20, pack_op(dttt)))  # local.get
                new_idx_local += 1
        if '-'.join(target_func['signature']['results']) not in self.return_dict:
            ddcode = self.allreturntype.pop()
            qmpd = [
                add_instr(0x20, pack_op(self.return_idx)),
                add_instr(0x41, pack_op(ddcode)),
                add_instr(0x46),
                add_instr(0x04, 0x40),  # if

            ]

            self.return_dict['-'.join(target_func['signature']['results'])] = ddcode
            self.return_type[ddcode] = qmpd+return_type_list
        else:
            ddcode = self.return_dict['-'.join(target_func['signature']['results'])]

        for i in range(len(this_fun)):
            if this_fun[i] == 'return':
                # print(ddcode)
                this_fun[i] = add_instr(0x41, pack_op(ddcode))




        locals_types = {}
        for k,v in enumerate(self.locals_types):
            locals_types[k] = v
        # print(locals_yingshe)
        # print(target_func['signature']['params'])
        self.wasmAst = self.analyzer.analyze_wasm_ast(code_list, locals_types=locals_types,
                                                      initial_stack=initial_stack, locals_yingshe=locals_yingshe)


        this_fun.append(add_instr(0x0B))

        # 分配一个新的局部变量作为 PC (Program Counter，指令指针)
        new_local_idx =  self.new_local_idx

        # 初始化随机 ID 池 (预估 ID 数量，打乱顺序以增强混淆)
        # 使用 AST 大小估算，乘 5 是为了留足冗余
        allshuz = self.allshuz


        duizhangmem = self.duizhangmem

        # Define temp vars
        tmp_i32 = self.tmp_i32
        tmp_i64 = self.tmp_i64
        tmp_f32 = self.tmp_f32
        tmp_f64 = self.tmp_f64



        if_block_list = self.if_block_list  # 用于收集所有扁平化后的代码块


        all_code_list = []

        # ==========================================
        # 3. 核心递归函数：生成扁平化代码块
        # ==========================================
        def push_code_list(code_list, current_block_entry_id, deep=0, deep_end=[]):
            # f_idx_e 追踪当前控制流的 ID
            f_idx_e = current_block_entry_id

            for idx, code in enumerate(code_list):
                y_code = code['original_instruction']

                # 当前指令块的 ID
                this_instr_id = f_idx_e
                # 下一条指令块的 ID (预分配)
                next_instr_id = allshuz.pop()

                t_list = []

                all_code_list.append(this_instr_id) # 记录流程

                # -------------------------------------------------
                # A. Dispatch Header (分发检查)
                # -------------------------------------------------
                t_list.append(add_instr(0x20, pack_op(new_local_idx)))  # 0x20 local.get PC (获取当前状态)
                t_list.append(add_instr(0x41, pack_op(this_instr_id)))  # 0x41 i32.const ID (当前块ID)
                t_list.append(add_instr(0x46))  # 0x46 i32.eq (比较 PC == ID)

                # [关键优化] 确定 Block Type
                # 如果是控制流指令 (if)，强制设为 0x40 (void)，因为它们只负责跳转 PC
                code_type_idx = 0x40


                t_list.append(add_instr(0x04, code_type_idx))  # 0x04 IF (Dispatch 成功，进入执行)




                # -------------------------------------------------
                # B. 逻辑处理 (分为 控制流 和 普通指令)
                # -------------------------------------------------

                if code['name'] == 'if':
                    # === Case 1: IF 控制流 (转化为 Select 跳转) ===
                    # ifidx_1 = len(all_code_list) - 1
                    all_code_list.append( "if")


                    true_branch_start_id = allshuz.pop()  # True 分支入口 ID
                    end_merge_id = next_instr_id  # 结束汇合点 ID (End)

                    false_branch_start_id = end_merge_id  # 默认 False 跳到 End
                    if len(code['else_children']) != 0:
                        false_branch_start_id = allshuz.pop()  # 有 Else 则分配新 ID


                    all_code_list.append("x-"+str(true_branch_start_id)) # 占位 true

                    if len(code['else_children']) != 0:
                        all_code_list.append("x-"+str(end_merge_id))
                    else:
                        all_code_list.append("x-"+str(false_branch_start_id)) # 占位 false


                    # [递归] 处理子分支 (使用 children 和 else_children)
                    # 处理 True 分支
                    last_id_of_true = push_code_list(code['children'], true_branch_start_id, deep + 1, deep_end+[end_merge_id])
                    all_code_list.append(last_id_of_true)
                    # 创建链接块：子分支结束后强行跳转到 end_merge_id
                    all_code_list.append('goto')
                    all_code_list.append("x-"+str(end_merge_id))

                    # if_block_list.append(create_link_block(last_id_of_true, end_merge_id, new_local_idx))

                    # 处理 Else 分支
                    if len(code['else_children']) != 0:
                        last_id_of_false = push_code_list(code['else_children'], false_branch_start_id, deep + 1, deep_end+[end_merge_id])
                        all_code_list.append(last_id_of_false)
                        # 创建链接块：子分支结束后强行跳转到 end_merge_id
                        all_code_list.append('goto')
                        all_code_list.append("x-"+str(end_merge_id))
                        # if_block_list.append(create_link_block(last_id_of_false, end_merge_id, new_local_idx))

                    # 当前流的 ID 更新为 End ID
                    f_idx_e = end_merge_id
                elif code['name'] == 'i32.const':
                    all_code_list.append("i32.const")
                    all_code_list.append("x-" + str(code['operands'][0]['val']))
                    # print("x-" + str(code['operands'][0]['val']))
                    f_idx_e = next_instr_id

                elif code['name'] == 'local.get':
                    all_code_list.append("local.get")
                    all_code_list.append("x-" + str(code['operands'][0]['val']))
                    f_idx_e = next_instr_id

                elif code['name'] == 'local.tee':
                    all_code_list.append("local.tee")
                    all_code_list.append("x-" + str(code['operands'][0]['val']))
                    f_idx_e = next_instr_id




                elif code['name'] == 'i32.add':
                    all_code_list.append("i32.add")
                    f_idx_e = next_instr_id
                elif code['name'] == 'i32.sub':
                    all_code_list.append("i32.sub")
                    f_idx_e = next_instr_id
                elif code['name'] == 'i32.mul':
                    all_code_list.append("i32.mul")
                    f_idx_e = next_instr_id
                elif code['name'] == 'i32.eq':
                    all_code_list.append("i32.eq")
                    f_idx_e = next_instr_id

                # Bitwise
                elif code['name'] == 'i32.and':
                    all_code_list.append("i32.and")
                    f_idx_e = next_instr_id
                elif code['name'] == 'i32.or':
                    all_code_list.append("i32.or")
                    f_idx_e = next_instr_id
                elif code['name'] == 'i32.xor':
                    all_code_list.append("i32.xor")
                    f_idx_e = next_instr_id

                # Shift
                elif code['name'] == 'i32.shl':
                    all_code_list.append("i32.shl")
                    f_idx_e = next_instr_id
                elif code['name'] == 'i32.shr_s':
                    all_code_list.append("i32.shr_s")
                    f_idx_e = next_instr_id
                elif code['name'] == 'i32.shr_u':
                    all_code_list.append("i32.shr_u")
                    f_idx_e = next_instr_id
                elif code['name'] == 'i32.rotl':
                    all_code_list.append("i32.rotl")
                    f_idx_e = next_instr_id
                elif code['name'] == 'i32.rotr':
                    all_code_list.append("i32.rotr")
                    f_idx_e = next_instr_id

                # Comparison
                elif code['name'] == 'i32.ne':
                    all_code_list.append("i32.ne")
                    f_idx_e = next_instr_id
                elif code['name'] == 'i32.lt_s':
                    all_code_list.append("i32.lt_s")
                    f_idx_e = next_instr_id
                elif code['name'] == 'i32.eqz':
                    all_code_list.append("i32.eqz")
                    f_idx_e = next_instr_id
                elif code['name'] == 'i64.eqz':
                    all_code_list.append("i64.eqz")
                    f_idx_e = next_instr_id
                elif code['name'] == 'i32.lt_u':
                    all_code_list.append("i32.lt_u")
                    f_idx_e = next_instr_id
                elif code['name'] == 'i32.gt_s':
                    all_code_list.append("i32.gt_s")
                    f_idx_e = next_instr_id
                elif code['name'] == 'i32.gt_u':
                    all_code_list.append("i32.gt_u")
                    f_idx_e = next_instr_id
                elif code['name'] == 'i32.le_s':
                    all_code_list.append("i32.le_s")
                    f_idx_e = next_instr_id
                elif code['name'] == 'i32.le_u':
                    all_code_list.append("i32.le_u")
                    f_idx_e = next_instr_id
                elif code['name'] == 'i32.ge_s':
                    all_code_list.append("i32.ge_s")
                    f_idx_e = next_instr_id
                elif code['name'] == 'i32.ge_u':
                    all_code_list.append("i32.ge_u")
                    f_idx_e = next_instr_id

                # Memory Load
                elif code['name'] == 'i32.load':
                    all_code_list.append("i32.load")
                    # operands[0] is align, operands[1] is offset
                    all_code_list.append("x-" + str(code['operands'][1]['val']))
                    f_idx_e = next_instr_id

                # =================================================
                # i64 Instructions
                # =================================================
                elif code['name'] == 'i64.add':
                    all_code_list.append("i64.add")
                    f_idx_e = next_instr_id
                elif code['name'] == 'i64.sub':
                    all_code_list.append("i64.sub")
                    f_idx_e = next_instr_id
                elif code['name'] == 'i64.mul':
                    all_code_list.append("i64.mul")
                    f_idx_e = next_instr_id
                elif code['name'] == 'i64.eq':
                    all_code_list.append("i64.eq")
                    f_idx_e = next_instr_id
                elif code['name'] == 'i64.ne':
                    all_code_list.append("i64.ne")
                    f_idx_e = next_instr_id
                elif code['name'] == 'i64.lt_s':
                    all_code_list.append("i64.lt_s")
                    f_idx_e = next_instr_id
                elif code['name'] == 'i64.lt_u':
                    all_code_list.append("i64.lt_u")
                    f_idx_e = next_instr_id
                elif code['name'] == 'i64.gt_s':
                    all_code_list.append("i64.gt_s")
                    f_idx_e = next_instr_id
                elif code['name'] == 'i64.gt_u':
                    all_code_list.append("i64.gt_u")
                    f_idx_e = next_instr_id
                elif code['name'] == 'i64.le_s':
                    all_code_list.append("i64.le_s")
                    f_idx_e = next_instr_id
                elif code['name'] == 'i64.le_u':
                    all_code_list.append("i64.le_u")
                    f_idx_e = next_instr_id
                elif code['name'] == 'i64.ge_s':
                    all_code_list.append("i64.ge_s")
                    f_idx_e = next_instr_id
                elif code['name'] == 'i64.ge_u':
                    all_code_list.append("i64.ge_u")
                    f_idx_e = next_instr_id
                elif code['name'] == 'i64.and':
                    all_code_list.append("i64.and")
                    f_idx_e = next_instr_id
                elif code['name'] == 'i64.or':
                    all_code_list.append("i64.or")
                    f_idx_e = next_instr_id
                elif code['name'] == 'i64.xor':
                    all_code_list.append("i64.xor")
                    f_idx_e = next_instr_id
                elif code['name'] == 'i64.shl':
                    all_code_list.append("i64.shl")
                    f_idx_e = next_instr_id
                elif code['name'] == 'i64.shr_s':
                    all_code_list.append("i64.shr_s")
                    f_idx_e = next_instr_id
                elif code['name'] == 'i64.shr_u':
                    all_code_list.append("i64.shr_u")
                    f_idx_e = next_instr_id
                elif code['name'] == 'i64.rotl':
                    all_code_list.append("i64.rotl")
                    f_idx_e = next_instr_id
                elif code['name'] == 'i64.rotr':
                    all_code_list.append("i64.rotr")
                    f_idx_e = next_instr_id

                elif code['name'] == 'i64.load':
                    all_code_list.append("i64.load")
                    all_code_list.append("x-" + str(code['operands'][1]['val']))
                    f_idx_e = next_instr_id

                elif code['name'] == 'block':
                    # ================= BLOCK 处理逻辑 (极简版) =================


                    end_merge_id = allshuz.pop()


                    # 3. 递归处理内部
                    last_id_of_true = push_code_list(code['children'], next_instr_id, deep + 1, deep_end+[end_merge_id])
                    all_code_list.append(last_id_of_true)

                    # if_block_list.append(create_link_block(last_id_of_true, end_merge_id, new_local_idx)) # block 的end
                    all_code_list.append('goto')
                    all_code_list.append("x-"+str(end_merge_id))

                    f_idx_e = end_merge_id

                elif code['name'] == 'loop':
                    # ================= LOOP 处理逻辑 =================


                    end_merge_id = allshuz.pop()

                    # 2. Recurse
                    # [关键] Loop 的 br 0 目标是 Loop 开头 (next_instr_id)
                    # 所以 deep_end 压入 next_instr_id
                    last_id_of_true = push_code_list(code['children'], next_instr_id, deep + 1, deep_end+[next_instr_id])
                    all_code_list.append(last_id_of_true)

                    # 3. Exit Link
                    # if_block_list.append(create_link_block(last_id_of_true, end_merge_id, new_local_idx))
                    # 创建链接块：子分支结束后强行跳转到 end_merge_id
                    all_code_list.append('goto')
                    all_code_list.append("x-"+str(end_merge_id))

                    # 4. Exit
                    f_idx_e = end_merge_id

                    # =================================================
                    # 【新增】 处理 BR 指令 (无条件跳转)
                    # =================================================
                elif code['name'] == 'br':
                    br_depth = code['original_instruction'][2][0]['val']

                    # 【关键判断】检查深度是否超出了当前记录的 Block 范围
                    # deep_end 的长度就是当前嵌套的层数
                    if br_depth >= len(deep_end):
                        # case 1: 跳出函数 (相当于 return)
                        # 跳出 VMP 的外壳 Block (层级为 2)

                        t_list.append(add_instr(0x0C, pack_op(2)))  # br 2
                        t_list.append(add_instr(0x0B))  # end

                        # if_block_list.append(t_list)
                        if_block_list[this_instr_id] = t_list
                    else:
                        # case 2: 跳到某个 Block 的结束位置
                        # 正常取出目标 ID
                        target_id = deep_end[-(br_depth + 1)]


                        all_code_list.append('goto')
                        all_code_list.append("x-"+str(target_id))

                    # t_list.append(add_instr(0x0B))  # end
                    #
                    # # 同样，后续代码不可达，随便指一个 ID 即可
                    # if_block_list.append(t_list)
                    f_idx_e = next_instr_id

                elif code['name'] == 'return':
                    # ================= RETURN 处理逻辑 =================


                    t_list.append(add_instr(0x0C, pack_op(2)))  # 0x0C br 2

                    t_list.append(add_instr(0x0B))  # end (闭合 Dispatch IF)


                    if_block_list[this_instr_id] = t_list
                    f_idx_e = next_instr_id  # 实际上永远不会跳到这里

                # =================================================
                # 【新增】 处理 BR_IF 指令 (条件跳转)
                # =================================================
                elif code['name'] == 'br_if':
                    # 1. 获取深度
                    br_depth = code['original_instruction'][2][0]['val']
                    fallthrough_id = next_instr_id  # 如果不跳转，就去下一条

                    # ================= Case A: 跳出函数 (Return) =================
                    if br_depth >= len(deep_end):

                        all_code_list.append("if")
                        all_code_list.append("over")
                        all_code_list.append("x-"+str(fallthrough_id))

                    # ================= Case B: 内部跳转 (Set PC) =================
                    else:
                        # 获取跳转目标
                        target_id = deep_end[-(br_depth + 1)]

                        all_code_list.append("if")
                        all_code_list.append("x-"+str(target_id))
                        all_code_list.append("x-"+str(fallthrough_id))


                    f_idx_e = next_instr_id

                else:
                    # ============================================
                    # 【修正】普通指令处理逻辑 (Normal Instruction)
                    # ============================================

                    # 1. 计算所有参数总偏移 (用于反向加载)
                    total_pop_size = 0
                    for parem in code['pops']:
                        if parem in ['i32', 'f32']: total_pop_size += 4
                        elif parem in ['i64', 'f64']: total_pop_size += 8
                        else:
                            # [Debug] Raise error for unknown/any types to prevent silent corruption
                            # If analyzer failed to resolve 'any', we can't generate correct VMP code.
                            print(f"[VMP Error] Instruction {code['name']} has unresolved pop type: {parem}")
                            # raise ValueError(f"Unknown type '{parem}' in stack element for instruction {code['name']}")
                            # Fallback to i32? No, unsafe.
                            total_pop_size += 4 

                    # 2. 从【深层】到【浅层】依次加载参数
                    current_acc_offset = 0
                    if len(code['pops']) > 0:
                        for parem in code['pops']:
                            t_list.append(add_instr(0x20, pack_op(duizhangmem)))  # local.get SP
                            t_list.append(add_instr(0x41, pack_op(total_pop_size - current_acc_offset))) # Offset
                            t_list.append(add_instr(0x6B)) # i32.sub -> Addr

                            if parem == 'i32':
                                t_list.append(add_instr(0x28, [pack_op(0), pack_op(0)]))
                                current_acc_offset += 4
                            elif parem == 'i64':
                                t_list.append(add_instr(0x29, [pack_op(0), pack_op(0)]))
                                current_acc_offset += 8
                            elif parem == 'f32':
                                t_list.append(add_instr(0x2A, [pack_op(0), pack_op(0)]))
                                current_acc_offset += 4
                            elif parem == 'f64':
                                t_list.append(add_instr(0x2B, [pack_op(0), pack_op(0)]))
                                current_acc_offset += 8
                            else:
                                raise ValueError(f"Unknown type '{parem}' in stack element for instruction {code['name']}")

                        # 3. 消费参数后，更新 SP (减去 Total)
                        t_list.append(add_instr(0x20, pack_op(duizhangmem)))
                        t_list.append(add_instr(0x41, pack_op(total_pop_size)))
                        t_list.append(add_instr(0x6B)) # sub
                        t_list.append(add_instr(0x21, pack_op(duizhangmem))) # set SP

                    # 4. 执行原始指令
                    t_list.append(y_code)
                    
                    # [Fix] Include pops/pushes AND operands in key.
                    # y_code[3] (raw bytes) only captures original local index.
                    # operands captures the remapped VMP local index.
                    # We must distinguish local.set 10 from local.set 11 even if they were both local.set 0 originally.
                    key = (y_code[3], str(code['pops']), str(code['pushes']), str(code['operands']))
                    
                    if key not in self.putongcodeInfo:
                        self.putongcodeInfo[key] = [this_instr_id]
                    else:
                        self.putongcodeInfo[key].append(this_instr_id)

                    # 5. 处理返回值
                    # 5. 处理返回值 (Result Handling)
                    if len(code['pushes']) >= 1:
                        # 1. 计算每个结果在 VMP 栈帧增量中的偏移 (Offsets)
                        # VMP 栈是向上增长的。如果有 [A(4), B(8)]，SP 增加 12。
                        # A 存放在 SP+0, B 存放在 SP+4。
                        # 栈顶元素是 B。

                        offsets = []
                        current_offset = 0
                        total_sz = 0

                        for pt in code['pushes']:
                            sz = 8 if pt in ['i64', 'f64'] else 4
                            offsets.append({'type': pt, 'offset': current_offset, 'size': sz})
                            current_offset += sz
                            total_sz += sz




                        for i in range(len(code['pushes']) - 1, -1, -1):
                            idx = i
                            pushtype = code['pushes'][idx]
                            info = offsets[idx]
                            offset_val = info['offset']

                            # (A) Pop Value to Temp
                            if pushtype == 'i32':
                                t_list.append(add_instr(0x21, pack_op(tmp_i32)))
                            elif pushtype == 'i64':
                                t_list.append(add_instr(0x21, pack_op(tmp_i64)))
                            elif pushtype == 'f32':
                                t_list.append(add_instr(0x21, pack_op(tmp_f32)))
                            elif pushtype == 'f64':
                                t_list.append(add_instr(0x21, pack_op(tmp_f64)))

                            # (B) Prepare Address: SP + offset
                            t_list.append(add_instr(0x20, pack_op(duizhangmem))) # get SP
                            if offset_val > 0:
                                t_list.append(add_instr(0x41, pack_op(offset_val)))
                                t_list.append(add_instr(0x6A)) # add

                            # (C) Store Value
                            if pushtype == 'i32':
                                t_list.append(add_instr(0x20, pack_op(tmp_i32)))
                                t_list.append(add_instr(0x36, [pack_op(0), pack_op(0)]))
                            elif pushtype == 'i64':
                                t_list.append(add_instr(0x20, pack_op(tmp_i64)))
                                t_list.append(add_instr(0x37, [pack_op(0), pack_op(0)]))
                            elif pushtype == 'f32':
                                t_list.append(add_instr(0x20, pack_op(tmp_f32)))
                                t_list.append(add_instr(0x38, [pack_op(0), pack_op(0)]))
                            elif pushtype == 'f64':
                                t_list.append(add_instr(0x20, pack_op(tmp_f64)))
                                t_list.append(add_instr(0x39, [pack_op(0), pack_op(0)]))

                        # 3. 更新 SP
                        t_list.append(add_instr(0x20, pack_op(duizhangmem)))
                        t_list.append(add_instr(0x41, pack_op(total_sz)))
                        t_list.append(add_instr(0x6A)) # add
                        t_list.append(add_instr(0x21, pack_op(duizhangmem)))

                    # 6. 更新 PC 并跳回 Loop 开头
                    # t_list.append(add_instr(0x41, pack_op(next_instr_id)))
                    # t_list.append(add_instr(0x21, pack_op(new_local_idx)))
                    t_list.append(add_instr(0x0C, pack_op(0)))  # br 1

                    # 7. 闭合 Dispatch
                    t_list.append(add_instr(0x0B))  # 0x0B end

                    # if_block_list.append(t_list)
                    if_block_list[this_instr_id] = t_list
                    f_idx_e = next_instr_id

            if deep == 0: # 指令执行完后结束
                t_list = []
                t_list.append(add_instr(0x20, pack_op(new_local_idx)))  # 0x20 local.get PC (获取当前状态)
                t_list.append(add_instr(0x41, pack_op(f_idx_e)))  # 0x41 i32.const ID (当前块ID)
                t_list.append(add_instr(0x46))  # 0x46 i32.eq (比较 PC == ID)
                t_list.append(add_instr(0x04, 0x40))  # if (condition)
                t_list.append(add_instr(0x0C, pack_op(2)))  # br 2
                t_list.append(add_instr(0x0B))  # 0x0B end
                # if_block_list.append(t_list)
                if_block_list[f_idx_e] = t_list
                all_code_list.append(f_idx_e)

            return f_idx_e

        # ==========================================
        # 5. 执行生成 (Two-Pass Encoding)
        # ==========================================
        if not hasattr(self, 'wasmAst'):
            print("Error: wasmAst not found.")
            return []
        f_idx = allshuz.pop()

        # 从 AST 根节点开始递归生成
        push_code_list(self.wasmAst, f_idx)

        # --- Pass 1: Calculate Offsets (ID -> Memory Index) ---
        id_to_mem_idx = {}
        current_mem_idx = 0

        # We need to iterate all_code_list exactly how the generator does
        # to track the 'virtual' memory index in mycodeshuz

        idx = -1
        while True:
            idx += 1
            if idx >= len(all_code_list):
                break

            zl = all_code_list[idx]

            # [Optimization] Coalesce ID + Generic Op
            # If current is ID and next is Generic Op, map ID to current_mem_idx but DON'T consume space for ID
            is_generic_next = False
            if isinstance(zl, int) and idx + 1 < len(all_code_list):
                next_zl = all_code_list[idx+1]
                if (next_zl in ['if', 'goto', 'i32.const', 'local.get', 'local.tee', 'i32.load', 'i64.load'] or 
                    next_zl in self.op_map):
                    is_generic_next = True
            
            if is_generic_next:
                id_to_mem_idx[zl] = current_mem_idx
                continue # Skip consuming space for this ID, next iteration handles the Op

            # Record the memory index for this ID
            if isinstance(zl, int):
                id_to_mem_idx[zl] = current_mem_idx

            if zl == 'if':
                # Consumes if(1) + target(1) + else(1) = 3 words
                current_mem_idx += 3
                idx += 2 # Skip placeholders in list
            elif zl == 'goto':
                # Consumes goto(1) + target(1) = 2 words
                current_mem_idx += 2
                idx += 1
            elif zl == 'i32.const':
                # Consumes const(1) + val(1) = 2 words
                current_mem_idx += 2
                idx += 1
            elif zl == 'local.get':
                current_mem_idx += 2
                idx += 1
            elif zl == 'local.tee':
                current_mem_idx += 2
                idx += 1
            elif zl == 'i32.load':
                current_mem_idx += 2
                idx += 1
            elif zl == 'i64.load':
                current_mem_idx += 2
                idx += 1
            elif zl in ['i32.add', 'i32.sub', 'i32.mul', 'i32.eq',
                        'i32.and', 'i32.or', 'i32.xor',
                        'i32.shl', 'i32.shr_s', 'i32.shr_u', 'i32.rotl', 'i32.rotr',
                        'i32.ne', 'i32.lt_s', 'i32.lt_u', 'i32.gt_s', 'i32.gt_u', 'i32.le_s', 'i32.le_u', 'i32.ge_s', 'i32.ge_u',
                        'i64.add', 'i64.sub', 'i64.mul', 'i64.eq',
                        'i64.ne', 'i64.lt_s', 'i64.lt_u', 'i64.gt_s', 'i64.gt_u', 'i64.le_s', 'i64.le_u', 'i64.ge_s', 'i64.ge_u',
                        'i64.and', 'i64.or', 'i64.xor',
                        'i64.shl', 'i64.shr_s', 'i64.shr_u', 'i64.rotl', 'i64.rotr', 'i32.eqz', 'i64.eqz']:
                current_mem_idx += 1
                idx += 0
            elif zl in self.op_map: # Handle other ops in map if not listed above
                current_mem_idx += 1
            else:
                # Normal Block ID or Instruction ID
                # Consumes 1 word
                current_mem_idx += 1

        final_mem_idx = current_mem_idx # Point to end (for 'over' jumps)

        # 把一样的指令合并
        zbhebing = {}
        # needdel = [] # Unused
        
        # for k, v in self.putongcodeInfo.items():
        #     # [Instruction Expansion]
        #     # Instead of merging ALL into one (old logic), we keep up to 'instruction_expansion_factor' distinct blocks.
        #     # Example: If factor=5 and we have 10 identical instructions (IDs), we keep 5 separate blocks
        #     # and distribute the 10 usages among these 5 randomly.
        #
        #     # 1. Shuffle to ensure we don't just keep the first ones by control flow order
        #     shuffled_ids = list(v)
        #     random.shuffle(shuffled_ids)
        #
        #     # 2. Select Keepers
        #     count_to_keep = max(1, min(len(shuffled_ids), self.instruction_expansion_factor))
        #     keepers = shuffled_ids[:count_to_keep]
        #     discards = shuffled_ids[count_to_keep:]
        #
        #     # 3. Map Discards to Keepers
        #     for d in discards:
        #         target = random.choice(keepers)
        #         zbhebing[d] = target


        # --- Pass 2: Generate Bytecode using Mappings ---

        mycodeshuz = []
        idx = -1
        while True:
            idx += 1
            if idx >= len(all_code_list):
                break
            zl = all_code_list[idx]

            # [Optimization] Coalesce ID + Generic Op
            is_generic_next = False
            if isinstance(zl, int) and idx + 1 < len(all_code_list):
                next_zl = all_code_list[idx+1]
                if (next_zl in ['if', 'goto', 'i32.const', 'local.get', 'local.tee', 'i32.load', 'i64.load'] or 
                    next_zl in self.op_map):
                    is_generic_next = True
            
            if is_generic_next:
                continue # Skip emitting code for this ID

            if zl == 'if':
                mycodeshuz.append(self.if_code_idx)
                self.used_blocks.add(self.if_code_idx)

                if_goto = all_code_list[idx+1] # "over" or "x-ID"
                if if_goto == 'over':
                    mycodeshuz.append(final_mem_idx)
                else:
                    if_goto_id = int(if_goto.split('-')[-1])
                    if if_goto_id in id_to_mem_idx:
                        mycodeshuz.append(id_to_mem_idx[if_goto_id])
                    else:
                        print(f"Error: if_goto ID {if_goto_id} not found in map")
                        mycodeshuz.append(0) # Error fallback

                else_goto = all_code_list[idx+2] # "x-ID"
                else_goto_id = int(else_goto.split('-')[-1])
                if else_goto_id in id_to_mem_idx:
                    mycodeshuz.append(id_to_mem_idx[else_goto_id])
                else:
                    print(f"Error: else_goto ID {else_goto_id} not found in map")
                    mycodeshuz.append(0)

                idx += 2

            elif zl == 'goto':
                mycodeshuz.append(self.goto_code_idx)
                self.used_blocks.add(self.goto_code_idx)

                goto = all_code_list[idx + 1]
                goto_id = int(goto.split('-')[-1])

                if goto_id in id_to_mem_idx:
                    mycodeshuz.append(id_to_mem_idx[goto_id])
                else:
                     print(f"Error: goto ID {goto_id} not found in map")
                     mycodeshuz.append(0)
                idx +=1

            elif zl == 'i32.const':
                mycodeshuz.append(self.i32_const_code_idx)
                self.used_blocks.add(self.i32_const_code_idx)
                goto = all_code_list[idx + 1]
                val = int(goto[2:]) # Value, not ID
                mycodeshuz.append(val)
                idx += 1

            elif zl == 'local.get':
                mycodeshuz.append(self.local_get_code_idx)
                self.used_blocks.add(self.local_get_code_idx)
                goto = all_code_list[idx + 1]
                val = int(goto[2:])
                mycodeshuz.append(val)
                idx += 1
            elif zl == 'local.tee':
                mycodeshuz.append(self.local_tee_code_idx)
                self.used_blocks.add(self.local_tee_code_idx)
                goto = all_code_list[idx + 1]
                val = int(goto[2:])
                mycodeshuz.append(val)
                idx += 1

            elif zl == 'i32.load':
                mycodeshuz.append(self.i32_load_code_idx)
                self.used_blocks.add(self.i32_load_code_idx)
                goto = all_code_list[idx + 1]
                val = int(goto[2:])
                mycodeshuz.append(val)
                idx += 1

            elif zl == 'i64.load':
                mycodeshuz.append(self.i64_load_code_idx)
                self.used_blocks.add(self.i64_load_code_idx)
                goto = all_code_list[idx + 1]
                val = int(goto[2:])
                mycodeshuz.append(val)
                idx += 1

            elif zl in self.op_map:
                code_idx = self.op_map[zl]
                mycodeshuz.append(code_idx)
                self.used_blocks.add(code_idx)
                idx += 0

            else:
                # Normal ID
                if zl in zbhebing:
                    zl = zbhebing[zl]
                if zl in if_block_list:
                    mycodeshuz.append(zl)
                    self.used_blocks.add(zl)
                elif zl in self.op_map or zl == self.local_get_code_idx or zl == self.local_tee_code_idx or zl == self.i32_const_code_idx:
                    # Generic fallback (should be handled by optimization, but safety)
                    mycodeshuz.append(self.null_code_idx)
                    self.used_blocks.add(self.null_code_idx)
                else:
                    mycodeshuz.append(self.null_code_idx)
                    self.used_blocks.add(self.null_code_idx)

        return this_fun, mycodeshuz


    def over(self):
        new_code = self.new_code
        if_block_list = self.if_block_list
        # Remove unused blocks
        for k in list(if_block_list.keys()):
            # Always keep entry block (f_idx) just in case, though it should be in all_code_list
            if k not in self.used_blocks:
                del if_block_list[k]
        # ==========================================
        # 6. 写入最终代码
        # ==========================================
        # ==========================================
        # 5.5 Inject Virtual Branches (Opaque Predicates)
        # ==========================================
        # User constraint: "First 3 instructions are judgment check, don't move."
        # Strategy: Head(3) -> Check(True) -> IF -> Body(Real) -> ELSE -> Body(Fake) -> END
        
        # ==========================================
        # 5.5 Inject Virtual Branches (Opaque Predicates)
        # ==========================================
        # User constraint: "First 3 instructions are judgment check..."
        # We wrap the ENITRE block (including judgment) to preserve stack flow between judgment and body.
        # Strategy: Check(True) -> IF -> [Head+Body](Real) -> ELSE -> Fake -> END
        
        # for k_idx, block_instrs in if_block_list.items():
        #     if len(block_instrs) <= 3:
        #         continue
        #
        #     # Adjust Br depth in the ENTIRE block
        #     adjusted_block = []
        #     for instr in block_instrs:
        #         name = instr[0]
        #         opcode = instr[1]
        #
        #         if name in ['br', 'br_if']:
        #             # Extract depth
        #             ops_list = instr[2]
        #             if ops_list:
        #                  op_item = ops_list[0]
        #                  current_depth = 0
        #                  if isinstance(op_item, dict):
        #                      current_depth = op_item['val']
        #                  else:
        #                      current_depth = op_item
        #
        #                  new_depth = current_depth + 1
        #                  # Re-pack check
        #                  if isinstance(op_item, dict):
        #                      adjusted_block.append(add_instr(opcode, pack_op(new_depth)))
        #                  else:
        #                      adjusted_block.append(add_instr(opcode, pack_op(new_depth)))
        #             else:
        #                 adjusted_block.append(instr)
        #         else:
        #             adjusted_block.append(instr)
        #
        #     # Generate Opaque Components
        #     # 1. Always True Check
        #     opaque_check = generate_always_true_check(self.new_local_idx)
        #
        #     # 2. Fake Body
        #     fake_body = generate_fake_vmp_block(self.duizhangmem, self.new_local_idx)
        #
        #     # Construct New Block
        #     new_block = []
        #     new_block.extend(opaque_check)
        #     new_block.append(add_instr(0x04, 0x40)) # if void
        #
        #     new_block.extend(adjusted_block)
        #
        #     new_block.append(add_instr(0x05)) # else
        #     new_block.extend(fake_body)
        #
        #     new_block.append(add_instr(0x0B)) # end
        #
        #     # Update list
        #     if_block_list[k_idx] = new_block

        # ==========================================
        # 6. 写入最终代码
        # ==========================================
        if_block_list_lists = []
        for kand, v in if_block_list.items():
            if_block_list_lists.append(v)

        random.shuffle(if_block_list_lists)
        for blk in if_block_list_lists:
            for instr in blk:
                new_code.append(instr)

        # ==========================================
        # 6. 写入最终代码 (BST Dispatch)
        # ==========================================
        # bst_dispatch_code = build_bst_dispatch(if_block_list, self.new_local_idx)
        # for instr in bst_dispatch_code:
        #     new_code.append(instr)
        #这里需要把堆栈放到内存去并且记录类型


        new_code.append(add_instr(0x0C, pack_op(0)))  # br 0 继续循环
        new_code.append(add_instr(0x0B))  # 0x0B end (End Loop)
        new_code.append(add_instr(0x0B))  # 0x0B end (End Block)




        # ==========================================
        # 6. 写入最终代码
        # ==========================================
        if_block_list_lists = []
        for kand, v in self.return_type.items():
            if_block_list_lists.append(v)

        random.shuffle(if_block_list_lists)
        for blk in if_block_list_lists:
            for instr in blk:
                new_code.append(instr)
            # [Stack Restoration]
            if self.sp_global_idx is not None:
                new_code.append(add_instr(0x20, pack_op(self.saved_sp)))  # local.get saved_sp
                # new_code.append(add_instr(0x41, pack_op(1024)))
                # new_code.append(add_instr(0x6A))  # i32.add
                new_code.append(add_instr(0x24, pack_op(self.sp_global_idx)))  # global.set SP
            new_code.append(add_instr(0x0F)) # return
            new_code.append(add_instr(0x0B)) # end

        # 这里需要把堆栈放到内存去并且记录类型


        # -----
        # ==========================================
        # 7. 处理返回值 (Result Handling)
        # ==========================================
        # 必须把结果从内存堆栈 (duizhangmem) 搬运回 WASM 物理堆栈



        new_code.append(add_instr(0x00))  # unreachable
        new_code.append(add_instr(0x0B))  # 0x0B end
        type_idx = self.codec.add_type(self.vmp_fun['signature']['params'], self.vmp_fun['signature']['results'])
        self.vmp_fun['type_index'] = type_idx

        self.vmp_fun['code'] = new_code
        return self.vmp_fun
