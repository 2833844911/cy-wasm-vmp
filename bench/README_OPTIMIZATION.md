# cy-wasm-vmp：MD5 运行速度优化

日期：2026-11-09。基础仓库 [2833844911/cy-wasm-vmp](https://github.com/2833844911/cy-wasm-vmp)，提交 `e998a57301ef37c0453e3e567da137d50450a566`。

## 结果

保留 MD5 压缩函数和入口的指令虚拟化，将线性扫描处理器改为直接分派，本次实现快了约 9.5～9.9 倍。输出体积也从 5497 降到 5277 字节。本仓库已集成优化源码；下文主表与原始 JSON 保留压缩包中的 Linux 测试记录。macOS 独立复核结果见 [verification_macos](verification_macos/README.md)。

以下是原始 WASM、之前仅修复正确性的 VMP、本次优化 VMP，在同一进程、同一批运行中的比较。每组预热后测 7 轮、轮换三个版本的测量顺序，取每轮平均单次耗时的中位数。不能直接把这次新测量值与上一次不同时间的测量值作精确比率。

| 输入 | 优化前 VMP（毫秒/次） | 优化后 VMP（毫秒/次） | 加速倍数 | 优化后相对未保护 WASM 的耗时倍数 |
|---|---:|---:|---:|---:|
| abc (3 B) | 0.1958 | 0.0198 | 9.91× | 97.5× |
| 32 B | 0.2092 | 0.0215 | 9.71× | 100.1× |
| 64 B | 0.3218 | 0.0335 | 9.60× | 90.9× |
| 1024 B | 2.5720 | 0.2695 | 9.54× | 85.9× |
| 16384 B | 39.1306 | 4.0239 | 9.72× | 86.2× |

优化后仍比相同未保护 MD5 WASM 慢约 86～100 倍。此处衡量的是相同循环实现、相同保护范围的运行开销，不代表其他实现、编译器、设备或浏览器的结果。

## 改动

- 之前：每条虚拟指令逐个比较全部处理器，查找对应操作。
- 现在：用 WASM `br_table` 直接跳到相应处理器；处理器主体仍执行虚拟指令，未把 MD5 替换为原生调用，也未缩小保护函数范围。
- 操作码在每次构建时按 64 个一组随机分配紧凑编号，处理器布局继续随机排列。空洞或无效操作码进入 trap。
- 根据词法控制流嵌套重新定位处理器中的跳转，保留内部条件、循环、函数退出等目标；字节码立即数及跳转偏移表示不变。
- 包含此前的一行 if/else 假分支修复；原始仓库未经这一修复时，本次 MD5 示例摘要计算错误，不能作为有效性能对照。

保护结构和操作码分布发生了变化。这里验证的是功能和性能，没有评估或证明与原版相同的抗分析强度。

## 验证与已知限制

- 主测速的三个版本共 132 项摘要比对通过。
- 3 个不同构建种子各测 126 个标准、UTF-8、边界和确定性二进制输入，共 378 次 MD5 校验通过。三个产物 SHA-256 不同，主测速产物与被验证的主优化产物 SHA-256 一致。
- 最终源码的控制流/类型/调用回归检查：2064 项通过。包含嵌套 if/else、循环、内存偏移、全局变量、直接调用、递归、提前返回、i64/f32/f64 运算，以及多次调用。
- 另有 24 次重复检查暴露仓库之前就存在的缺陷：`br_if` 跳到函数隐式标签时返回值错误。修正前的性能基线与本次优化版本都存在相同问题，本次没有修复；没有新增回归失败。
- 因此回归 JSON 保留 `passed=false`，同时记录 `passedSupportedScope=true` 和 24 项已有失败。运行 `test_dispatch.py --strict` 会如实返回非零；默认模式只在新增失败时返回非零。
- 合并补丁和增量补丁均已实际验证可应用，并能重建本次测试源码。
- 有限输入和测试范围不构成所有 WASM 模块的兼容性证明。SIMD、线程等高级特性未在本次测试中覆盖。

## 测试条件

CPU：INTEL(R) XEON(R) PLATINUM 8573C；linux x64；Node.js v24.22.1，V8 13.6.233.17-node.58；Python 3.12.14。

MD5 示例由 `build_md5.py` 直接编码为标准 WASM，`md5.c` 是对应 C 参考实现，此处不是 Clang/Emscripten 编译产物。主随机种子 20261109，额外校验种子 20261110、20261111。保护配置仍为 `not_jeb=True`、`instruction_expansion_factor=1`、`selected_functions=None`。项目跳过最后一个原函数，示例将无计算逻辑的输出地址访问器放在最后。

输入预先放在内存，计时包含 JS→WASM 调用开销，不包括输入复制、十六进制转换、Node 原生 MD5、模块加载和构建。Node crypto 仅作为摘要参照。JSON 保留每轮采样、最小/最大耗时、环境和产物 SHA-256。共享执行环境存在波动；加载字段只有单次观察值，不是可靠的冷启动基准。

## 历史版本使用补丁

当前仓库已经应用优化，无需再次应用补丁。以下仅用于原始提交。

将本包 `bench/` 放入上述指定提交的仓库根目录。

**未经修改的原始仓库**，应用合并补丁（已包含 if/else 修复）：

```bash
git apply --check bench/cy_wasm_vmp_optimization.patch
git apply bench/cy_wasm_vmp_optimization.patch
```

**已经应用之前 if/else 修复的仓库**，只应用增量优化补丁：

```bash
git apply --check bench/dispatch_optimization.patch
git apply bench/dispatch_optimization.patch
```

二者选一，不要叠加重复应用。

## 复现

包内保留了之前正确性修复版的 WASM 和配置用于比较。应用优化补丁后：

```bash
python3 bench/build_md5.py
python3 bench/protect_optimized.py
node bench/benchmark_optimization.mjs
python3 bench/test_dispatch.py --json-output bench/dispatch_optimized.json
python3 bench/test_if_else.py
python3 bench/protect_optimized.py --seed 20261110 --suffix seed20261110
python3 bench/protect_optimized.py --seed 20261111 --suffix seed20261111
node bench/check_md5_seeded.mjs
```

如需从源码重新生成“优化前”对照，请在原始提交的另一个目录只应用 `if_else_fix.patch`，运行 `build_md5.py`、`protect.py`，将其输出 `md5_vmp.wasm` 与 `protection.json` 分别复制为比较目录的 `md5_vmp_before_optimization.wasm` 与 `protection_before_optimization.json`。

测试脚本兼容 Python 3.12，针对项目未使用且已经被 Python 移除的 `symbol.continue_stmt` 导入提供进程内兼容名称。这不是性能改动。
