# WASM-VMP: WebAssembly Virtual Machine Protection

[中文](README.md) | **English**

A powerful WebAssembly binary obfuscation and protection tool that safeguards WASM code through virtualization, control flow flattening, and data encryption techniques.
## Safe loads and leaner construction

Native-memarg scalar load handlers, deduplication before body construction, and compact AST byte heights are integrated. Measured Base64 construction median drops about 80.9 → 62.0 ms (23% less time); flat depth-2048 AST allocation peak drops about 36.4 → 2.73 MB. MD5 runtime is broadly unchanged. See [regressions, measurements and limits](bench/verification_loads/README.md).

## Private VMP memory and semantic fixes

The previous **10 application-memory behavior differences are resolved**. Bytecode and frames use an unexported private memory; application limits, imports/exports and heap markers remain intact. The expanded strict official subset passes 168 modules / 8352 comparisons. See the [memory regression report](bench/verification_memory/README.md).

Outputs with application memory require a **multi-memory-capable runtime**; Node.js 24/V8 is verified. Post-trap instance reinitialization remains necessary. The sections below record earlier revisions.

## Sized frames and handler sharing

Typed peak operand-stack sizing replaces fixed 1024-byte frames; checked arena allocation prevents caller-frame and bytecode overwrites within valid compiled programs. Stable module-wide sharing merges equivalent generic handlers while retaining configurable variants. Protected output size drops about 34% for Base64 and 16% for MD5 at the same protection scope; MD5 runtime is broadly unchanged. See [regressions and resource limits](bench/verification_frames/README.md), including post-trap instance disposal and the remaining memory-semantics limitations.

## Binary syntax verification

76 official syntax suites, 1119 valid input modules, 2238 builds: all 2022 successful outputs pass WABT and V8, while 216 builds explicitly reject unsupported features. No invalid output remains in this corpus. Fixed start-function indexing with non-function imports and accidental deletion of global-initializer operand bytes. See the [syntax report and limits](bench/verification_syntax/README.md). Valid syntax does not establish runtime equivalence.

## Second optimization and compatibility checks (2026-11-09)

Direct local dispatch and bounded ID sampling improve MD5 runtime by another 1.7–1.8× over the first optimized version and construction by about 38× on the measured machine. Structured branch stack cleanup, implicit-function `br_if`, numeric types, and missing module sections are fixed. See the [results, reproduction commands, and limitations](bench/verification_v2/README.md).

187 fixture categories, three build seeds, MD5 and compiled Base64 regressions pass. The supported official subset passes for 132 modules. The broader official run retains 10 memory-semantics failures and rejects unsupported reference features. VMP reserves physical linear memory, affecting capacity and original out-of-bounds behavior; this is not full WASM conformance.

## USE
[https://wasm.tsvmp.com/](https://wasm.tsvmp.com/en/)
## 📋 Table of Contents

- [Overview](#overview)
- [Core Features](#core-features)
- [Technical Principles](#technical-principles)
- [Installation & Usage](#installation--usage)
- [Project Architecture](#project-architecture)
- [Usage Examples](#usage-examples)
- [Important Notes](#important-notes)
- [Development Guide](#development-guide)
- [License](#license)

## Overview

WASM-VMP is a professional WebAssembly code protection tool that transforms standard WASM binary files into highly obfuscated versions, effectively preventing reverse engineering and code analysis. The tool features a modular design and provides both command-line interface and web interface options.

### Use Cases

- Protect core algorithms in commercial WebAssembly applications
- Prevent reverse analysis of sensitive business logic
- Increase code cracking difficulty
- Protect intellectual property

## Core Features

### 1. Virtual Machine Protection (VMP)
- **Instruction Virtualization**: Converts original WASM instructions to custom bytecode
- **Virtual Stack**: Creates independent virtual stack in high memory region (10MB+) to avoid conflicts with original stack
- **Interpreter Loop**: Generates custom bytecode interpreter for runtime dynamic execution
- **Selective Protection**: Supports specifying particular functions for virtualization protection

### 2. Control Flow Obfuscation
- **Control Flow Flattening**: Disrupts original control flow using Binary Search Tree (BST) dispatcher
- **Opaque Predicates**: Inserts complex conditional checks that are always true/false
- **Fake Code Blocks**: Injects never-executed fake VMP code blocks
- **br_table Preprocessing**: Automatically removes and converts complex branch table instructions

### 3. Data Protection
- **Data Segment Encryption**: Encrypts all data segments using XOR keys
- **Runtime Decryption**: Injects decryption function that automatically decrypts on module startup
- **Start Section Hijacking**: Modifies Start section to ensure decryption function executes first

### 4. Instruction Expansion
- **Instruction Polymorphism**: Expands simple instructions into equivalent complex instruction sequences
- **Constant Obfuscation**: Hides constant values using mathematical operations
- **Configurable Expansion Factor**: Controls instruction inflation degree

### 5. Dual Usage Modes
- **Command-Line Tool**: Suitable for batch processing and automation integration
- **Web Interface**: Provides visual operation with function selection and real-time progress viewing

## Technical Principles

### VMP Memory Layout

```
Low Address
├─ 0x000000    Original WASM stack and heap (typically < 1MB)
├─ ...
├─ 0xA00000    VMP virtual stack start address (10MB)
├─ 0xA00000+   VMP bytecode data segment
└─ High Address
```

### Function Indexing System

```
Global Function Index = Imported Function Count + Internal Function Index
```

- `codec.imported_func_count`: Tracks number of imported functions
- `function_codes`: Contains only internal function bodies (excludes imports)
- `func_signatures`: Maps function indices to (params, results) tuples

### VMP Workflow

```
1. Parse Module
   ├─ Read all Sections
   ├─ Build function signature mapping
   └─ Build global variable type mapping

2. Scan Target Functions
   ├─ Analyze max params/results/locals count
   └─ Determine resources needed for VMP interpreter

3. Inject Global SP
   └─ Add virtual stack pointer global variable

4. Process Each Selected Function
   ├─ Preprocess (remove br_table)
   ├─ Encode to VMP bytecode
   └─ Replace function body with VMP dispatcher call

5. Append VMP Interpreter
   └─ Generate complete bytecode interpreter function

6. Inject VMP Bytecode
   └─ Add as data segment to high memory region

7. Update Heap Base
   └─ Modify __heap_base to point after VMP data
```

### Section Re-encoding

Sections that need re-encoding after modifications:

- **Type Section (ID 1)**: When new function signatures are added
- **Function Section (ID 3)**: When functions are added/modified
- **Global Section (ID 6)**: When SP global variable is injected
- **Code Section (ID 10)**: Always (function bodies are modified)
- **Data Section (ID 11)**: When VMP bytecode or encrypted data is added
- **Data Count Section (ID 12)**: When data segment count changes

## Installation & Usage

### Requirements

- Python 3.7+
- Flask (only for web interface)

### Install Dependencies

```bash
# If using web interface
pip install flask
```

### Command-Line Usage

#### Basic Usage

```python
from wasm_vmp import JiexStart

# Process entire WASM file
processor = JiexStart('input.wasm')
processor.parse_module()
processor.encrypt_module('output.wasm', not_jeb=True)
```

#### Selective Function Protection

```python
# Protect only specific functions (by global index)
processor = JiexStart('input.wasm')
processor.parse_module()
processor.encrypt_module(
    'output.wasm',
    not_jeb=True,
    selected_functions=[2, 5, 10, 15]  # Function index list
)
```

#### Quick Test

```bash
python test.py
# Processes base64_2.wasm -> base64_2_vmp.wasm
```

### Web Interface Usage

#### Start Server

```bash
python app.py
# Server runs at http://0.0.0.0:25100
```

#### Usage Flow

1. **Upload File**: Select .wasm file to protect (max 1MB)
2. **Analyze Functions**: System automatically parses and lists all internal functions
3. **Select Functions**: Check functions to protect (optional, defaults to all)
4. **Start Processing**: Click encrypt button for async background processing
5. **Download Result**: Download protected file after processing completes

## Project Architecture

### Core Modules (`wasm_vmp/`)

```
wasm_vmp/
├── __init__.py                  # Package entry, exports JiexStart
├── core.py                      # Core orchestrator (JiexStart class)
├── codec.py                     # WASM codec (WasmCodec class)
├── analyzer.py                  # Stack type inference and AST generation (WasmAnalyzer class)
├── obfuscator.py                # Data encryption and code injection (WasmObfuscator class)
├── wasmvmp.py                   # VMP engine (WasmVMP class)
├── preprocessor.py              # Preprocessing transformations (br_table removal)
├── control_flow_flattener.py   # Control flow flattening (BST dispatch)
├── instructions_expander.py    # Instruction expansion and polymorphism
├── block_definitions.py        # Instruction block definitions
├── opaque_utils.py             # Opaque predicate generation
├── utils.py                    # LEB128 encoding/decoding and helper functions
├── consts.py                   # WASM opcode and constant definitions
├── README.md                   # Chinese refactoring documentation
└── WASM_INSTRUCTIONS.md        # WASM instruction reference manual
```

### Web Application

```
├── app.py                      # Flask server (async task processing)
├── templates/
│   └── index.html             # Web UI
├── static/
│   └── script.js              # Frontend logic
├── uploads/                   # Temporary storage for uploaded files
└── outputs/                   # Processed output files
```

### Test Files

```
├── test.py                    # Command-line test script
├── base64_2.wasm             # Test input file
└── base64_2_vmp.wasm         # Test output file
```

## Usage Examples

### Example 1: Protect Encryption Algorithm

```python
from wasm_vmp import JiexStart

# Assume functions 5-8 are core encryption algorithms
processor = JiexStart('crypto.wasm')
processor.parse_module()
processor.encrypt_module(
    'crypto_protected.wasm',
    not_jeb=True,
    selected_functions=[5, 6, 7, 8]
)
print("Encryption algorithms protected")
```

### Example 2: Batch Processing

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
        print(f'Processed: {filename}')
```

### Example 3: Integration into Build Process

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
        print(f"Protection failed: {e}")
        return False

if __name__ == '__main__':
    if protect_wasm('build/app.wasm', 'dist/app.wasm', [10, 11, 12]):
        print("✓ WASM protection successful")
        sys.exit(0)
    else:
        print("✗ WASM protection failed")
        sys.exit(1)
```

## Important Notes

### ⚠️ Critical Limitations

1. **File Size**: Web interface limits upload to max 1MB
2. **Memory Usage**: VMP allocates virtual stack at 10MB address, ensure original program doesn't use this region
3. **Performance Impact**: Virtualization protection significantly reduces execution speed (typically 10-100x slower)
4. **Compatibility**: Some advanced WASM features may not be fully supported (e.g., SIMD, multi-value returns)

### 🔒 Security Recommendations

1. **Selective Protection**: Only apply VMP protection to core algorithm functions to avoid excessive performance degradation
2. **Multi-Layer Defense**: Combine data encryption, control flow obfuscation, and instruction expansion
3. **Regular Updates**: Obfuscation algorithms use randomization, each build generates different protection code
4. **Test Validation**: Always perform functional testing after protection to ensure program runs correctly

### 📝 Best Practices

1. **Identify Key Functions**: Use web interface analysis feature to view function sizes and names
2. **Progressive Protection**: Start by protecting a few functions for testing, then expand after confirmation
3. **Preserve Original Files**: Always keep unprotected original WASM files
4. **Version Control**: Don't commit protected files to version control systems

### 🐛 Common Issues

**Q: Protected WASM file won't run?**
A: Check if imported functions were selected for protection (imported functions should not be protected), or if the original file depends on specific memory layout.

**Q: File size increased significantly?**
A: This is normal. VMP injects interpreter code and bytecode data, typically increasing size by 2-5x.

**Q: How to determine function indices?**
A: Use the web interface analysis feature, or tools like `wasm-objdump` to view function lists.

**Q: Can I protect the same file multiple times?**
A: Not recommended. Multiple protections cause severe performance degradation and may introduce instability.

## Development Guide

### Code Structure

The project uses modular design, refactored from an original 2300-line monolithic file:

- **core.py**: Main entry point, coordinates module operations
- **codec.py**: Handles low-level WASM binary format reading/writing
- **analyzer.py**: Performs stack balance analysis and type inference
- **obfuscator.py**: Implements various obfuscation techniques
- **wasmvmp.py**: VMP core engine

### Extension Development

#### Adding New Obfuscation Techniques

```python
# Add new method in obfuscator.py
class WasmObfuscator:
    def my_custom_obfuscation(self, function_code):
        # Implement custom obfuscation logic
        pass

# Call in core.py
self.obfuscator.my_custom_obfuscation(func)
```

#### Custom VMP Instructions

```python
# Extend instruction handling in wasmvmp.py
def encode_custom_instruction(self, opcode, operands):
    # Generate custom bytecode
    pass
```

### Debugging Tips

```python
# Enable verbose logging
processor = JiexStart('input.wasm')
processor.parse_module()

# View function signatures
print(processor.analyzer.func_signatures)

# View global variable types
print(processor.analyzer.global_types)

# Export intermediate results
processor.codec.export_section_info('debug_sections.json')
```

## License

This project is licensed under the Apache License 2.0. See [LICENSE](LICENSE) file for details.

---

## 🤝 Contributing

Issues and Pull Requests are welcome!

## 📧 Contact

For questions or suggestions, please contact via GitHub Issues.

---

**Disclaimer**: This tool is intended for legitimate code protection purposes only. Users should comply with relevant laws and regulations and must not use it for illegal purposes.
