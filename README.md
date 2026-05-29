# WASM-VMP: WebAssembly Virtual Machine Protection

**中文** | [English](README_EN.md)

一个强大的 WebAssembly 二进制混淆和保护工具，通过虚拟化、控制流扁平化和数据加密技术来保护 WASM 代码。
## 在线使用
https://wasm.tsvmp.com/
## 📋 目录

- [项目简介](#项目简介)
- [核心特性](#核心特性)
- [技术原理](#技术原理)
- [安装与使用](#安装与使用)
- [项目架构](#项目架构)
- [使用示例](#使用示例)
- [注意事项](#注意事项)
- [开发指南](#开发指南)
- [许可证](#许可证)

## 项目简介

WASM-VMP 是一个专业的 WebAssembly 代码保护工具，能够将标准的 WASM 二进制文件转换为高度混淆的版本，有效防止逆向工程和代码分析。该工具采用模块化设计，提供了命令行接口和 Web 界面两种使用方式。

### 适用场景

- 保护商业 WebAssembly 应用的核心算法
- 防止敏感业务逻辑被逆向分析
- 增加代码破解难度
- 保护知识产权

## 核心特性

### 1. 虚拟机保护 (VMP)
- **指令虚拟化**: 将原始 WASM 指令转换为自定义字节码
- **虚拟栈**: 在高内存区域（10MB+）创建独立的虚拟栈，避免与原始堆栈冲突
- **解释器循环**: 生成自定义的字节码解释器，运行时动态执行
- **选择性保护**: 支持指定特定函数进行虚拟化保护

### 2. 控制流混淆
- **控制流扁平化**: 使用二叉搜索树（BST）调度器打乱原始控制流
- **不透明谓词**: 插入始终为真/假的复杂条件判断
- **假代码块**: 注入永不执行的虚假 VMP 代码块
- **br_table 预处理**: 自动移除和转换复杂的分支表指令

### 3. 数据保护
- **数据段加密**: 使用 XOR 密钥加密所有数据段
- **运行时解密**: 注入解密函数，在模块启动时自动解密
- **Start 段劫持**: 修改 Start 段确保解密函数优先执行

### 4. 指令扩展
- **指令多态**: 将简单指令扩展为等价的复杂指令序列
- **常量混淆**: 使用数学运算隐藏常量值
- **可配置扩展因子**: 控制指令膨胀程度

### 5. 双重使用方式
- **命令行工具**: 适合批量处理和自动化集成
- **Web 界面**: 提供可视化操作，支持函数选择和实时进度查看

## 技术原理

### VMP 内存布局

```
低地址
├─ 0x000000    原始 WASM 堆栈和堆（通常 < 1MB）
├─ ...
├─ 0xA00000    VMP 虚拟栈起始地址（10MB）
├─ 0xA00000+   VMP 字节码数据段
└─ 高地址
```

### 函数索引系统

```
全局函数索引 = 导入函数数量 + 内部函数索引
```

- `codec.imported_func_count`: 跟踪导入函数数量
- `function_codes`: 仅包含内部函数体（不含导入）
- `func_signatures`: 映射函数索引到 (参数, 返回值) 元组

### VMP 工作流程

```
1. 解析模块
   ├─ 读取所有 Section
   ├─ 构建函数签名映射
   └─ 构建全局变量类型映射

2. 扫描目标函数
   ├─ 分析最大参数/返回值/局部变量数量
   └─ 确定 VMP 解释器所需资源

3. 注入全局 SP
   └─ 添加虚拟栈指针全局变量

4. 处理每个选定函数
   ├─ 预处理（移除 br_table）
   ├─ 编码为 VMP 字节码
   └─ 替换函数体为 VMP 调度器调用

5. 追加 VMP 解释器
   └─ 生成完整的字节码解释器函数

6. 注入 VMP 字节码
   └─ 作为数据段添加到高内存区域

7. 更新堆基址
   └─ 修改 __heap_base 指向 VMP 数据之后
```

### Section 重编码

修改后需要重新编码的 Section：

- **Type Section (ID 1)**: 添加新函数签名时
- **Function Section (ID 3)**: 函数添加/修改时
- **Global Section (ID 6)**: 注入 SP 全局变量时
- **Code Section (ID 10)**: 总是需要（函数体被修改）
- **Data Section (ID 11)**: 添加 VMP 字节码或加密数据时
- **Data Count Section (ID 12)**: 数据段数量变化时

## 安装与使用

### 环境要求

- Python 3.7+
- Flask（仅 Web 界面需要）

### 安装依赖

```bash
# 如果使用 Web 界面
pip install flask
```

### 命令行使用

#### 基础用法

```python
from wasm_vmp import JiexStart

# 处理整个 WASM 文件
processor = JiexStart('input.wasm')
processor.parse_module()
processor.encrypt_module('output.wasm', not_jeb=True)
```

#### 选择性函数保护

```python
# 仅保护特定函数（按全局索引）
processor = JiexStart('input.wasm')
processor.parse_module()
processor.encrypt_module(
    'output.wasm',
    not_jeb=True,
    selected_functions=[2, 5, 10, 15]  # 函数索引列表
)
```

#### 快速测试

```bash
python test.py
# 处理 base64_2.wasm -> base64_2_vmp.wasm
```

### Web 界面使用

#### 启动服务器

```bash
python app.py
# 服务器运行在 http://0.0.0.0:25100
```

#### 使用流程

1. **上传文件**: 选择要保护的 .wasm 文件（最大 1MB）
2. **分析函数**: 系统自动解析并列出所有内部函数
3. **选择函数**: 勾选需要保护的函数（可选，默认全部）
4. **开始处理**: 点击加密按钮，后台异步处理
5. **下载结果**: 处理完成后下载保护后的文件

## 项目架构

### 核心模块 (`wasm_vmp/`)

```
wasm_vmp/
├── __init__.py                  # 包入口，导出 JiexStart
├── core.py                      # 核心编排器（JiexStart 类）
├── codec.py                     # WASM 编解码器（WasmCodec 类）
├── analyzer.py                  # 栈类型推断和 AST 生成（WasmAnalyzer 类）
├── obfuscator.py                # 数据加密和代码注入（WasmObfuscator 类）
├── wasmvmp.py                   # VMP 引擎（WasmVMP 类）
├── preprocessor.py              # 预处理转换（br_table 移除）
├── control_flow_flattener.py   # 控制流扁平化（BST 调度）
├── instructions_expander.py    # 指令扩展和多态
├── block_definitions.py        # 指令块定义
├── opaque_utils.py             # 不透明谓词生成
├── utils.py                    # LEB128 编解码和辅助函数
├── consts.py                   # WASM 操作码和常量定义
├── README.md                   # 中文重构文档
└── WASM_INSTRUCTIONS.md        # WASM 指令参考手册
```

### Web 应用

```
├── app.py                      # Flask 服务器（异步任务处理）
├── templates/
│   └── index.html             # Web UI
├── static/
│   └── script.js              # 前端逻辑
├── uploads/                   # 上传文件临时存储
└── outputs/                   # 处理后的输出文件
```

### 测试文件

```
├── test.py                    # 命令行测试脚本
├── base64_2.wasm             # 测试输入文件
└── base64_2_vmp.wasm         # 测试输出文件
```

## 使用示例

### 示例 1: 保护加密算法

```python
from wasm_vmp import JiexStart

# 假设函数 5-8 是核心加密算法
processor = JiexStart('crypto.wasm')
processor.parse_module()
processor.encrypt_module(
    'crypto_protected.wasm',
    not_jeb=True,
    selected_functions=[5, 6, 7, 8]
)
print("加密算法已保护")
```

### 示例 2: 批量处理

```python
import os
from wasm_vmp import JiexStart

input_dir = 'wasm_files/'
output_dir = 'protected_files/'

for filename in os.listdir(input_dir):
    if filename.endswith('.wasm'):
        input_path = os.path.join(input_dir, filename)
        output_path = os.path.join(output_dir, f'protected_{filename}')

        processor = JiexStart(input_path)
        processor.parse_module()
        processor.encrypt_module(output_path, not_jeb=True)
        print(f'已处理: {filename}')
```

### 示例 3: 集成到构建流程

```python
# build_script.py
import sys
from wasm_vmp import JiexStart

def protect_wasm(input_file, output_file, critical_functions=None):
    try:
        processor = JiexStart(input_file)
        processor.parse_module()
        processor.encrypt_module(
            output_file,
            not_jeb=True,
            selected_functions=critical_functions
        )
        return True
    except Exception as e:
        print(f"保护失败: {e}")
        return False

if __name__ == '__main__':
    if protect_wasm('build/app.wasm', 'dist/app.wasm', [10, 11, 12]):
        print("✓ WASM 保护成功")
        sys.exit(0)
    else:
        print("✗ WASM 保护失败")
        sys.exit(1)
```

## 注意事项

### ⚠️ 重要限制

1. **文件大小**: Web 界面限制上传文件最大 1MB
2. **内存占用**: VMP 会在 10MB 地址处分配虚拟栈，确保原始程序不使用该区域
3. **性能影响**: 虚拟化保护会显著降低执行速度（通常 10-100 倍）
4. **兼容性**: 某些高级 WASM 特性可能不完全支持（如 SIMD、多值返回）

### 🔒 安全建议

1. **选择性保护**: 仅对核心算法函数进行 VMP 保护，避免全局保护导致性能过差
2. **多层防护**: 结合数据加密、控制流混淆和指令扩展使用
3. **定期更新**: 混淆算法使用随机化，每次构建生成不同的保护代码
4. **测试验证**: 保护后务必进行功能测试，确保程序正常运行

### 📝 最佳实践

1. **识别关键函数**: 使用 Web 界面分析功能，查看函数大小和名称
2. **渐进式保护**: 先保护少量函数测试，确认无误后再扩大范围
3. **保留原始文件**: 始终保留未保护的原始 WASM 文件
4. **版本控制**: 不要将保护后的文件提交到版本控制系统

### 🐛 常见问题

**Q: 保护后的 WASM 文件无法运行？**
A: 检查是否选择了导入函数进行保护（导入函数不应被保护），或者原始文件是否依赖特定内存布局。

**Q: 文件体积增大很多？**
A: 这是正常现象。VMP 会注入解释器代码和字节码数据，通常会增加 2-5 倍体积。

**Q: 如何确定函数索引？**
A: 使用 Web 界面的分析功能，或者使用 `wasm-objdump` 等工具查看函数列表。

**Q: 可以多次保护同一个文件吗？**
A: 不建议。多次保护会导致性能急剧下降，且可能引入不稳定性。

## 开发指南

### 代码结构

项目采用模块化设计，从原始的 2300 行单文件重构而来：

- **core.py**: 主入口，协调各模块工作
- **codec.py**: 处理 WASM 二进制格式的底层读写
- **analyzer.py**: 进行栈平衡分析和类型推断
- **obfuscator.py**: 实现各种混淆技术
- **wasmvmp.py**: VMP 核心引擎

### 扩展开发

#### 添加新的混淆技术

```python
# 在 obfuscator.py 中添加新方法
class WasmObfuscator:
    def my_custom_obfuscation(self, function_code):
        # 实现自定义混淆逻辑
        pass

# 在 core.py 中调用
self.obfuscator.my_custom_obfuscation(func)
```

#### 自定义 VMP 指令

```python
# 在 wasmvmp.py 中扩展指令处理
def encode_custom_instruction(self, opcode, operands):
    # 生成自定义字节码
    pass
```

### 调试技巧

```python
# 启用详细日志
processor = JiexStart('input.wasm')
processor.parse_module()

# 查看函数签名
print(processor.analyzer.func_signatures)

# 查看全局变量类型
print(processor.analyzer.global_types)

# 导出中间结果
processor.codec.export_section_info('debug_sections.json')
```

## 许可证

本项目采用 Apache License 2.0 许可证。详见 [LICENSE](LICENSE) 文件。

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📧 联系方式

如有问题或建议，请通过 GitHub Issues 联系。

---

**免责声明**: 本工具仅用于合法的代码保护目的。使用者应遵守相关法律法规，不得用于非法用途。
