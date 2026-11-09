# 业务内存语义修复（2026-11-09）

基线：63fca0b256ed0d325a75854c74f3790e951f8125。独立运行环境：macOS arm64、Python 3.9.6、Node.js v24.19.0、WABT 1.0.39。

## 已消除原有 10 项差异

以前将 VMP 字节码和操作数栈放进业务线性内存，并扩充其容量，改变了 memory.size/memory.grow 返回值及越界检查。现在追加一个**不导出的私有内存**存放字节码和帧区，原始内存的 min/max、导入、导出、索引及 __heap_base 均保持不变。

原始业务 load/store 和 bulk-memory 指令访问原内存；仅生成解释器中的字节码/栈访问指定私有内存。无原始内存时，私有内存为索引 0；原始单内存时私有内存为索引 1。字节码从私有地址 0 开始，栈帧继续按类型峰值分配并检查边界。私有数据段追加在末尾，原始数据索引不变，DataCount 按需增加。

原有 10 个失败用例均转为通过，逐模块前后对照见 resolved_differences.json。

- 扩大后的官方严格范围：**168 个模块、8352 次对比全部通过，0 项语义差异**，已用于 CI。
- 更广官方报告：169 个成功转换模块均通过双验证，8352 次对比通过、**0 次行为差异**；另有 1 个含引用指令的模块仍明确不支持，故 spec_full_results.json 继续保留完整范围 passed=false，未将不支持项冒充通过。
- 两个含较新引用类型语法的顶层原始模块仍无法由当前 WABT 编译，4 个栈耗尽断言未执行；这是已有 runner 的范围限制，不是完整规范符合性认证。

## 同时修复的边界

- 旧 i32.load/i64.load 快捷处理器先做 i32.add，可能将地址加偏移回绕为合法地址。现在保留原始 memarg，交由引擎执行完整有效地址和越界检查。
- codec 正确处理 multi-memory memarg 的 0x40 标志，编码顺序为 align、memory index、offset，并保留显式 memory 0 的语义。
- 不再迁移或拒绝动态 __heap_base；常量及导入 global 初始化均保持原值。
- 重叠活动数据段、global/未知偏移及高地址段保留原始数据，不在初始化后错误解密被后段覆盖的字节。
- 导入内存保持原始数据段字节，避免实例化失败时向宿主暴露加密中间状态。其他可安全处理的普通数据段继续使用原来的数据混淆；指令虚拟化保留。未评估或证明相同抗分析强度。

多内存编码依据 [WebAssembly 官方说明](https://github.com/WebAssembly/spec/blob/main/proposals/multi-memory/Overview.md)。

## 验证

| 检查 | 结果 |
|---|---|
| 业务内存专项 | 32 类、96 构建，1548 次调用对比、1896 次状态/导入检查通过 |
| 实例化失败的宿主可见内存 | 9 次检查通过，完整 64 KiB 快照一致 |
| scalar memarg 编解码 | 23 种指令、memory 0/1，92 次访问；46 次运行对比及显式 memory 0 案例通过 |
| 原有兼容性 | 195 类、585 构建、3408 次对比通过 |
| 栈帧 | 27 类、81 构建、297 次对比和 9 次独立实例的耗尽 trap 检查通过 |
| 处理器共享 | 64 个原函数、6 构建、3456 次对比通过 |
| 控制流 | 2088 项通过 |
| MD5 | 默认全函数保护的三种子 378 次摘要校验通过，运行基准另有 132 次摘要校验通过 |
| 编译的 C++/Emscripten Base64 | 135 次校验通过 |
| 官方语法 | 76 组、1120 个有效原始模块、2240 次构建；2022 个输出双验证通过，218 次明确不支持，0 个无效输出 |

覆盖原始/导入内存、零页、增长返回值和最大值、精确越界、加载偏移溢出、memory.copy/fill/init/drop、活动/被动段、启动函数、堆标记、10 MB 数据与旧栈区冲突、无业务内存模块、重叠段和失败实例化。

## 兼容性与资源范围

**带业务内存的输出需要运行时支持 multi-memory。** 已验证 Node.js 24/V8 和 WABT（显式启用 multi_memory）。未支持此特性的引擎会拒绝编译；本次没有用改变业务语义的单内存方案作静默回退。原始多内存、shared memory、memory64、GC、SIMD、引用值等输入的支持范围没有扩大，仍可能明确拒绝。

此次解决的是已验证的业务内存差异，不是任意 WASM 的完全等价证明。私有帧区仍有资源上限；trap 跳过正常 SP 恢复的问题尚未处理，**trap 后应重新实例化**。测试在 trap 后使用新实例，未将旧实例复用计为通过。

## 体积与性能

完整基线与当前源码分别在独立进程构建，7 轮交替测量；MD5 两侧保护同样的 [0,1,2]，Base64 两侧保护全部原函数。

| 示例 | 基线字节 | 本次字节 | 构建中位数 ms（基线 → 本次） |
|---|---:|---:|---:|
| md5 | 4413 | 4559 | 6.80 → 6.75 |
| base64 | 49690 | 49419 | 72.24 → 79.02 |

MD5 五组输入的本次吞吐约为基线 0.95～0.99×，耗时约增加 1～5%。本轮优先保留原始内存行为，不宣称运行提速；共享环境存在波动，完整采样见 runtime_results.json。

## 复现

```bash
npm ci --prefix bench --ignore-scripts
node bench/test_memory_semantics.mjs /tmp/memory.json
node bench/test_codec_memargs.mjs /tmp/codec.json
node bench/test_compatibility.mjs /tmp/compatibility.json
node bench/test_stack_frames.mjs /tmp/frames.json
python3 bench/test_dispatch.py --strict
node bench/test_syntax.mjs /path/to/WebAssembly/testsuite /tmp/syntax.json
```

基准复现：

```bash
git worktree add --detach /tmp/vmp-before-memory 63fca0b
python3 bench/benchmark_frames.py /tmp/vmp-before-memory --output-dir bench/verification_memory
node bench/benchmark_optimization.mjs bench/verification_memory/benchmark_config.json
```

Python 3.9/3.12、Node.js 24 的 GitHub CI 已增加内存专项和 memarg 编码回归，并将严格官方运行范围扩大到包含原先失败的各组。
