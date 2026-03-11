import random
class JiexStart():
    def __init__(self,wasm_file = 'base64_2.wasm'):

        with open(wasm_file, "rb") as f:
            self.wasm_data = f.read()
        self.WASM_MAGIC = b'\x00\x61\x73\x6D'  # 魔数: '0x00 0x61 0x73 0x6D' (对应 'wasm')
        self.WASM_VERSION = b'\x01\x00\x00\x00'  # 版本: '0x01 0x00 0x00 0x00'
        self.imports = []
        self.can_safe_mem = 1024
        self.function_codes = []
        self.module_function_names = {}
        self.exports = {}
        self.VALUE_TYPE_NAMES = {
            0x7F: "i32",
            0x7E: "i64",
            0x7D: "f32",
            0x7C: "f64",
            0x7B: "v128",
            0x70: "funcref",
            0x6F: "externref",
            0x40: "void"
        }

        # WASM 操作码字典 (对应 V8: wasm-opcodes.h)
        # 这个字典包含了所有标准 WASM 操作码的映射
        self.WASM_OPCODES = {
            # 控制流指令 (0x00-0x1F) - wasm-opcodes.h 第34-55行
            0x00: "unreachable",
            0x01: "nop",
            0x02: "block",
            0x03: "loop",
            0x04: "if",
            0x05: "else",
            0x0B: "end",
            0x0C: "br",
            0x0D: "br_if",
            0x0E: "br_table",
            0x0F: "return",

            # 函数调用 (0x10-0x15) - wasm-opcodes.h 第59-64行
            0x10: "call",
            0x11: "call_indirect",
            0x12: "return_call",
            0x13: "return_call_indirect",

            # 变量操作 (0x1A-0x26) - wasm-opcodes.h 第65-74行
            0x1A: "drop",
            0x1B: "select",
            0x20: "local.get",
            0x21: "local.set",
            0x22: "local.tee",
            0x23: "global.get",
            0x24: "global.set",
            0x25: "table.get",
            0x26: "table.set",

            # 内存加载 (0x28-0x35) - wasm-opcodes.h 第86-99行
            0x28: "i32.load",
            0x29: "i64.load",
            0x2A: "f32.load",
            0x2B: "f64.load",
            0x2C: "i32.load8_s",
            0x2D: "i32.load8_u",
            0x2E: "i32.load16_s",
            0x2F: "i32.load16_u",
            0x30: "i64.load8_s",
            0x31: "i64.load8_u",
            0x32: "i64.load16_s",
            0x33: "i64.load16_u",
            0x34: "i64.load32_s",
            0x35: "i64.load32_u",

            # 内存存储 (0x36-0x3E) - wasm-opcodes.h 第103-111行
            0x36: "i32.store",
            0x37: "i64.store",
            0x38: "f32.store",
            0x39: "f64.store",
            0x3A: "i32.store8",
            0x3B: "i32.store16",
            0x3C: "i64.store8",
            0x3D: "i64.store16",
            0x3E: "i64.store32",

            # 内存操作 (0x3F-0x40) - wasm-opcodes.h 第115-116行
            0x3F: "memory.size",
            0x40: "memory.grow",

            # 常量 (0x41-0x44) - wasm-opcodes.h 第75-78行
            0x41: "i32.const",
            0x42: "i64.const",
            0x43: "f32.const",
            0x44: "f64.const",

            # i32 比较 (0x45-0x4F) - wasm-opcodes.h 第131-141行
            0x45: "i32.eqz",
            0x46: "i32.eq",
            0x47: "i32.ne",
            0x48: "i32.lt_s",
            0x49: "i32.lt_u",
            0x4A: "i32.gt_s",
            0x4B: "i32.gt_u",
            0x4C: "i32.le_s",
            0x4D: "i32.le_u",
            0x4E: "i32.ge_s",
            0x4F: "i32.ge_u",

            # i64 比较 (0x50-0x5A) - wasm-opcodes.h 第142-152行
            0x50: "i64.eqz",
            0x51: "i64.eq",
            0x52: "i64.ne",
            0x53: "i64.lt_s",
            0x54: "i64.lt_u",
            0x55: "i64.gt_s",
            0x56: "i64.gt_u",
            0x57: "i64.le_s",
            0x58: "i64.le_u",
            0x59: "i64.ge_s",
            0x5A: "i64.ge_u",

            # f32 比较 (0x5B-0x60) - wasm-opcodes.h 第153-158行
            0x5B: "f32.eq",
            0x5C: "f32.ne",
            0x5D: "f32.lt",
            0x5E: "f32.gt",
            0x5F: "f32.le",
            0x60: "f32.ge",

            # f64 比较 (0x61-0x66) - wasm-opcodes.h 第159-164行
            0x61: "f64.eq",
            0x62: "f64.ne",
            0x63: "f64.lt",
            0x64: "f64.gt",
            0x65: "f64.le",
            0x66: "f64.ge",

            # i32 算术 (0x67-0x78) - wasm-opcodes.h 第165-179行
            0x67: "i32.clz",
            0x68: "i32.ctz",
            0x69: "i32.popcnt",
            0x6A: "i32.add",
            0x6B: "i32.sub",
            0x6C: "i32.mul",
            0x6D: "i32.div_s",
            0x6E: "i32.div_u",
            0x6F: "i32.rem_s",
            0x70: "i32.rem_u",
            0x71: "i32.and",
            0x72: "i32.or",
            0x73: "i32.xor",
            0x74: "i32.shl",
            0x75: "i32.shr_s",
            0x76: "i32.shr_u",
            0x77: "i32.rotl",
            0x78: "i32.rotr",

            # i64 算术 (0x79-0x8A) - wasm-opcodes.h 第180-194行
            0x79: "i64.clz",
            0x7A: "i64.ctz",
            0x7B: "i64.popcnt",
            0x7C: "i64.add",
            0x7D: "i64.sub",
            0x7E: "i64.mul",
            0x7F: "i64.div_s",
            0x80: "i64.div_u",
            0x81: "i64.rem_s",
            0x82: "i64.rem_u",
            0x83: "i64.and",
            0x84: "i64.or",
            0x85: "i64.xor",
            0x86: "i64.shl",
            0x87: "i64.shr_s",
            0x88: "i64.shr_u",
            0x89: "i64.rotl",
            0x8A: "i64.rotr",

            # f32 算术 (0x8B-0x98) - wasm-opcodes.h 第195-208行
            0x8B: "f32.abs",
            0x8C: "f32.neg",
            0x8D: "f32.ceil",
            0x8E: "f32.floor",
            0x8F: "f32.trunc",
            0x90: "f32.nearest",
            0x91: "f32.sqrt",
            0x92: "f32.add",
            0x93: "f32.sub",
            0x94: "f32.mul",
            0x95: "f32.div",
            0x96: "f32.min",
            0x97: "f32.max",
            0x98: "f32.copysign",

            # f64 算术 (0x99-0xA6) - wasm-opcodes.h 第209-222行
            0x99: "f64.abs",
            0x9A: "f64.neg",
            0x9B: "f64.ceil",
            0x9C: "f64.floor",
            0x9D: "f64.trunc",
            0x9E: "f64.nearest",
            0x9F: "f64.sqrt",
            0xA0: "f64.add",
            0xA1: "f64.sub",
            0xA2: "f64.mul",
            0xA3: "f64.div",
            0xA4: "f64.min",
            0xA5: "f64.max",
            0xA6: "f64.copysign",

            # 类型转换 (0xA7-0xC4) - wasm-opcodes.h 第223-252行
            0xA7: "i32.wrap_i64",
            0xA8: "i32.trunc_f32_s",
            0xA9: "i32.trunc_f32_u",
            0xAA: "i32.trunc_f64_s",
            0xAB: "i32.trunc_f64_u",
            0xAC: "i64.extend_i32_s",
            0xAD: "i64.extend_i32_u",
            0xAE: "i64.trunc_f32_s",
            0xAF: "i64.trunc_f32_u",
            0xB0: "i64.trunc_f64_s",
            0xB1: "i64.trunc_f64_u",
            0xB2: "f32.convert_i32_s",
            0xB3: "f32.convert_i32_u",
            0xB4: "f32.convert_i64_s",
            0xB5: "f32.convert_i64_u",
            0xB6: "f32.demote_f64",
            0xB7: "f64.convert_i32_s",
            0xB8: "f64.convert_i32_u",
            0xB9: "f64.convert_i64_s",
            0xBA: "f64.convert_i64_u",
            0xBB: "f64.promote_f32",
            0xBC: "i32.reinterpret_f32",
            0xBD: "i64.reinterpret_f64",
            0xBE: "f32.reinterpret_i32",
            0xBF: "f64.reinterpret_i64",
            0xC0: "i32.extend8_s",
            0xC1: "i32.extend16_s",
            0xC2: "i64.extend8_s",
            0xC3: "i64.extend16_s",
            0xC4: "i64.extend32_s",

            # 引用类型 (0xD0-0xD6)
            0xD0: "ref.null",
            0xD1: "ref.is_null",
            0xD2: "ref.func",
            0xD3: "ref.as_non_null",
            0xD4: "br_on_null",
            0xD5: "ref.eq",
            0xD6: "br_on_non_null",
        }
        self.IMPORT_EXPORT_KIND_NAMES = {
            0: "Function",
            1: "Table",
            2: "Memory",
            3: "Global",
            4: "Tag"
        }
        self.EXTERNAL_FUNCTION = 0
        self.EXTERNAL_TABLE = 1
        self.EXTERNAL_MEMORY = 2
        self.EXTERNAL_GLOBAL = 3
        self.EXTERNAL_TAG = 4

    def analyze_wasm_stack_types(self, instructions, initial_locals=None, debug=False):
        """
        分析 WASM 指令并返回：
        1. 当前栈上的剩余类型列表
        2. 缺失的栈参数数量 (underflow count)

        Args:
            instructions: 指令列表
            initial_locals: (可选) 初始局部变量类型字典
            debug: 是否打印每步详情

        Returns:
            tuple: (stack_list, missing_count)
                   stack_list: ['i32', 'i32', ...]
                   missing_count: int (例如 2 表示该块需要从外部获取 2 个参数)
        """

        # 当前的值栈
        stack = []

        # 记录缺失的栈参数数量
        missing_count = 0

        # 局部变量类型推断记录
        locals_map = initial_locals.copy() if initial_locals else {}

        # --- 辅助函数：弹栈并统计缺失 ---
        def pop_stack(n=1):
            nonlocal missing_count
            popped = []
            for _ in range(n):
                if not stack:
                    # 栈是空的，说明需要外部参数
                    missing_count += 1
                    if debug: print(f"  -> Stack underflow! Missing req: {missing_count}")
                    # 使用占位符，保证后续逻辑不崩溃
                    popped.append('underflow_val')
                else:
                    popped.append(stack.pop())
            # WASM 栈是后进先出，pop 出来的顺序是 [栈顶, 栈顶-1...]
            # 对于二元运算 add(a, b)，栈顶是 b，下面是 a
            return popped

        if debug:
            print(f"{'Instruction':<25} | {'Op Inputs':<15} | {'Stack After'}")
            print("-" * 65)

        for inst in instructions:
            opcode = inst[0]
            parts = opcode.split('.')
            category = parts[0]  # i32, f64, local, etc.

            # --- 1. 常量 (Push 1) ---
            if 'const' in opcode:
                stack.append(category)

            # --- 2. 变量操作 ---
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
            elif opcode == 'global.get':  # 0x23
                # 警告：这里假设全局变量都是 i32，如果你的 wasm 里有 i64 全局变量，这里会出错
                # 正确做法是解析 Global Section
                stack.append('i32')
            elif opcode == 'call':  # 0x10
                func_index = inst[1]['val'] if isinstance(inst[1], dict) else inst[1]

                # 这里的逻辑需要你提供一个 self.func_signatures 字典
                # 格式: { func_index: ([param_types], [return_types]) }
                if hasattr(self, 'func_signatures'):
                    params, returns = self.func_signatures.get(func_index, ([], []))
                    pop_stack(len(params))
                    for ret_type in returns:
                        stack.append(ret_type)
                else:
                    print(f"⚠️ 警告: 未知函数 {func_index} 的签名，无法分析栈变化！")
                    # 如果你只是为了跑通 base64.wasm，且知道它调用的函数返回什么，可以在这里手动 hack
                    # 例如: if func_index == X: stack.append('i32')
            elif opcode == 'local.tee':
                val_type = stack[-1] if stack else 'unknown'
                # 如果栈空 tee 也会触发 pop 检查
                if not stack:
                    # 这是一个特殊情况，tee 既读又写，如果不处理会导致逻辑混乱
                    # 但通常 pop_stack(1) 然后 push 回去即可
                    vals = pop_stack(1)  # 这会增加 missing_count
                    stack.append(vals[0])  # 马上推回去
                    val_type = vals[0]

                idx = inst[1]['val'] if isinstance(inst[1], dict) else inst[1]
                locals_map[idx] = val_type

            elif opcode == 'drop':
                pop_stack(1)

            elif opcode == 'select':
                # Pop 3: val1, val2, cond
                popped = pop_stack(3)
                # 简单的类型推断：取 val1 的类型
                result_type = popped[2] if len(popped) >= 3 else 'unknown'
                if result_type == 'underflow_val': result_type = 'unknown'
                stack.append(result_type)

            # --- 3. 内存加载 (Load) ---
            elif 'load' in opcode:
                pop_stack(1)  # Pop addr
                stack.append(category)

            # --- 4. 内存存储 (Store) ---
            elif 'store' in opcode:
                pop_stack(2)  # Pop val, Pop addr

            # --- 5. 比较运算 (Compare) ---
            elif any(x in opcode for x in ['eqz', 'eq', 'ne', 'lt', 'gt', 'le', 'ge']):
                if 'eqz' in opcode:
                    pop_stack(1)
                else:
                    pop_stack(2)
                stack.append('i32')  # 结果总是 i32

            # --- 6. 算术运算 (Arithmetic) ---
            elif any(x in opcode for x in ['add', 'sub', 'mul', 'div', 'rem', 'and', 'or', 'xor', 'shl', 'shr', 'rot']):
                pop_stack(2)
                stack.append(category)

            elif any(x in opcode for x in ['clz', 'ctz', 'popcnt', 'abs', 'neg', 'ceil', 'floor', 'sqrt']):
                pop_stack(1)
                stack.append(category)

            # --- 7. 类型转换 ---
            elif 'wrap' in opcode or 'extend' in opcode or 'convert' in opcode or 'trunc' in opcode:
                pop_stack(1)
                stack.append(category)

            # --- 8. 控制流 ---
            elif opcode == 'if':
                pop_stack(1)  # Condition

            elif opcode == 'br_if':
                pop_stack(1)  # Condition

            elif opcode == 'br_table':
                pop_stack(1)  # Index

            # 调试打印
            if debug:
                print(f"{opcode:<25} | {str(stack[-3:]):<15} (top)")

        # 返回元组：(剩余栈列表, 缺失参数数量)
        return stack, missing_count

    def _get_op_stack_effect(self, opcode_name, operands, locals_types=None):
        """
        计算指令的栈影响 (pops, pushes)
        返回: (pop_types, push_types)
        对于多态指令 (drop, select, local.set/tee unknown)，pop_types 可能包含 'any'。
        """
        name = opcode_name
        parts = name.split('.')
        category = parts[0] # i32, f64, local, memory, etc.
        
        # 1. 常量
        if 'const' in name:
            return [], [category]
            
        # 2. 变量操作
        elif name == 'local.get':
            idx = operands[0]['val'] if isinstance(operands[0], dict) else operands[0]
            if locals_types and idx in locals_types:
                return [], [locals_types[idx]]
            return [], ['unknown']
            
        elif name == 'local.set':
            idx = operands[0]['val'] if isinstance(operands[0], dict) else operands[0]
            if locals_types and idx in locals_types:
                return [locals_types[idx]], []
            return ['any'], [] # 允许匹配任意栈顶
            
        elif name == 'local.tee':
            idx = operands[0]['val'] if isinstance(operands[0], dict) else operands[0]
            t = 'any'
            if locals_types and idx in locals_types:
                t = locals_types[idx]
            return [t], [t]
            
        elif name == 'global.get':
            return [], ['unknown']
        elif name == 'global.set':
            return ['unknown'], []
            
        # 3. 内存操作
        elif 'load' in name:
            return ['i32'], [category]
            
        elif 'store' in name:
            return [category, 'i32'], []
            
        elif name == 'memory.size':
            return [], ['i32']
        elif name == 'memory.grow':
            return ['i32'], ['i32']
            
        # 4. 控制流
        elif name in ['block', 'loop', 'if']:
            block_type = operands[0] if operands else 0x40
            
            pops = []
            pushes = []
            
            if name == 'if':
                pops.append('i32') # condition
                
            if block_type == 0x40: # void
                pass
            elif block_type in self.VALUE_TYPE_NAMES: # 单个返回值
                pushes.append(self.VALUE_TYPE_NAMES[block_type])
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
            func_idx = operands[0] if operands else 0
            if hasattr(self, 'func_signatures'):
                params, returns = self.func_signatures.get(func_idx, ([], []))
                return list(params), list(returns)
            return [], []
            
        elif name == 'call_indirect':
            return ['any', 'i32'], ['any']
            
        # 5. 比较运算
        elif any(x in name for x in ['eq', 'ne', 'lt', 'gt', 'le', 'ge']):
            if 'eqz' in name:
                return [category], ['i32']
            return [category, category], ['i32']
            
        # 6. 算术/位运算
        elif any(x in name for x in ['add', 'sub', 'mul', 'div', 'rem', 'and', 'or', 'xor', 'shl', 'shr', 'rot']):
            return [category, category], [category]
            
        # 7. 一元运算
        elif any(x in name for x in ['clz', 'ctz', 'popcnt', 'abs', 'neg', 'ceil', 'floor', 'sqrt', 'trunc', 'nearest']):
            return [category], [category]
            
        # 8. 类型转换
        elif 'wrap' in name: return ['i64'], ['i32']
        elif 'extend' in name: return ['i32'], ['i64']
        elif 'promote' in name: return ['f32'], ['f64']
        elif 'demote' in name: return ['f64'], ['f32']
        elif 'convert' in name:
            src = 'i32' if 'i32' in name else 'i64'
            return [src], [category]
        elif 'reinterpret' in name:
            src = 'i32' if 'i32' in name else ('i64' if 'i64' in name else ('f32' if 'f32' in name else 'f64'))
            if category == 'f32': src = 'i32'
            elif category == 'i32': src = 'f32'
            elif category == 'f64': src = 'i64'
            elif category == 'i64': src = 'f64'
            return [src], [category]
            
        return [], []

    def analyze_wasm_ast(self, instructions, locals_types=None, initial_stack=None):
        """
        将扁平的指令列表解析为 AST 结构，并进行两轮分析以推断类型。
        Pass 1: 推断局部变量类型
        Pass 2: 生成 AST
        
        Args:
            instructions: 指令列表
            locals_types: 初始局部变量类型
            initial_stack: 初始栈状态 ["i32", "i64"] (列表尾部为栈顶)
        """
        
        # --- Pass 1: Inference ---
        inferred_locals = locals_types.copy() if locals_types else {}
        
        # 简单的栈元素对象，用于追踪来源
        class StackValue:
            def __init__(self, type_name, sources=None):
                self.type = type_name
                self.sources = sources or set() # set of local indices
                
        cursor = 0
        total_instrs = len(instructions)
        
        def run_inference(current_stack, stop_at_else=False):
            nonlocal cursor
            
            while cursor < total_instrs:
                inst = instructions[cursor]
                cursor += 1
                name = inst[0]
                operands = inst[2]
                
                # 获取静态影响 (使用当前已知的 inferred_locals)
                static_pops, static_pushes = self._get_op_stack_effect(name, operands, inferred_locals)
                
                # Pop Phase
                popped_values = []
                for required_type in reversed(static_pops):
                    val = None
                    if current_stack:
                        val = current_stack.pop()
                    else:
                        val = StackValue('unknown') # Underflow
                        
                    popped_values.insert(0, val)
                    
                    # Inference Logic: Consumer Constraints
                    # 如果指令需要特定类型 (e.g. i32.add)，且 pop 的值来源是 unknown 的 local，则推断该 local 为 i32
                    if required_type != 'any' and required_type != 'unknown':
                        if val.type == 'unknown' or val.type == 'any':
                            for src_local in val.sources:
                                if src_local not in inferred_locals:
                                    inferred_locals[src_local] = required_type
                                    
                # Inference Logic: Producer Constraints (local.set)
                if name == 'local.set' or name == 'local.tee':
                    idx = operands[0]['val'] if isinstance(operands[0], dict) else operands[0]
                    # pop 的值决定了 local 的类型
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
                        # 如果 local 类型已知，t 就是那个类型，否则是 unknown
                        if idx in inferred_locals:
                            t = inferred_locals[idx]
                            
                    elif name == 'local.tee':
                        # tee 传递来源
                        if popped_values:
                            sources = popped_values[0].sources
                            
                    elif name == 'select':
                        # select 传递来源 (合并?)
                        pass
                        
                    current_stack.append(StackValue(t, sources))
                    
                # Control Flow Recursion
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
                    
        # Run Pass 1
        saved_cursor = cursor
        
        # Prepare initial inference stack
        inference_stack = []
        if initial_stack:
            for t in initial_stack:
                inference_stack.append(StackValue(t))
                
        try:
            run_inference(inference_stack)
        except Exception as e:
            print(f"Inference warning: {e}")
            
        # --- Pass 2: Generation (AST) ---
        cursor = 0 # Reset cursor
        
        def parse_sequence(current_stack, stop_at_else=False):
            nonlocal cursor
            nodes = []
            
            while cursor < total_instrs:
                inst = instructions[cursor]
                cursor += 1
                
                name = inst[0]
                opcode = inst[1]
                operands = inst[2]
                
                # 使用 inferred_locals 获取更准确的静态影响
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
                    if len(actual_pops) >= 1:
                        res_type = actual_pops[0]
                        actual_pushes.append(res_type)
                        current_stack.append(res_type)
                    else:
                        actual_pushes.append('unknown')
                        current_stack.append('unknown')
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
                    'else_children': []
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

        # Prepare initial generation stack
        generation_stack = list(initial_stack) if initial_stack else []
        return parse_sequence(generation_stack)

    def get_opcode_name(self, opcode):
        return self.WASM_OPCODES.get(opcode, f"unknown_0x{opcode:02x}")

    def decode_module_header(self, bytes_data, offset):
        if len(bytes_data) < 8: return
        magic_word = bytes_data[offset:offset + 4]
        if magic_word != self.WASM_MAGIC: raise ValueError("Invalid Magic")
        version = bytes_data[offset + 4:offset + 8]
        if version != self.WASM_VERSION: raise ValueError("Invalid Version")
        print(f"✓ Magic & Version Valid")

    # =========================================================================
    # LEB128 Utils
    # =========================================================================

    def write_leb128_unsigned(self, val, min_bytes=0):
        if val < 0: val = 0
        result = bytearray()
        while True:
            byte = val & 0x7F
            val >>= 7
            if val == 0 and (len(result) + 1) >= min_bytes:
                result.append(byte)
                break
            else:
                byte |= 0x80
                result.append(byte)
        return bytes(result)

    def read_leb128_unsigned(self, data, offset):
        result = 0
        shift = 0
        bytes_read = 0
        while True:
            if offset + bytes_read >= len(data): break
            byte = data[offset + bytes_read]
            bytes_read += 1
            result |= (byte & 0x7F) << shift
            if (byte & 0x80) == 0:
                break
            shift += 7
        return result, bytes_read

    def write_leb128_signed(self, val, min_bytes=0):
        val = int(val)
        result = bytearray()
        while True:
            byte = val & 0x7F
            val >>= 7
            is_termination_val = (val == 0 and (byte & 0x40) == 0) or \
                                 (val == -1 and (byte & 0x40) != 0)
            current_len = len(result) + 1
            if is_termination_val and current_len >= min_bytes:
                result.append(byte)
                break
            else:
                byte |= 0x80
                result.append(byte)
        return bytes(result)

    def read_leb128_signed(self, data, offset):
        result = 0
        shift = 0
        count = 0
        byte = 0
        while True:
            if offset + count >= len(data): break
            byte = data[offset + count]
            result |= (byte & 0x7F) << shift
            count += 1
            shift += 7
            if not (byte & 0x80):
                break

        # FIX: Removed `and shift < 64` check.
        # This ensures we correctly sign-extend even if the number was padded beyond 64 bits (e.g. 10 bytes).
        if byte & 0x40:
            result |= (~0 << shift)

        return result, count

    def read_next_section(self, offset):
        if offset >= len(self.wasm_data): return False, offset
        section_id = self.wasm_data[offset]
        offset += 1
        section_length, length_bytes = self.read_leb128_unsigned(self.wasm_data, offset)
        offset += length_bytes
        section_info = {
            'section_id': section_id,
            'data': self.wasm_data[offset:offset + section_length],
        }
        offset += section_length
        return section_info, offset

    def _pack_operand(self, val, length):
        return {'val': val, 'len': length}

    def _extract_operand(self, operand):
        if isinstance(operand, dict):
            return operand['val'], operand.get('len', 0)
        return operand, 0

    # =========================================================================
    # Decoder with Raw Bytes Capture
    # =========================================================================

    def decode_code_section(self, section_data):
        payload_data = section_data['data']
        offset = 0
        function_codes = []

        if offset >= len(payload_data): return function_codes

        functions_count, bytes_read = self.read_leb128_unsigned(payload_data, offset)
        offset += bytes_read

        for i in range(functions_count):
            if offset >= len(payload_data): break

            function_code = {'index': i, 'locals': [], 'code': []}

            body_size, tb = self.read_leb128_unsigned(payload_data, offset)
            offset += tb
            body_end = offset + body_size
            body_data = payload_data[offset: body_end]
            offset = body_end

            # Locals parsing and raw capture
            b_offset = 0
            locals_start = b_offset  # 记录 Locals 区域开始偏移

            # 读取局部变量组数量
            local_decl_count, lb = self.read_leb128_unsigned(body_data, b_offset)
            b_offset += lb
            # 保存数量的字节长度，用于还原 Padding
            function_code['locals_count_len'] = lb

            for _ in range(local_decl_count):
                local_cnt, lc_b = self.read_leb128_unsigned(body_data, b_offset)
                b_offset += lc_b
                local_type = body_data[b_offset]
                b_offset += 1
                # 保存每个 local 数量的字节长度
                function_code['locals'].append({'count': local_cnt, 'type': local_type, 'len': lc_b})

            # 捕获整个 Locals 区域的原始字节
            function_code['locals_raw'] = body_data[locals_start:b_offset]

            # Instructions
            instruction_bytes = body_data[b_offset:]
            instr_offset = 0
            block_start_opcodes = [0x02, 0x03, 0x04]

            while instr_offset < len(instruction_bytes):
                # 记录指令开始偏移，用于捕获原始字节
                start_offset = instr_offset

                opcode = instruction_bytes[instr_offset]
                opcode_name = self.get_opcode_name(opcode)
                instr_offset += 1
                operand_int_list = []

                # Block types
                if opcode in block_start_opcodes:
                    block_type = instruction_bytes[instr_offset]
                    instr_offset += 1
                    operand_int_list = [block_type]

                # Indices (Local, Global, Call, etc)
                elif opcode in [0x20, 0x21, 0x22, 0x23, 0x24, 0x10, 0x0C, 0x0D, 0x25, 0x26]:
                    idx, idx_bytes = self.read_leb128_unsigned(instruction_bytes, instr_offset)
                    instr_offset += idx_bytes
                    operand_int_list = [self._pack_operand(idx, idx_bytes)]

                elif opcode == 0x11:  # Call Indirect
                    type_idx, b1 = self.read_leb128_unsigned(instruction_bytes, instr_offset)
                    instr_offset += b1
                    table_idx, b2 = self.read_leb128_unsigned(instruction_bytes, instr_offset)
                    instr_offset += b2
                    operand_int_list = [self._pack_operand(type_idx, b1), self._pack_operand(table_idx, b2)]

                elif opcode == 0x0E:  # Br Table
                    target_cnt, b = self.read_leb128_unsigned(instruction_bytes, instr_offset)
                    instr_offset += b
                    operand_int_list.append(self._pack_operand(target_cnt, b))
                    for _ in range(target_cnt):
                        t, tb = self.read_leb128_unsigned(instruction_bytes, instr_offset)
                        instr_offset += tb
                        operand_int_list.append(self._pack_operand(t, tb))
                    def_idx, db = self.read_leb128_unsigned(instruction_bytes, instr_offset)
                    instr_offset += db
                    operand_int_list.append(self._pack_operand(def_idx, db))

                elif opcode in [0x3F, 0x40]:  # Memory
                    m, b = self.read_leb128_unsigned(instruction_bytes, instr_offset)
                    instr_offset += b
                    operand_int_list = [self._pack_operand(m, b)]

                elif opcode == 0x41:  # i32.const
                    val, val_bytes = self.read_leb128_signed(instruction_bytes, instr_offset)
                    instr_offset += val_bytes
                    operand_int_list = [self._pack_operand(val, val_bytes)]
                elif opcode == 0x42:  # i64.const
                    val, val_bytes = self.read_leb128_signed(instruction_bytes, instr_offset)
                    instr_offset += val_bytes
                    operand_int_list = [self._pack_operand(val, val_bytes)]

                elif opcode in [0x43, 0x44]:  # float
                    size = 4 if opcode == 0x43 else 8
                    raw = instruction_bytes[instr_offset:instr_offset + size]
                    instr_offset += size
                    operand_int_list = [raw]

                elif 0x28 <= opcode <= 0x3E:  # Load/Store
                    align, b1 = self.read_leb128_unsigned(instruction_bytes, instr_offset)
                    instr_offset += b1
                    offset_mem, b2 = self.read_leb128_unsigned(instruction_bytes, instr_offset)
                    instr_offset += b2
                    operand_int_list = [self._pack_operand(align, b1), self._pack_operand(offset_mem, b2)]
                    print()

                elif opcode == 0xFC:  # Bulk Memory
                    sub_opcode, sub_b = self.read_leb128_unsigned(instruction_bytes, instr_offset)
                    instr_offset += sub_b
                    args = []
                    if sub_opcode == 10:  # memory.copy
                        d, b1 = self.read_leb128_unsigned(instruction_bytes, instr_offset)
                        instr_offset += b1
                        s, b2 = self.read_leb128_unsigned(instruction_bytes, instr_offset)
                        instr_offset += b2
                        args = [self._pack_operand(d, b1), self._pack_operand(s, b2)]
                    elif sub_opcode == 11:  # memory.fill
                        m, b1 = self.read_leb128_unsigned(instruction_bytes, instr_offset)
                        instr_offset += b1
                        args = [self._pack_operand(m, b1)]
                    elif sub_opcode == 8:  # memory.init
                        seg, b1 = self.read_leb128_unsigned(instruction_bytes, instr_offset)
                        instr_offset += b1
                        mem, b2 = self.read_leb128_unsigned(instruction_bytes, instr_offset)
                        instr_offset += b2
                        args = [self._pack_operand(seg, b1), self._pack_operand(mem, b2)]
                    elif sub_opcode == 9:  # data.drop
                        seg, b1 = self.read_leb128_unsigned(instruction_bytes, instr_offset)
                        instr_offset += b1
                        args = [self._pack_operand(seg, b1)]
                    operand_int_list = [self._pack_operand(sub_opcode, sub_b), args]

                # === 捕获原始字节 ===
                end_offset = instr_offset
                raw_bytes = instruction_bytes[start_offset:end_offset]

                # 存储: [名称, Opcode, 操作数, 原始字节]
                function_code['code'].append([opcode_name, opcode, operand_int_list, raw_bytes])

            function_codes.append(function_code)

        return function_codes

    # =========================================================================
    # Encoder with Verification
    # =========================================================================

    def encode_code_section(self, function_codes):
        final_buffer = bytearray()
        final_buffer.extend(self.write_leb128_unsigned(len(function_codes)))
        block_start_opcodes = [0x02, 0x03, 0x04]

        has_error = False

        for func_idx, func in enumerate(function_codes):
            body_buffer = bytearray()

            # === Locals Encoding & Verification ===
            locals_buffer = bytearray()

            # 1. 编码 locals 组的数量 (支持 Padding)
            locals_count_len = func.get('locals_count_len', 0)
            locals_buffer.extend(self.write_leb128_unsigned(len(func['locals']), min_bytes=locals_count_len))

            for local in func['locals']:
                # 2. 编码每个组的变量数量 (支持 Padding)
                local_len = local.get('len', 0)
                locals_buffer.extend(self.write_leb128_unsigned(local['count'], min_bytes=local_len))
                locals_buffer.append(local['type'])

            # 3. 校验 Locals 原始字节
            if 'locals_raw' in func:
                if locals_buffer != func['locals_raw']:
                    if not has_error:  # 只打印第一个错误以免刷屏
                        print(f"\n[Error] Locals Mismatch Detected!")
                        print(f"  Func Index: {func_idx}")
                        print(f"  Original : {func['locals_raw'].hex().upper()}")
                        print(f"  Generated: {locals_buffer.hex().upper()}")
                        has_error = True

            # 加入主 buffer
            body_buffer.extend(locals_buffer)

            # Code Instruction Encoding
            for instr_idx, instr in enumerate(func['code']):
                opcode = instr[1]
                operands = instr[2]
                original_bytes = instr[3]  # 取出原始字节

                # 使用临时 buffer 生成当前指令
                temp_buf = bytearray()
                temp_buf.append(opcode)
                # if opcode == 0x00:
                #     temp_buf.append(opcode)

                if opcode in block_start_opcodes:
                    temp_buf.append(operands[0])

                elif opcode in [0x20, 0x21, 0x22, 0x23, 0x24, 0x10, 0x0C, 0x0D, 0x25, 0x26]:
                    val, length = self._extract_operand(operands[0])
                    temp_buf.extend(self.write_leb128_unsigned(val, min_bytes=length))

                elif opcode == 0x11:
                    val1, len1 = self._extract_operand(operands[0])
                    val2, len2 = self._extract_operand(operands[1])
                    temp_buf.extend(self.write_leb128_unsigned(val1, min_bytes=len1))
                    temp_buf.extend(self.write_leb128_unsigned(val2, min_bytes=len2))

                elif opcode == 0x0E:
                    cnt, cnt_len = self._extract_operand(operands[0])
                    temp_buf.extend(self.write_leb128_unsigned(cnt, min_bytes=cnt_len))
                    targets = operands[1:-1]
                    for t_op in targets:
                        t_val, t_len = self._extract_operand(t_op)
                        temp_buf.extend(self.write_leb128_unsigned(t_val, min_bytes=t_len))
                    def_val, def_len = self._extract_operand(operands[-1])
                    temp_buf.extend(self.write_leb128_unsigned(def_val, min_bytes=def_len))

                elif opcode in [0x3F, 0x40]:
                    val, length = self._extract_operand(operands[0] if operands else 0)
                    temp_buf.extend(self.write_leb128_unsigned(val, min_bytes=length))

                elif opcode in [0x41, 0x42]:
                    val, length = self._extract_operand(operands[0])
                    temp_buf.extend(self.write_leb128_signed(val, min_bytes=length))

                elif opcode in [0x43, 0x44]:
                    temp_buf.extend(operands[0])

                elif 0x28 <= opcode <= 0x3E:
                    val1, len1 = self._extract_operand(operands[0])
                    val2, len2 = self._extract_operand(operands[1])
                    temp_buf.extend(self.write_leb128_unsigned(val1, min_bytes=len1))
                    temp_buf.extend(self.write_leb128_unsigned(val2, min_bytes=len2))

                elif opcode == 0xFC:
                    sub_val, sub_len = self._extract_operand(operands[0])
                    temp_buf.extend(self.write_leb128_unsigned(sub_val, min_bytes=sub_len))
                    args = operands[1]
                    for arg in args:
                        val, length = self._extract_operand(arg)
                        temp_buf.extend(self.write_leb128_unsigned(val, min_bytes=length))

                # === 验证环节 ===
                # 比较 temp_buf 和 original_bytes
                # if temp_buf != original_bytes:
                #     if not has_error:  # 只打印前几个错误以免刷屏
                #         print(f"\n[Error] Mismatch Detected!")
                #         print(f"  Func Index: {func_idx}")
                #         print(f"  Instr Index: {instr_idx}")
                #         print(f"  Opcode: {instr[0]} (0x{opcode:02X})")
                #         print(f"  Original : {original_bytes.hex().upper()}")
                #         print(f"  Generated: {temp_buf.hex().upper()}")
                #         has_error = True

                body_buffer.extend(temp_buf)

            final_buffer.extend(self.write_leb128_unsigned(len(body_buffer)))
            final_buffer.extend(body_buffer)

        # if not has_error:
        #     print("✓ 所有指令字节校验通过！")
        # else:
        #     print("⚠️ 存在字节不匹配，请检查上方日志。")

        return bytes(final_buffer)

    def is_metadata_segment(self, segment_data):
        """
        检测数据段是否包含类型元数据字符串（用于 embind）
        如果包含，则不应该加密
        """
        # 常见的 embind 类型字符串特征
        metadata_keywords = [
            b'std::',
            b'emscripten',
            b'unsigned',
            b'basic_string',
            b'exception',
            b'typeinfo',
            b'double',
            b'float',
            b'bool',
            b'void',
            b'catching',
        ]
        
        # 如果数据段太小(< 100字节)，可能不是元数据段
        if len(segment_data) < 100:
            return False
        
        # 检查前 500 字节是否包含多个元数据关键词
        sample = segment_data[:500]
        keyword_count = sum(1 for kw in metadata_keywords if kw in sample)
        
        # 如果包含 3 个或以上关键词，认为是元数据段
        return keyword_count >= 3

    def obfuscate_data_section(self, section_info, xor_key):
        """
        全段混淆 Data Section。
        只针对 Active Segment (Mode 0 & 2) 进行加密，并返回元数据供 _start 解密使用。

        :param section_info: 原始 section 字典
        :param xor_key: 混淆用的 key (int)
        :return: (modified_bytes, segment_configs)
                 segment_configs 是一个列表: [{'start': 1024, 'len': 16}, ...]
        """
        print(f"\n{'=' * 20} 开始智能混淆 Data 段 {'=' * 20}")

        payload = bytearray(section_info['data'])
        offset = 0
        segment_configs = []  # 用于记录被加密的段信息，以便 _start 解密

        # 1. 读取段的数量
        count, read_len = self.read_leb128_unsigned(payload, offset)
        offset += read_len
        # if count> 1:
        #     count = 1
        print(f"-> 发现 {count} 个数据段")

        # 2. 遍历每个数据段
        for i in range(count):
            if offset >= len(payload): break

            # --- 解析 Segment Header ---
            mode = payload[offset]
            offset += 1

            mem_offset_val = 0
            is_active = False  # 标记当前段是否需要加密

            # 模式处理
            if mode == 0:  # Active (最常见)
                is_active = True
                # 解析 offset (i32.const)
                if payload[offset] == 0x41:  # i32.const
                    offset += 1
                    val, val_len = self.read_leb128_signed(payload, offset)
                    mem_offset_val = val
                    offset += val_len
                    if payload[offset] == 0x0B:  # END
                        offset += 1
                    else:
                        print(f"⚠️ Seg {i}: Offset 表达式异常 (无 END)，跳过加密")
                        is_active = False
                else:
                    print(f"⚠️ Seg {i}: Offset 不是 i32.const，太复杂不支持，跳过")
                    is_active = False  # 如果用了 global.get 等复杂指令，暂不支持自动加密



            elif mode == 1:  # Passive
                # Passive 段没有 offset，是被动调用的，不能在 _start 预先解密
                print(f"ℹ️ Seg {i}: Passive 模式，跳过")
                is_active = False

            elif mode == 2:  # Active with Memory Index
                is_active = True
                # 跳过 memory index
                _, mem_idx_len = self.read_leb128_unsigned(payload, offset)
                offset += mem_idx_len
                # 解析 Offset (同 Mode 0)
                if payload[offset] == 0x41:
                    offset += 1
                    val, val_len = self.read_leb128_signed(payload, offset)
                    mem_offset_val = val
                    offset += val_len
                    offset += 1  # END
                else:
                    is_active = False

            # --- 解析 Data 本体 ---
            data_size, size_len = self.read_leb128_unsigned(payload, offset)
            # if data_size >=100:
            #     data_size = 100

            offset += size_len
            
            # 获取数据内容用于检测
            segment_data = payload[offset:offset + data_size]

            # --- 执行加密前的智能检测 ---
            if is_active and data_size > 0:
                # 检查是否是元数据段
                # if self.is_metadata_segment(segment_data):
                #     print(f"   ⚠️ 跳过 Segment {i}: 检测到 embind 元数据 (地址 {mem_offset_val}, 长度 {data_size})")
                #     is_active = False  # 不加密
                # else:
                #     print(f"   🔥 加密 Segment {i}: 内存地址 {mem_offset_val} (0x{mem_offset_val:X}), 长度 {data_size}")
                # 原地异或修改
                for j in range(data_size):
                    payload[offset + j] ^= xor_key

                # 记录配置，供代码注入使用
                segment_configs.append({
                    'start': offset,
                    'len': data_size
                })
                break
            else:
                if is_active:
                    print(f"   Empty Segment {i}, skip.")

            # 移动 offset 跳过数据部分，准备处理下一个段
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
        ying_code.append([shangyib_code, self.add_instr(0x0C, self.pack_op(2)) , 0, "end"]) # 如果执行到最后就break
        random.shuffle(ying_code)

        new_code.append(self.add_instr(0x02, 0x40)) # block
        new_code.append(self.add_instr(0x41, self.pack_op(frist_come_code)))  # i32.const frist_come_code
        new_code.append(self.add_instr(0x21, self.pack_op(need_jbbl)))  # local.set need_jbbl

        new_code.append(self.add_instr(0x41, self.pack_op(self.can_safe_mem)))  # i32.const can_safe_mem
        new_code.append(self.add_instr(0x21, self.pack_op(save_start_addr_local)))  # local.set save_start_addr_local


        new_code.append(self.add_instr(0x41, self.pack_op(0)))  # i32.const 0
        new_code.append(self.add_instr(0x21, self.pack_op(save_idx_addr_local)))  # local.set save_idx_addr_local


        new_code.append(self.add_instr(0x03, 0x40))  # loop                  (开启一个循环标签，用于继续循环)
        len_ying_code = len(ying_code)

        def get_else(myshuz, idx_ying_code):
            if idx_ying_code >= len_ying_code:
                # myshuz.append(self.add_instr(0x01))
                # myshuz.append(self.add_instr(0x0B))
                return
            ying_cd = ying_code[idx_ying_code]
            myshuz.append(self.add_instr(0x20, self.pack_op(need_jbbl)))  # local.get need_jbbl
            myshuz.append(self.add_instr(0x41, self.pack_op(ying_cd[0])))  # i32.const ying_cd[0]

            myshuz.append(self.add_instr(0x46))

            starck_list, need_param = self.analyze_wasm_stack_types([ying_cd[1]])
            print("==>开始")
            print(ying_cd[1])
            print("starck_list,need_param==>", starck_list, need_param)
            myshuz.append(self.add_instr(0x04, 0x40))  # if

            # --- 测试 ---
            myshuz.append(self.add_instr(0x41, self.pack_op(1)))
            myshuz.append(self.add_instr(0x20, self.pack_op(need_jbbl)))  # local.get need_jbbl
            myshuz.append(self.add_instr(0x46));  # i32.eq
            myshuz.append(self.add_instr(0x04, 0x40))
            # --- 循环条件检查 ---
            # if len == 0 break
            myshuz.append(self.add_instr(0x20, self.pack_op(save_start_addr_local)))  # local.get start
            myshuz.append(self.add_instr(0x20, self.pack_op(save_start_addr_local)))  # local.get start
            myshuz.append(self.add_instr(0x36, [self.pack_op(0), self.pack_op(0)]))  # i32.store

            myshuz.append(self.add_instr(0x20, self.pack_op(1)))
            myshuz.append(self.add_instr(0x20, self.pack_op(need_jbbl)))  # local.get need_jbbl
            myshuz.append(self.add_instr(0x47));  # i32.eqz               (判断 len 是否等于 0)
            myshuz.append(self.add_instr(0x0D, self.pack_op(idx_ying_code + 3)))  # br_if 1               (如果等于0，跳出 block [depth 1])
            myshuz.append(self.add_instr(0x0C, self.pack_op(0)))

            # jeb崩溃
            # add_instr(0x21, pack_op(2));  # local.set 2
            # add_instr(0x21, pack_op(2));  # local.set 2
            # add_instr(0x21, pack_op(2));  # local.set 2

            myshuz.append(self.add_instr(0x0B))  # end                   (block 结束标记)

            #--- 测试结束 ---

            if ying_cd[-1] != 'end':
                myshuz.append(self.add_instr(0x41, self.pack_op(ying_cd[2]))) # 需要增加 ^ 混淆
                myshuz.append(self.add_instr(0x21, self.pack_op(need_jbbl)))  # local.set need_jbbl
            # ✅ 从内存栈中弹出（读取）需要的参数
            # 重要：只有当栈中有数据时才读取（idx > 0）
            # 如果栈为空（idx == 0），说明这是初始指令，不需要从内存读取
            for param_i in range(need_param):
                # 1. 减少栈指针
                myshuz.append(self.add_instr(0x20, self.pack_op(save_idx_addr_local)))  # local.get idx
                myshuz.append(
                    self.add_instr(0x41, self.pack_op(need_param - param_i)))  # i32.const need_param + param_i
                myshuz.append(self.add_instr(0x6B))  # i32.sub
                # myshuz.append(self.add_instr(0x22, self.pack_op(save_idx_addr_local)))  # local.tee idx (保存并保留在栈上)

                # 2. 计算地址: StartAddr + (idx * 4)
                myshuz.append(self.add_instr(0x41, self.pack_op(4)))  # i32.const 4
                myshuz.append(self.add_instr(0x6C))  # i32.mul
                myshuz.append(self.add_instr(0x20, self.pack_op(save_start_addr_local)))  # local.get start
                myshuz.append(self.add_instr(0x6A))  # i32.add

                # 3. 从内存读取
                myshuz.append(self.add_instr(0x28, [self.pack_op(0), self.pack_op(0)]))  # i32.load
            if need_param > 0:
                myshuz.append(self.add_instr(0x20, self.pack_op(save_idx_addr_local)))  # local.get idx
                myshuz.append(self.add_instr(0x41, self.pack_op(need_param)))  # i32.const need_param
                myshuz.append(self.add_instr(0x6B))  # i32.sub
                myshuz.append(self.add_instr(0x21, self.pack_op(save_idx_addr_local)))  # local.set temp

            print(f"      → 已添加 {need_param} 个参数的安全读取逻辑")
            if ying_cd[-1] != 'end':
                myshuz.append(ying_cd[1])  # 如果是跳转语句的话需要跳转的层数需要增加2层
            else:
                myshuz.append(self.add_instr(0x0C, self.pack_op(2 + idx_ying_code)))
            # myshuz.append(self.add_instr(0x0C, self.pack_op(1)) ) # br 1 类似continue
            for i in range(len(starck_list)):
                val_type = starck_list[i]

                # ---------------------------------------------------------
                # 1. 暂存结果 (Pop Value)
                # ---------------------------------------------------------
                # 因为我们要计算地址，必须先把挡在栈顶的计算结果拿开
                myshuz.append(self.add_instr(0x21, self.pack_op(temp_val_local)))  # local.set temp

                # ---------------------------------------------------------
                # 2. 计算写入地址: StartAddr + (CurrentCount * 4)
                # ---------------------------------------------------------
                # 注意：这里不需要减 1，因为 Count 指向的是下一个空位，直接写进去即可

                myshuz.append(self.add_instr(0x20, self.pack_op(save_start_addr_local)))  # local.get start
                myshuz.append(
                    self.add_instr(0x20, self.pack_op(save_idx_addr_local)))  # local.get idx (Current Count)

                # 计算偏移量: Count * 4 (假设是 i32)
                myshuz.append(self.add_instr(0x41, self.pack_op(4)))  # i32.const 4
                myshuz.append(self.add_instr(0x6C))  # i32.mul

                # 基址 + 偏移
                myshuz.append(self.add_instr(0x6A))  # i32.add

                # 此时栈状态: [TargetAddress]

                # ---------------------------------------------------------
                # 3. 取回数值 (Push Value)
                # ---------------------------------------------------------
                myshuz.append(self.add_instr(0x20, self.pack_op(temp_val_local)))  # local.get temp

                # 此时栈状态: [TargetAddress, Value] -> 符合 store 的要求

                # ---------------------------------------------------------
                # 4. 写入内存
                # ---------------------------------------------------------

                myshuz.append(self.add_instr(0x36, [self.pack_op(0), self.pack_op(0)]))  # i32.store

                # ---------------------------------------------------------
                # 5. 更新计数 (Count++)
                # ---------------------------------------------------------
                # 写入了一个数据，栈指针 + 1
                myshuz.append(self.add_instr(0x20, self.pack_op(save_idx_addr_local)))  # local.get idx
                myshuz.append(self.add_instr(0x41, self.pack_op(1)))  # i32.const 1
                myshuz.append(self.add_instr(0x6A))  # i32.add
                myshuz.append(self.add_instr(0x21, self.pack_op(save_idx_addr_local)))  # local.set idx
            # myshuz.append(self.add_instr(0x0C, self.pack_op(1)))  # br 1                  (跳转回 loop 开头 [depth 1])
            myshuz.append(self.add_instr(0x05))
            get_else(myshuz, idx_ying_code+1)
            myshuz.append(self.add_instr(0x0B))

        get_else(new_code, 0)



        new_code.append(self.add_instr(0x0C, self.pack_op(0)))
        new_code.append(self.add_instr(0x0B))
        new_code.append(self.add_instr(0x0B))
        return new_code, need_jbbl









    def pack_op(self, val):
        return {'val': val, 'len': 0}

    def add_instr(self, opcode, operands=None):
        name = self.get_opcode_name(opcode)
        raw = bytearray([opcode])

        ops_list = []
        if operands is not None:
            if isinstance(operands, list):
                ops_list = operands
            else:
                ops_list = [operands]

        # 简单的 Raw Bytes 生成 (仅用于注入的已知指令)
        if opcode in [0x02, 0x03]:  # Block/Loop
            raw.append(operands)  # 0x40
        elif opcode == 0x41:  # i32.const
            raw.extend(self.write_leb128_signed(operands['val']))
        elif opcode in [0x20, 0x21, 0x0D, 0x0C, 0x10]:  # Index
            raw.extend(self.write_leb128_unsigned(operands['val']))
        elif opcode in [0x2D, 0x3A]:  # Load/Store
            raw.extend(b'\x00\x00')  # align=0, offset=0

        return [name, opcode, ops_list, bytes(raw)]
    def _gen_decryption_instrs(self, segment_configs, xor_key, original_start_idx=None):
        """生成解密函数的结构化数据"""
        instructions = []

        def add_instr(opcode, operands=None):
            name = self.get_opcode_name(opcode)
            raw = bytearray([opcode])

            ops_list = []
            if operands is not None:
                if isinstance(operands, list):
                    ops_list = operands
                else:
                    ops_list = [operands]

            # 简单的 Raw Bytes 生成 (仅用于注入的已知指令)
            if opcode in [0x02, 0x03]:  # Block/Loop
                raw.append(operands)  # 0x40
            elif opcode == 0x41:  # i32.const
                raw.extend(self.write_leb128_signed(operands['val']))
            elif opcode in [0x20, 0x21, 0x0D, 0x0C, 0x10]:  # Index
                raw.extend(self.write_leb128_unsigned(operands['val']))
            elif opcode in [0x2D, 0x3A]:  # Load/Store
                raw.extend(b'\x00\x00')  # align=0, offset=0

            instructions.append([name, opcode, ops_list, bytes(raw)])

        def pack_op(val):
            return {'val': val, 'len': 0}

        # Locals: 2 个 i32 (ptr, len)
        locals_list = [{'count': 3+4, 'type': 0x7F, 'len': 1}]

        # Body
        for seg in segment_configs:
            start_addr = seg['start']
            length = seg['len']

            # --- 初始化变量 ---
            # ptr = start (Local 0)
            add_instr(0x41, pack_op(start_addr));  # i32.const start_addr  (压入起始地址)
            add_instr(0x21, pack_op(0))  # local.set 0           (保存到局部变量0: ptr)

            # len = length (Local 1)
            add_instr(0x41, pack_op(length));  # i32.const length      (压入长度)
            add_instr(0x21, pack_op(1))  # local.set 1           (保存到局部变量1: len)

            # --- 循环结构 ---
            # Block & Loop 结构用于控制流跳转
            add_instr(0x02, 0x40);  # block                 (开启一个块，用于跳出循环)
            add_instr(0x03, 0x40)  # loop                  (开启一个循环标签，用于继续循环)

            # --- 测试 ---
            add_instr(0x41, pack_op(1));  #
            add_instr(0x41, pack_op(1));  #
            add_instr(0x04, 0x40); # if
            # --- 循环条件检查 ---
            # if len == 0 break
            add_instr(0x20, pack_op(1));  # local.get 1           (获取 len)
            add_instr(0x45);  # i32.eqz               (判断 len 是否等于 0)
            add_instr(0x0D, pack_op(2))  # br_if 1               (如果等于0，跳出 block [depth 1])
            add_instr(0x0C, pack_op(0))

            # jeb崩溃
            # add_instr(0x21, pack_op(2));  # local.set 2
            # add_instr(0x21, pack_op(2));  # local.set 2
            # add_instr(0x21, pack_op(2));  # local.set 2


            add_instr(0x0B)  # end                   (block 结束标记)




            # # --- 循环条件检查 ---
            # # if len == 0 break
            # add_instr(0x20, pack_op(1));  # local.get 1           (获取 len)
            # add_instr(0x45);  # i32.eqz               (判断 len 是否等于 0)
            # add_instr(0x0D, pack_op(1))  # br_if 1               (如果等于0，跳出 block [depth 1])

            # --- 解密逻辑: mem[ptr] = mem[ptr] ^ key ---
            # 1. 准备存储地址
            add_instr(0x20, pack_op(0))  # local.get 0           (获取 ptr，作为 store 的地址)
            # 2. 准备存储的值 (先读取，再异或)
            add_instr(0x20, pack_op(0));  # local.get 0           (获取 ptr，作为 load 的地址)


            add_instr(0x2D, [pack_op(0), pack_op(0)])  # i32.load8_u 0 0       (读取内存一字节: mem[ptr])

            add_instr(0x41, pack_op(xor_key));  # i32.const xor_key     (压入密钥)


            add_instr(0x73)  # i32.xor               (执行异或: mem[ptr] ^ key)



            # 3. 执行存储
            add_instr(0x3A, [pack_op(0), pack_op(0)])  # i32.store8 0 0        (将异或结果写回: mem[ptr] = result)




            # --- 变量更新 ---
            # ptr++
            add_instr(0x20, pack_op(0));  # local.get 0           (获取 ptr)
            add_instr(0x41, pack_op(1));  # i32.const 1           (压入 1)
            add_instr(0x6A);  # i32.add               (计算 ptr + 1)
            add_instr(0x21, pack_op(0))  # local.set 0           (更新 ptr)

            # len--
            add_instr(0x20, pack_op(1));  # local.get 1           (获取 len)
            add_instr(0x41, pack_op(1));  # i32.const 1           (压入 1)
            add_instr(0x6B);  # i32.sub               (计算 len - 1)
            add_instr(0x21, pack_op(1))  # local.set 1           (更新 len)





            # --- 循环尾部 ---
            # continue
            add_instr(0x0C, pack_op(0))  # br 0                  (跳转回 loop 开头 [depth 0])
            add_instr(0x0B);  # end                   (loop 结束标记)
            add_instr(0x0B)  # end                   (block 结束标记)

        # ✅ 启用控制流混淆
        # 注意：我们只混淆解密循环的核心部分（不包括循环条件判断）
        # 这样可以保持循环结构清晰，同时增加核心逻辑的复杂度
        print(f"   [混淆] 正在对解密循环核心逻辑应用控制流混淆...")
        
        # 选择要混淆的指令范围：从循环体内部开始到循环结束前
        # instructions[14:20] 大约是解密的核心代码（load, xor, store, ptr++, len--）
        core_instructions = instructions[14:20]  # 核心解密逻辑
        
        if len(core_instructions) > 0:
            jmzl, locals_new = self.kozhilc(core_instructions, locals_list[0]['count']-1)
            instructions_new = instructions[0:14] + jmzl + instructions[20:]
            instructions = instructions_new
            print(f"   [混淆] ✓ 已混淆 {len(core_instructions)} 条指令")
        else:
            print(f"   [混淆] ⚠ 跳过混淆（指令数不足）")


        # Call Original Start if exists
        if original_start_idx is not None:
            print(f"   ↪ [Code] 注入指令: call {original_start_idx}")
            add_instr(0x10, pack_op(original_start_idx))

        add_instr(0x0B)  # End Func

        return [{
            'index': 0,
            'locals': locals_list,
            'locals_count_len': 1,
            'code': instructions
        }]
    def read_utf8_string(self,data, offset):
        """
        读取 UTF-8 字符串（LEB128 长度前缀）
        对应 V8: consume_string

        :param data: 字节数据
        :param offset: 当前偏移
        :return: (字符串, 总字节数)
        """
        # 读取字符串长度
        string_length, length_bytes = self.read_leb128_unsigned(data, offset)
        offset += length_bytes

        # 读取字符串内容
        if string_length > 0:
            string_data = data[offset:offset + string_length]
            try:
                string_value = string_data.decode('utf-8')
            except UnicodeDecodeError:
                string_value = f"<invalid UTF-8: {string_data.hex()}>"
        else:
            string_value = ""

        total_bytes = length_bytes + string_length
        return string_value, total_bytes

    def decode_import_section(self,payload_data):
        """
        解析 Import Section (节 ID = 2)
        对应 V8: module-decoder.cc 中的 DecodeImportSection (第 758 行)

        Import Section 声明模块需要从外部导入的资源

        :param payload_data: Import Section 的 payload 数据
        :return: 解析出的导入列表
        """

        # 第 759-760 行：读取导入数量
        import_count, bytes_read = self.read_leb128_unsigned(payload_data, 0)
        offset = bytes_read


        imports = []

        # 第 762-858 行：遍历每个导入项
        for i in range(import_count):
            if offset >= len(payload_data):
                break


            # 第 774 行：读取模块名
            module_name, mb = self.read_utf8_string(payload_data, offset)
            offset += mb

            # 第 775 行：读取字段名
            field_name, fb = self.read_utf8_string(payload_data, offset)
            offset += fb
            # 第 776-777 行：读取导入类型
            if offset >= len(payload_data):
                break
            import_kind = payload_data[offset]
            offset += 1
            kind_name = self.IMPORT_EXPORT_KIND_NAMES.get(import_kind, f"Unknown(0x{import_kind:02x})")

            import_desc = {
                'index': i,
                'module_name': module_name,
                'field_name': field_name,
                'kind': import_kind,
                'kind_name': kind_name
            }

            # 第 778-857 行：根据类型解析导入描述
            if import_kind == self.EXTERNAL_FUNCTION:
                # 第 779-794 行：导入函数
                # 读取类型索引（函数签名索引）
                type_index, tb = self.read_leb128_unsigned(payload_data, offset)
                offset += tb
                import_desc['type_index'] = type_index

            elif import_kind == self.EXTERNAL_TABLE:
                # 第 796-816 行：导入表
                # 读取表的元素类型
                if offset >= len(payload_data):
                    break
                elem_type = payload_data[offset]
                offset += 1
                type_name = self.VALUE_TYPE_NAMES.get(elem_type, f"0x{elem_type:02x}")

                # 读取限制（初始大小、最大大小）
                if offset >= len(payload_data):
                    break
                flags = payload_data[offset]
                offset += 1
                has_max = (flags & 0x01) != 0

                initial_size, ib = self.read_leb128_unsigned(payload_data, offset)
                offset += ib

                if has_max:
                    max_size, maxb = self.read_leb128_unsigned(payload_data, offset)
                    offset += maxb
                    # print(f"  │  │  └─ Maximum size: {max_size}")
                # else:
                #     print(f"  │  │  └─ Maximum size: (unbounded)")

                import_desc.update({
                    'elem_type': type_name,
                    'initial_size': initial_size,
                    'has_max': has_max
                })

            elif import_kind == self.EXTERNAL_MEMORY:
                # 第 818-827 行：导入内存
                # 读取限制标志
                if offset >= len(payload_data):
                    break
                flags = payload_data[offset]
                offset += 1
                has_max = (flags & 0x01) != 0
                is_shared = (flags & 0x02) != 0
                is_memory64 = (flags & 0x04) != 0

                # 读取初始页数
                initial_pages, ib = self.read_leb128_unsigned(payload_data, offset)
                offset += ib
                # print(f"  │  │  ├─ Initial pages: {initial_pages} ({initial_pages * 65536} bytes)")

                if has_max:
                    max_pages, maxb = self.read_leb128_unsigned(payload_data, offset)
                    offset += maxb
                    # print(f"  │  │  ├─ Maximum pages: {max_pages} ({max_pages * 65536} bytes)")
                # else:
                #     print(f"  │  │  ├─ Maximum pages: (unbounded)")

                # if is_shared:
                #     print(f"  │  │  ├─ Shared: yes")
                # if is_memory64:
                #     print(f"  │  │  └─ Memory64: yes")
                # else:
                #     print(f"  │  │  └─ Memory type: 32-bit")

                import_desc.update({
                    'initial_pages': initial_pages,
                    'has_max': has_max,
                    'is_shared': is_shared,
                    'is_memory64': is_memory64
                })

            elif import_kind == self.EXTERNAL_GLOBAL:
                # 第 829-839 行：导入全局变量
                # 读取值类型
                if offset >= len(payload_data):
                    break
                value_type = payload_data[offset]
                offset += 1
                type_name = self.VALUE_TYPE_NAMES.get(value_type, f"0x{value_type:02x}")

                # 读取可变性
                if offset >= len(payload_data):
                    break
                mutability = payload_data[offset]
                offset += 1
                is_mutable = mutability == 1

                import_desc.update({
                    'value_type': type_name,
                    'mutable': is_mutable
                })

            elif import_kind == self.EXTERNAL_TAG:
                # 第 841-852 行：导入标签（异常处理）
                # 读取属性（通常被忽略）
                if offset >= len(payload_data):
                    break
                attribute = payload_data[offset]
                offset += 1

                # 读取标签签名索引
                tag_sig_index, tb = self.read_leb128_unsigned(payload_data, offset)
                offset += tb

                import_desc['tag_sig_index'] = tag_sig_index

            else:
                # 第 854-856 行：未知类型
                print(f"⚠ Unknown import kind: 0x{import_kind:02x}")

            imports.append(import_desc)


        # 统计导入的函数数量（用于计算函数索引偏移）
        global module_imported_func_count
        imported_func_count = sum(1 for imp in imports if imp['kind'] == self.EXTERNAL_FUNCTION)
        module_imported_func_count = imported_func_count
        print(f"  │     Note: 其中 {imported_func_count} 个是函数导入")

        return imports

    def decode_export_section(self,payload_data):
        """
        解析 Export Section (节 7)
        对应 V8: module-decoder.cc 第 946-1017 行的 DecodeExportSection()

        Export Section 定义了模块向外部暴露的资源

        格式：
          export_section ::= export_count:u32 export*
          export ::= name:name kind:byte index:u32

        其中 kind 可以是：
          0x00 = Function (导出函数)
          0x01 = Table (导出表)
          0x02 = Memory (导出内存)
          0x03 = Global (导出全局变量)
          0x04 = Tag (导出标签，用于异常处理)

        :param payload_data: Export Section 的 payload 数据
        :return: 导出项列表
        """
        offset = 0

        exports = []


        # 第 947-948 行：读取导出项数量
        if offset >= len(payload_data):
            print(f"Error: Insufficient data for export count")
            return exports

        export_count, bytes_read = self.read_leb128_unsigned(payload_data, offset)
        offset += bytes_read
        print(f"Export count: {export_count}")

        # 第 950-1017 行：遍历每个导出项
        for i in range(export_count):


            export_info = {
                'index': i,
                'name': '',
                'kind': 0,
                'kind_name': '',
                'export_index': 0
            }

            # 第 961 行：读取导出名称（字符串）
            # consume_string: 读取 LEB128 长度 + UTF-8 字符串
            name, tb = self.read_utf8_string(payload_data, offset)
            offset += tb
            export_info['name'] = name

            # 第 964 行：读取导出类型（1 字节）
            # exp->kind = consume_u8("export kind")

            export_kind = payload_data[offset]
            offset += 1
            kind_name = self.IMPORT_EXPORT_KIND_NAMES.get(export_kind, f"Unknown(0x{export_kind:02x})")
            export_info['kind'] = export_kind
            export_info['kind_name'] = kind_name

            # 第 965-1015 行：根据导出类型读取索引
            # switch (exp->kind) { ... }
            if export_kind == self.EXTERNAL_FUNCTION:
                # 第 966-979 行：导出函数
                # exp->index = consume_func_index(...)
                func_index, tb = self.read_leb128_unsigned(payload_data, offset)
                offset += tb
                export_info['export_index'] = func_index

            elif export_kind == self.EXTERNAL_TABLE:
                # 第 980-985 行：导出表
                # exp->index = consume_table_index(...)
                table_index, tb = self.read_leb128_unsigned(payload_data, offset)
                offset += tb
                export_info['export_index'] = table_index

            elif export_kind == self.EXTERNAL_MEMORY:
                # 第 986-995 行：导出内存
                # uint32_t index = consume_u32v("memory index")
                mem_index, tb = self.read_leb128_unsigned(payload_data, offset)
                offset += tb
                export_info['export_index'] = mem_index
                # 第 990-991 行：WASM 1.0 只支持一个内存（索引必须为 0）

            elif export_kind == self.EXTERNAL_GLOBAL:
                # 第 996-1003 行：导出全局变量
                global_index, tb = self.read_leb128_unsigned(payload_data, offset)
                offset += tb
                export_info['export_index'] = global_index

            elif export_kind == self.EXTERNAL_TAG:
                # 第 1004-1012 行：导出标签（异常处理）
                # exp->index = consume_tag_index(...)
                tag_index, tb = self.read_leb128_unsigned(payload_data, offset)
                offset += tb
                export_info['export_index'] = tag_index

            else:
                # 第 1013-1015 行：无效的导出类型
                break

            exports.append(export_info)


        # 收集导出的函数名（用于在 Code Section 显示）
        for exp in exports:
            if exp['kind'] == self.EXTERNAL_FUNCTION:
                func_index = exp['export_index']
                func_name = exp['name']
                self.module_function_names[func_index] = func_name

        return exports

    def ensure_memory_size(self, section_lists, required_size):
        """
        确保 Memory Section 有足够的初始页数来容纳所需的内存大小
        """
        # 计算需要的页数 (WASM 页大小为 64KB = 65536 bytes)
        PAGE_SIZE = 65536
        required_pages = (required_size + PAGE_SIZE - 1) // PAGE_SIZE
        
        # 找到 Memory Section (Section ID = 5)
        mem_sec = next((s for s in section_lists if s['section_id'] == 5), None)
        
        if mem_sec:
            payload = bytearray(mem_sec['data'])
            offset = 0
            
            # 读取内存数量 (通常为 1)
            mem_count, bytes_read = self.read_leb128_unsigned(payload, offset)
            offset += bytes_read
            
            # 读取 flags (bit 0: has_max, bit 1: is_shared, bit 2: is_memory64)
            flags = payload[offset]
            offset += 1
            has_max = (flags & 0x01) != 0
            
            # 读取初始页数
            initial_pages, ib = self.read_leb128_unsigned(payload, offset)
            offset += ib
            
            print(f"   [Memory] 当前初始页数: {initial_pages} ({initial_pages * PAGE_SIZE} bytes)")
            
            # 如果当前页数不够，增加页数
            if initial_pages < required_pages:
                print(f"   [Memory] 需要增加到: {required_pages} 页 ({required_pages * PAGE_SIZE} bytes)")
                
                # 重新构建 Memory Section
                new_payload = bytearray()
                new_payload.extend(self.write_leb128_unsigned(mem_count))
                new_payload.append(flags)
                new_payload.extend(self.write_leb128_unsigned(required_pages))
                
                if has_max:
                    max_pages, maxb = self.read_leb128_unsigned(payload, offset)
                    # 确保 max_pages 也足够大
                    if max_pages < required_pages:
                        max_pages = required_pages + 10  # 留一些余量
                    new_payload.extend(self.write_leb128_unsigned(max_pages))
                
                mem_sec['data'] = bytes(new_payload)
                print(f"   [Memory] ✓ 已更新 Memory Section")
            else:
                print(f"   [Memory] ✓ 当前内存足够")
        else:
            print(f"   [Memory] ⚠ 未找到 Memory Section，可能是导入的内存")

    def find_safe_data_offset(self, section_lists):
        """
        扫描 Data 段，寻找已被占用的最大内存地址，返回一个安全的空闲起始地址。
        """
        max_used_offset = 0

        # 找到 Data Section
        data_sec = next((s for s in section_lists if s['section_id'] == 11), None)

        if not data_sec:
            # 如果没有 Data 段，通常保留前 1KB (防止 NULL 指针解引用等)，返回 1024
            print("   [Memory Scan] 未发现 Data 段，默认起始地址: 1024")
            return 1024

        payload = data_sec['data']
        offset = 0

        # 读取段数量
        count, read_len = self.read_leb128_unsigned(payload, offset)
        offset += read_len

        for i in range(count):
            if offset >= len(payload): break

            # 读取段模式 (Mode)
            mode = payload[offset]
            offset += 1

            mem_offset_val = 0
            is_active = False

            # 只关心 Active 段 (Mode 0 & 2)
            if mode == 0:
                is_active = True
                if payload[offset] == 0x41:  # i32.const
                    offset += 1
                    val, val_len = self.read_leb128_signed(payload, offset)
                    mem_offset_val = val
                    offset += val_len
                    offset += 1  # END (0x0B)
                else:
                    # 如果是 global.get 等复杂指令，无法静态计算，只能保守跳过
                    print(f"   [Memory Scan] Seg {i}: Offset 复杂，无法计算")
                    is_active = False  # 无法计算，暂且忽略
                    # 这里的 offset 处理会比较麻烦，因为不知道指令长度，
                    # 实际项目中需完善 opcode 解析，这里简化处理跳过直到找到 size

            elif mode == 1:  # Passive
                is_active = False

            elif mode == 2:  # Active with mem idx
                is_active = True
                _, mem_idx_len = self.read_leb128_unsigned(payload, offset)  # mem idx
                offset += mem_idx_len
                if payload[offset] == 0x41:
                    offset += 1
                    val, val_len = self.read_leb128_signed(payload, offset)
                    mem_offset_val = val
                    offset += val_len
                    offset += 1  # END
                else:
                    is_active = False

            # 读取数据长度
            data_size, size_len = self.read_leb128_unsigned(payload, offset)
            offset += size_len

            # 计算结束地址
            if is_active:
                end_addr = mem_offset_val + data_size
                if end_addr > max_used_offset:
                    max_used_offset = end_addr

            # 跳过数据内容
            offset += data_size

        # 加上一点 Padding (例如 16 字节对齐)
        safe_addr = (max_used_offset + 15) & ~15
        if safe_addr == 0: safe_addr = 1024  # 避免 0 地址

        print(f"   [Memory Scan] 检测到最大静态地址: {max_used_offset}, 推荐安全地址: {safe_addr}")
        return safe_addr

    def obfuscate_code_section(self, function_codes, need_change, CONF_KEY):
        """
        在 Code Section 中查找 _start 函数，并注入解密逻辑。
        """
        if not need_change:
            return

        for idx, function_code in enumerate(function_codes):
            # 计算当前函数在全局索引空间中的位置 (Imports 数量 + 当前 Code 段索引)
            newidx = len(self.imports) + idx

            # 判断是否是 _start 导出函数
            if newidx in self.module_function_names and self.module_function_names[newidx] == "_start":
                print(f"   ↪ 注入解密逻辑到函数: {self.module_function_names[newidx]} (Idx: {newidx})")

                # 1. 生成解密用的 AST
                # original_start_idx=None 表示我们不生成 Call 指令，只生成解密循环
                # 因为我们是直接把代码插在原函数头部，跑完解密自然会往下执行原逻辑
                dec_func_struct_list = self._gen_decryption_instrs(need_change, CONF_KEY, original_start_idx=None)
                dec_func = dec_func_struct_list[0]

                dec_instrs = dec_func['code']
                dec_locals = dec_func['locals']  # 通常包含 ptr(0) 和 len(1)

                # 2. 移除生成的 'end' 指令 (0x0B)
                # 因为我们要把代码插在前面，不能让函数提前结束
                if dec_instrs and dec_instrs[-1][1] == 0x0B:
                    dec_instrs.pop()

                # 3. 计算原函数现有的局部变量数量 (用于变量重定位)
                # 我们把解密用的变量追加到最后，防止冲突
                # 假设 _start 没有参数 (Standard WASI _start is ()->())
                current_locals_count = 0
                for loc in function_code['locals']:
                    current_locals_count += loc['count']

                # 新变量的起始索引
                ptr_idx = current_locals_count  # 原来的 local 0 变成这个
                len_idx = current_locals_count + 1  # 原来的 local 1 变成这个

                # 4. 修正解密指令中的 Local Index
                # 遍历生成的指令，将 local.get/set 0 改为 ptr_idx，1 改为 len_idx
                for instr in dec_instrs:
                    opcode = instr[1]
                    # 0x20: local.get, 0x21: local.set, 0x22: local.tee
                    if opcode in [0x20, 0x21, 0x22]:
                        ops = instr[2]  # 操作数列表 [{'val': 0, 'len': 1}]
                        if ops:
                            old_val = ops[0]['val']
                            new_val = old_val

                            # 进行重映射
                            if old_val == 0:
                                new_val = ptr_idx
                            elif old_val == 1:
                                new_val = len_idx

                            # 重新生成 LEB128 字节
                            new_val_bytes = self.write_leb128_unsigned(new_val)

                            # 更新操作数对象
                            ops[0]['val'] = new_val
                            ops[0]['len'] = len(new_val_bytes)

                            # 更新指令的 raw_bytes (opcode + operand)
                            instr[3] = bytes([opcode]) + new_val_bytes

                # 5. 合并 Locals
                # 将解密用的 locals 追加到原函数 locals 列表后面
                function_code['locals'].extend(dec_locals)

                # 删除 locals_raw 缓存，强迫 encode_code_section 重新计算并生成二进制
                # 因为我们修改了 locals 列表结构
                if 'locals_raw' in function_code:
                    del function_code['locals_raw']

                # 6. 合并代码
                # 将解密指令插入到原函数代码的最前面
                function_code['code'] = dec_instrs + function_code['code']

                print(f"      [+] 已合并 {len(dec_instrs)} 条解密指令，新增变量索引 {ptr_idx}, {len_idx}")


        print()

    def inject_decryption_routine(self, section_lists, segment_configs, xor_key):
        print(f"\n{'=' * 20} 正在注入 Section 8 (Start) {'=' * 20}")

        # 1. Type Section: 确保有 ()->void
        type_sec = next((s for s in section_lists if s['section_id'] == 1), None)
        void_type_idx = 0
        target_sig = b'\x60\x00\x00'  # ()->void

        if type_sec:
            cnt, lb = self.read_leb128_unsigned(type_sec['data'], 0)
            void_type_idx = cnt
            new_data = bytearray()
            new_data.extend(self.write_leb128_unsigned(cnt + 1))
            new_data.extend(type_sec['data'][lb:])
            new_data.extend(target_sig)
            type_sec['data'] = new_data
        else:
            payload = bytearray(self.write_leb128_unsigned(1)) + target_sig
            section_lists.insert(0, {'section_id': 1, 'data': payload})

        # 2. 计算新函数的 Index
        imported_funcs = len(self.imports)
        func_sec = next((s for s in section_lists if s['section_id'] == 3), None)
        internal_count = 0
        if func_sec:
            internal_count, _ = self.read_leb128_unsigned(func_sec['data'], 0)

        new_func_idx = imported_funcs + internal_count
        print(f"-> 新增解密函数 Index: {new_func_idx}")

        # 3. Func Section: 声明新函数
        if func_sec:
            cnt, lb = self.read_leb128_unsigned(func_sec['data'], 0)
            new_data = bytearray()
            new_data.extend(self.write_leb128_unsigned(cnt + 1))
            new_data.extend(func_sec['data'][lb:])
            new_data.extend(self.write_leb128_unsigned(void_type_idx))
            func_sec['data'] = new_data
        else:
            # 简单处理：插在 Type 后面
            payload = bytearray(self.write_leb128_unsigned(1)) + self.write_leb128_unsigned(void_type_idx)
            section_lists.insert(1, {'section_id': 3, 'data': payload})

        # 4. Start Section: 关键逻辑
        start_sec = next((s for s in section_lists if s['section_id'] == 8), None)
        original_start_idx = None

        if start_sec:
            original_start_idx, _ = self.read_leb128_unsigned(start_sec['data'], 0)
            print(f"-> 发现原有 Start (Index {original_start_idx})，执行劫持")
            start_sec['data'] = self.write_leb128_unsigned(new_func_idx)
        else:
            print(f"-> 原本无 Start 段，新建 Start Section 指向 {new_func_idx}")
            payload = self.write_leb128_unsigned(new_func_idx)
            # 查找插入位置 (Export=7, Code=10)
            insert_pos = 0
            for i, s in enumerate(section_lists):
                if s['section_id'] < 8: insert_pos = i + 1
            section_lists.insert(insert_pos, {'section_id': 8, 'data': payload})

        # 5. Code Section: 插入函数体
        code_sec = next((s for s in section_lists if s['section_id'] == 10), None)
        if code_sec:
            # 先解码整个 Code 段
            parsed_funcs = self.function_codes

            # 生成新函数体 (包含 call original 逻辑)
            new_func_struct = self._gen_decryption_instrs(segment_configs, xor_key, original_start_idx)[0]

            # 追加到列表
            parsed_funcs.append(new_func_struct)

            # 重新编码
            code_sec['data'] = self.encode_code_section(parsed_funcs)
            print(f"-> Code 段已更新，当前函数总数: {len(parsed_funcs)}")
        else:
            raise ValueError("WASM 没有 Code 段，无法注入")
    def decode_module(self):
        if not self.wasm_data: return
        print(f"\n{'#' * 60}\n# 开始解析与重建 WASM 模块 (带字节验证)\n{'#' * 60}")

        offset = 0
        self.decode_module_header(self.wasm_data, offset)
        offset += 8

        section_lists = []
        while offset < len(self.wasm_data):
            section_info, offset = self.read_next_section(offset)
            if section_info == False: break
            section_lists.append(section_info)

        new_wasm = bytearray()
        new_wasm.extend(self.WASM_MAGIC)
        new_wasm.extend(self.WASM_VERSION)

        # === 混淆配置 ===
        # 请确保这里的配置与 inject_obfuscation 中的完全一致！
        CONF_KEY = 0x55
        # ===============

        need_change = []
        self.can_safe_mem = self.find_safe_data_offset(section_lists)
        
        # 计算需要的临时栈空间大小 (估算: 每个指令最多保存 10 个 i32 值)
        # 这里预留 4KB (1024 个 i32 值) 应该足够了
        stack_size = 4096
        required_memory_size = self.can_safe_mem + stack_size
        
        # 确保内存足够
        print(f"\n{'=' * 20} 检查并调整内存大小 {'=' * 20}")
        print(f"   需要的内存大小: {required_memory_size} bytes")
        self.ensure_memory_size(section_lists, required_memory_size)
        
        for section_info in section_lists:
            sec_id = section_info['section_id']
            payload = section_info['data']
            if sec_id == 2:
                # Import Section - 导入声明
                self.imports = self.decode_import_section(payload)
            elif sec_id == 7:
                # Import Section - 导入声明
                self.exports = self.decode_export_section(payload)
                print()
            if sec_id == 10:
                print(f"→ 处理 CODE 段")
                self.function_codes = self.decode_code_section(section_info)
                # self.obfuscate_code_section(function_codes, need_change, CONF_KEY)

                # payload = self.encode_code_section(function_codes)
            elif sec_id == 11:  # Data Section
                print(f"→ 处理 DATA 段 (智能混淆字符串数据)")
                # 调用智能混淆函数（会自动跳过元数据段）
                payload,need_change = self.obfuscate_data_section(section_info, CONF_KEY)
                section_info['data'] = payload
        # 2. 注入 Start 逻辑 (不管原文件结构如何)
        if need_change:
            self.inject_decryption_routine(section_lists, need_change, CONF_KEY)
        else:
            print("未发现有效 Data 段，跳过。")
        for section_info in section_lists:
            sec_id = section_info['section_id']
            payload = section_info['data']

            new_wasm.append(sec_id)
            new_wasm.extend(self.write_leb128_unsigned(len(payload)))
            new_wasm.extend(payload)

        output_filename = "base64.wasm"
        with open(output_filename, "wb") as f:
            f.write(new_wasm)
        print(f"\n✅ 成功生成新文件: {output_filename}")

if __name__ == '__main__':
    wasmjsq = JiexStart("base64_2.wasm")
    wasmjsq.decode_module()





