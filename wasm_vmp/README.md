# WasmVmp 项目重构文档

## 1. 重构概述
原有的 `new_jiex.py` 是一个包含所有逻辑的单文件脚本（约 2300 行），维护和扩展较为困难。本次重构将其拆分为多个模块，形成一个标准的 Python 包 `wasm_vmp`。

## 2. 项目结构

```
wasm_vmp/
├── __init__.py      # 包入口，导出核心类 JiexStart
├── core.py          # 核心逻辑 (JiexStart 类)，负责编排各模块
├── consts.py        # 常量定义 (WASM Opcode, Magic, Types)
├── utils.py         # 工具函数 (LEB128 编解码, 字符串读取)
├── codec.py         # 编解码模块 (Section 解析与生成)
├── analyzer.py      # 分析模块 (栈类型推断, AST 生成)
└── obfuscator.py    # 混淆模块 (Data 段加密, 代码注入, 控制流混淆)
```

## 3. 模块说明

### `consts.py`
存放所有静态常量，如 WASM 魔数、版本号、Opcode 映射表、Value Type 名称等。

### `utils.py`
存放通用的底层工具函数，主要是 LEB128 格式的读写函数 (`read_leb128_unsigned` 等) 和 helper 函数 (`add_instr`, `pack_op`)。

### `codec.py`
负责 WASM 文件格式的解析与封装。
- `WasmCodec` 类：包含 `decode_module_header`, `decode_code_section` 等方法。
- 处理 Section 的二进制读写。

### `analyzer.py`
负责代码分析。
- `WasmAnalyzer` 类：包含 `analyze_wasm_stack_types` (栈平衡分析) 和 `analyze_wasm_ast` (AST 生成与类型推断)。

### `obfuscator.py`
负责核心混淆逻辑。
- `WasmObfuscator` 类：
    - `obfuscate_data_section`: 智能加密 Data 段。
    - `kozhilc`: 控制流混淆算法。
    - `inject_decryption_routine`: 注入解密函数和 Start 劫持逻辑。
    - `_gen_decryption_instrs`: 生成解密用的 WASM指令。

### `core.py`
项目的主入口，包含 `JiexStart` 类。
- 初始化 `codec`, `analyzer`, `obfuscator` 实例。
- `decode_module()` 方法负责串联整个流程：解析 -> 分析 -> 混淆 -> 重组文件。

### `wasmvmp.py`
负责 WASM 虚拟化保护 (VMP)。
- `WasmVMP` 类：
    - 将原始 WASM 指令转换为自定义字节码。
    - 生成解释器循环 (Dispatch Loop) 和虚拟栈。
    - 支持控制流扁平化 (Control Flow Flattening)。
    - 实现了自定义的虚拟指令集 (VM Instructions)。

## 4. 如何使用

```python
from wasm_vmp import JiexStart

# 初始化并运行混淆
processor = JiexStart("input.wasm")
processor.decode_module() 
# output will be base64.wasm (default)
```
