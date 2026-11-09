# 安全加载、提前判重与 AST 精简（2026-11-09）

完整基线为 `62d3075dc5aed061e71414d802d020920a90b9d0`。本机环境：macOS arm64、Python 3.9.6、Node.js v24.19.0、WABT 1.0.39。

## 按顺序完成的改动

1. **专用 scalar load**：14 种标量加载原地替换私有栈上的地址，直接执行原始业务加载指令和 memarg。i32/f32 结果不更新 SP，i64/f64 只增加 4 字节，省去通用出入栈流程。不以 i32.add 计算业务有效地址，原始偏移、内存索引、越界 trap 和浮点位模式保留。
2. **构造前判重**：普通指令先注册稳定代表，复用项不再构造出入栈主体。保留原有一字操作码、控制流 ID 和多代表因子；空占位仅用于保持两轮偏移计算一致，发射前删除。代表在跨函数调用中保持稳定。
3. **精简 AST 快照**：保留实时类型栈及结构化控制边界的必要快照，普通节点只存 stack_bytes_before/after 和 entry_stack_bytes。按指令增量维护字节高度，帧峰值与分支清栈读取整数，不再逐指令复制完整类型栈。平直深栈移除了二次方快照开销；深度嵌套的递归限制未改变。

## 实测收益

完整基线与当前源码在独立进程构建，7 轮交替测量；进程启动不计入构建时间。MD5 两侧均保护 [0,1,2]，最后的地址访问器都不保护；Base64 两侧保护全部 34 个原函数。

| 示例 | 构建中位数 ms（基线 → 本次） | 耗时减少 | 输出字节（基线 → 本次） |
|---|---:|---:|---:|
| md5 | 6.87 → 6.17 | 10.2% | 4559 → 4484 |
| base64 | 80.85 → 61.99 | 23.3% | 49419 → 48953 |

MD5 五组输入的运行比率约 0.99～1.03×，**基本持平，不宣称明显运行提速**。计时前另做 132 次摘要校验；完整重复采样在 runtime_results.json。收益主要体现在构建耗时、Python 分配峰值和少量解释器代码缩减，不能推及所有模块或设备。

AST 定向测试保持输入已分配、AST 存活，用 tracemalloc 测量分析期间 Python 分配峰值（**不是进程 RSS，也不是完整构建峰值**）：

| 平直栈深度 | 完整快照基线 | 紧凑 AST | 峰值减少 |
|---|---:|---:|---:|
| 1024 | 9.82 MB | 1.37 MB | 86.1% |
| 2048 | 36.40 MB | 2.73 MB | 92.5% |

该差分测试从 Git 读取保留的旧分析器，比较 322 个节点的出入栈类型、前后字节高度、块参数和已知帧峰值。时间仅为单次观察，不作为普遍分析速度结论。

提前判重专项保持相同 128 次普通指令出现，因子 1/3/64 分别保留 2/6/128 个代表，WasmVMP 模块内 add_instr 调用为 3013/3069/4777，确认生成工作量随保留主体数变化。这不是全程序所有指令工厂的总调用数；仍会构造小的头部/控制占位，不代表消除了所有临时对象。

## 验证

- 专用加载：14 种加载、56 个函数、三个种子，**3024 次对比通过（其中 1740 次预期 trap）**。覆盖偏移 0/1/13/uint32 最大值、精确内存末端、地址回绕、符号扩展、浮点 NaN/负零位模式、业务内存不变；trap 后使用新实例。
- 提前判重：64 个函数，因子 1/3/64，1728 次输出对比及双验证器通过。
- AST：322 个节点差分、4 类已知帧峰值和两个深度分配样本通过。
- 原有兼容性：195 类、585 构建、3408 次对比通过。
- 内存专项：32 类、96 构建、1548 次调用、1896 次状态/导入及 9 次失败实例化检查通过。
- 栈帧：27 类、81 构建、297 次对比及 9 次新实例的耗尽检查通过。
- 处理器共享：64 个原函数、6 构建、3456 次对比通过。
- 控制流：2088 项通过；独立 if/else 通过。
- 当前源码默认全函数保护 MD5：三种子 378 次摘要校验通过；C++/Emscripten Base64 135 次通过；scalar memarg 编解码 46 次运行对比及显式 memory 0 检查通过。
- 官方严格范围：168 个模块、8352 次运行对比通过，0 次差异。
- 官方语法：76 组、1120 个有效输入、2240 构建；2022 个输出双验证通过，218 次明确不支持，0 个无效输出。
- 更广官方报告仍保留 1 个引用指令模块不支持，因此 spec_full_results.json 的 passed=false 保留；成功转换模块的行为差异为 0。未将不支持项或 runner 无法编译的模块冒充通过。

## 范围与复现

私有内存隔离和支持范围没有扩大：带业务内存的输出仍需 multi-memory 运行时，已验证 Node.js 24/V8。原始多内存、memory64、shared memory、GC/SIMD/引用值等仍可能明确拒绝。本轮没有处理 trap 跳过私有 SP 恢复的问题，trap 后仍应重新实例化；没有评估抗分析强度。

```bash
npm ci --prefix bench --ignore-scripts
node bench/test_scalar_loads.mjs /tmp/loads.json
node bench/test_early_dedup.mjs /tmp/dedup.json
python3 bench/test_ast_compact.py --json-output /tmp/ast.json
node bench/test_memory_semantics.mjs /tmp/memory.json
python3 bench/test_dispatch.py --strict
node bench/test_syntax.mjs /path/to/WebAssembly/testsuite /tmp/syntax.json
```

AST 差分测试需要 Git 历史中的 62d3075，CI checkout 已设置 fetch-depth:0。CI 使用 Python 3.9/3.12、Node.js 24，已加入三项新回归。

完整构建和 MD5 基准：

```bash
git worktree add --detach /tmp/vmp-before-loads 62d3075
python3 bench/benchmark_frames.py /tmp/vmp-before-loads --output-dir bench/verification_loads
node bench/benchmark_optimization.mjs bench/verification_loads/benchmark_config.json
```
