# 专项语法验证（2026-11-09）

> 历史记录：原来的 10 项业务内存差异已在 [独立内存修复](../verification_memory/README.md) 中消除。

目标是检查合法原始 WASM 经保护后是否仍满足二进制语法和静态类型规则。每个成功输出分别经 **WABT 1.0.39** 与 **Node.js v24.19.0 / V8** 验证，不依赖项目自己的解析器作最终判断。

## 结果

| 检查 | 结果 |
|---|---:|
| 官方语法文件 | 76 组 |
| 双验证器认可的原始模块 | 1119 个 |
| 两种子、两种 not_jeb 构建 | 2238 次 |
| 成功输出且双验证通过 | **2022 次（1011 个模块）** |
| 明确拒绝不支持特性 | 216 次（108 个模块） |
| 输出无效 WASM | **0** |
| 未分类构建异常 | **0** |
| 独立验证器拒绝官方 invalid/malformed 输入 | 2761/2761 |

覆盖结构化 block/loop/if、br/br_if/br_table、数值类型与转换、块签名、多返回值、局部/全局变量、直接/间接调用、函数与非函数导入、导出、启动函数、数据段、element/table、内存指令、LEB128、常量、名称和 UTF-8 等。表操作中的部分提案和引用操作仍被明确拒绝，不应将这些拒绝计作支持。

另有 86 个顶层原始模块无法由当前 WABT 编译或无法同时通过两个验证器，未提交保护，详情见 results.json 的 intake。负向测试检查的是独立验证器，**不表示 VMP 解析器完整实现了非法模块验证**；不支持的语法也可能在判断官方所指错误前被拒绝。

额外回归：194 类样例、582 次构建检查通过，3405 次运行对比通过；包含 6 次预期拒绝检查。控制流 2088 项、实际编译 Base64 模块 135 项校验通过。

## 本次验证找出并修复的问题

1. 解密启动函数索引错误：旧代码将内存、全局变量等导入也计入函数索引，导致 imports/linking 的 3 个模块在两个种子下输出无效。改为只计算 kind=0 的函数导入，并加入带活动数据段的非函数导入运行回归。
2. 全局初始表达式丢字节：旧代码剥离 init_raw 末尾的 0x0b，但这个字节也可能是整数 11、浮点常量的末字节或 global.get 的索引 11。解码器已经去除了 end，编码器现在原样保留操作数字节。新增 i32/i64/f32/f64 和导入全局索引共 5 类、15 次构建回归；修复前全部失败，修复后全部通过。

before_fix_summary.json 保留失败证据摘要；results.json 与 compatibility_results.json 是修复后的完整报告。

## 范围与复现

这是语法/类型验证，**不是所有模块运行等价或完整规范符合性认证**。此前发现的 10 次内存容量/越界行为差异仍存在，见 [第二轮报告](../verification_v2/README.md)。引用类型、SIMD、GC、线程、memory64、多内存和部分表操作不在当前支持范围。

来源：[WebAssembly/testsuite](https://github.com/WebAssembly/testsuite)，固定提交 92a3d806c7d70f5b63f125e6155b8d76304509f1。

```bash
npm ci --prefix bench --ignore-scripts
node bench/test_syntax.mjs /path/to/WebAssembly/testsuite /tmp/syntax.json
node bench/test_compatibility.mjs /tmp/compatibility.json
python3 bench/test_dispatch.py --strict
node bench/test_base64.mjs /tmp/base64.json
```

此专项已加入 GitHub CI，Python 3.9/3.12、Node.js 24。官方 syntax runner 不实例化语料模块，避免将链接条件或启动时 trap 混同为语法错误；运行行为由额外回归检查。

## 各语法文件的输出验证

以下计数按构建次数统计（每个模块两个种子）：

| 官方文件 | 双验证通过 | 明确不支持 |
|---|---:|---:|
| address | 8 | 0 |
| align | 50 | 0 |
| binary | 38 | 2 |
| binary-leb128 | 66 | 0 |
| block | 2 | 0 |
| br | 2 | 0 |
| br_if | 2 | 0 |
| call | 2 | 0 |
| call_indirect | 6 | 0 |
| const | 804 | 0 |
| conversions | 2 | 0 |
| custom | 4 | 2 |
| data | 52 | 0 |
| elem | 102 | 8 |
| endianness | 2 | 0 |
| exports | 112 | 0 |
| f32 | 2 | 0 |
| f64 | 2 | 0 |
| float_exprs | 196 | 0 |
| float_literals | 4 | 0 |
| forward | 2 | 0 |
| func | 8 | 0 |
| func_ptrs | 6 | 0 |
| global | 10 | 0 |
| i32 | 2 | 0 |
| i64 | 2 | 0 |
| if | 2 | 0 |
| imports | 132 | 0 |
| int_exprs | 38 | 0 |
| int_literals | 2 | 0 |
| labels | 2 | 0 |
| left-to-right | 2 | 0 |
| linking | 34 | 0 |
| load | 2 | 0 |
| local_get | 2 | 0 |
| local_set | 2 | 0 |
| local_tee | 2 | 0 |
| loop | 2 | 0 |
| memory | 22 | 0 |
| memory_copy | 66 | 0 |
| memory_fill | 22 | 0 |
| memory_init | 58 | 0 |
| memory_redundancy | 2 | 0 |
| memory_size | 8 | 0 |
| memory_trap | 4 | 0 |
| names | 6 | 0 |
| nop | 2 | 0 |
| return | 2 | 0 |
| select | 2 | 2 |
| start | 10 | 0 |
| store | 2 | 0 |
| switch | 2 | 0 |
| table | 18 | 0 |
| table_copy | 6 | 98 |
| table_fill | 0 | 2 |
| table_get | 0 | 2 |
| table_grow | 0 | 18 |
| table_init | 2 | 78 |
| table_set | 0 | 2 |
| table_size | 0 | 2 |
| token | 62 | 0 |
| type | 2 | 0 |
| type-equivalence | 2 | 0 |
| unreachable | 2 | 0 |
| unreached-valid | 2 | 0 |
| unwind | 2 | 0 |
| utf8-invalid-encoding | 6 | 0 |
