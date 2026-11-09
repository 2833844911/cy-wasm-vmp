# 第二轮优化与兼容性检查（2026-11-09）

对比基线：`80d5852`。本机环境：macOS arm64、Python 3.9.6、Node.js v24.19.0、WABT 1.0.39。

## 改动

- `local.get` / `local.tee` 从逐项扫描改为随机布局的 `br_table` 分派，保留按类型访问。
- 从原有稀疏 ID 空间按模块大小抽样，避免每次构建创建和打乱约百万个整数。
- 修复函数隐式标签 `br_if` 的条件消费与返回行为。
- 重新跟踪结构化控制流的栈类型、入口高度和标签结果；跳转时移除应丢弃的值并保留结果，修复嵌套分支和循环回跳；不再为不可达代码生成未知栈类型处理器。
- 修复 `i64.extend8_s/16_s/32_s` 栈类型；支持数值 typed select、多字节块类型索引和索引 64 与 void 的区分。
- `br_table` 预处理移到局部变量容量扫描之前。
- 缺少 global/memory 节时创建所需节，保持 DataCount 在 Code 之前。
- 默认保护所有定义函数，包括最后一个函数；空选择原样输出。回归确认选中函数实际被改写。
- 移除库中未使用的 `symbol` 导入，不再依赖测试 shim。
- 对未支持的指令、引用/向量类型、共享/64 位/多内存和类型形式明确报错，避免按错误的字节边界继续解析。

## 性能

相同 MD5 原始模块、保护函数 `[0, 1, 2]`、相同配置。最后的地址访问器在两侧均不保护，以保持相同范围。默认保护全部函数的产物另外校验。

7 轮构建耗时中位数：229.447 ms → 6.103 ms，约 37.59×。计时包含解析与构建。

运行耗时（微秒/次），7 轮交替测量中位数：

| 输入 | 第一轮优化版 | 本次优化版 | 进一步加速 |
|---|---:|---:|---:|
| abc (3 B) | 8.765 | 5.072 | 1.73× |
| 32 B | 10.101 | 5.561 | 1.82× |
| 64 B | 16.259 | 9.022 | 1.80× |
| 1024 B | 128.536 | 71.728 | 1.79× |
| 16384 B | 1960.001 | 1079.280 | 1.82× |

本次仍比未保护 WASM 慢约 35.8～43.6 倍。相同保护范围体积 5277 → 5257 字节。结果受设备和环境影响。

## 测试结果

- 自建 **187 类样例、561 次构建**：3384 次运行对比通过。成功输出均经 WABT 和 V8 验证；其中 6 次构建是预期拒绝 SIMD/引用指令的检查，没有生成输出。覆盖三种子、两种 not_jeb 设置、扩展因子 1/3、整数/浮点/转换/内存/调用/多返回值/控制流/导入/启动/被动数据/缺省节/函数选择等。
- 原有控制流回归 **2088 项全部通过**，独立 if/else 回归通过。`test_dispatch.py` 默认要求完整通过，历史基线失败只能显式允许。
- 当前源码默认保护全部原函数：三种子 **378 次 MD5 校验**通过；性能基准另有 **132 次摘要校验**通过。
- 仓库实际编译的 C++/Emscripten Base64 模块：原版与两种子保护版共 **135 次**校验通过，含 UTF-8 输入，三个模块均通过双验证器。
- 官方测试集：[WebAssembly/testsuite](https://github.com/WebAssembly/testsuite)，固定提交 `92a3d806c7d70f5b63f125e6155b8d76304509f1`。14 组支持范围：**132 个模块、7592 次调用对比全部通过**，已加入 CI。
- 更广的 26 组官方检查：170 个模块中 **168 个成功输出均通过双验证器**，2 个模块因引用类型等未支持内容明确拒绝；**8342 次调用对比通过，10 次内存语义差异未通过**。`spec_results.json` 如实保留 `passed=false`。另有两个含新引用类型语法的原始模块无法由当前 WABT 编译，记录在 intake；4 个栈耗尽检查未执行。

官方 runner 只对模块/调用命令做原版与保护版差分，不实现负向验证和完整链接/注册命令，不构成完整规范符合性认证。

## 尚未解决的实际限制

VMP 在原始线性内存的 10 MB 附近放置字节码与栈，并可能将原始内存扩至至少 192 页。因此 `memory.size`、`memory.grow` 返回的容量与原始内存边界附近的访问行为可能变化。官方广泛检查剩余的 10 次差异均属于这一问题。修复需要调整内存隔离方案，不能只隐藏失败项。

SIMD、引用值保护、GC、线程、memory64、多内存等不在支持范围。当前解析器可能拒绝含这些特性的模块，即使相关函数未被选中。大模块、应用堆区和运行时分配仍需实际集成验证。性能及有限测试不能证明任意 WASM 兼容性或抗分析强度。

## 复现

```bash
npm ci --prefix bench --ignore-scripts
node bench/test_compatibility.mjs /tmp/compatibility.json
python3 bench/test_dispatch.py --strict
python3 bench/test_if_else.py
node bench/test_base64.mjs /tmp/base64.json
python3 bench/protect_optimized.py --output-dir /tmp/vmp-md5
python3 bench/protect_optimized.py --seed 20261110 --suffix seed20261110 --output-dir /tmp/vmp-md5
python3 bench/protect_optimized.py --seed 20261111 --suffix seed20261111 --output-dir /tmp/vmp-md5
node bench/check_md5_seeded.mjs /tmp/vmp-md5
python3 bench/benchmark_build.py 80d5852
node bench/benchmark_optimization.mjs bench/verification_v2/benchmark_config.json
```

官方完整检查（预期仍返回非零）：

```bash
node bench/test_spec.mjs /path/to/WebAssembly/testsuite /tmp/spec.json
```

CI 使用 Python 3.9/3.12 和 Node.js 24，执行自建回归、MD5、Base64 与指定官方支持范围。CI 状态以 GitHub Actions 实际结果为准。
