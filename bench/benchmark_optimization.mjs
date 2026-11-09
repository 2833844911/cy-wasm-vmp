import { readFileSync, writeFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { cpus, platform, arch, release } from 'node:os';
import { performance } from 'node:perf_hooks';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import assert from 'node:assert/strict';

const here = dirname(fileURLToPath(import.meta.url));
const config = process.argv[2] ? JSON.parse(readFileSync(process.argv[2], 'utf8')) : {};
const targetMs = 120;
const samplesPerCase = 7;
const median = xs => [...xs].sort((a, b) => a - b)[Math.floor(xs.length / 2)];
const digest = data => createHash('md5').update(data).digest('hex');
const sha256 = data => createHash('sha256').update(data).digest('hex');
const pattern = n => Buffer.from(Uint8Array.from({ length: n }, (_, i) => (i * 73 + (i >>> 3) * 19 + 11) & 255));

async function load(name, path) {
  const bytes = readFileSync(path);
  const compileStart = performance.now();
  const module = await WebAssembly.compile(bytes);
  const compileMs = performance.now() - compileStart;
  const instanceStart = performance.now();
  const instance = await WebAssembly.instantiate(module, {});
  const instantiateMs = performance.now() - instanceStart;
  const e = instance.exports;
  for (const k of ['md5_hash', 'input_ptr', 'output_ptr']) assert.equal(typeof e[k], 'function', `${name}: missing ${k}`);
  assert(e.memory instanceof WebAssembly.Memory, `${name}: missing exported memory`);
  const input = e.input_ptr() >>> 0;
  const output = e.output_ptr() >>> 0;
  assert(input + 65536 <= e.memory.buffer.byteLength);
  assert(output + 16 <= e.memory.buffer.byteLength);
  return { name, path, bytes: bytes.length, sha256: sha256(bytes), instance, input, output,
    fn: e.md5_hash, firstLoad: { compileMs, instantiateMs },
    prepare(data) { new Uint8Array(e.memory.buffer, input, data.length).set(data); },
    result() { return Buffer.from(e.memory.buffer, output, 16).toString('hex'); },
    hash(data) { this.prepare(data); this.fn(input, data.length, output); return this.result(); },
  };
}

const variants = [
  await load('native_wasm', resolve(here, 'md5.wasm')),
  await load('correctness_fixed_vmp', resolve(here, config.before || 'md5_vmp_before_optimization.wasm')),
  await load('optimized_vmp', resolve(here, config.after || 'md5_vmp_optimized.wasm')),
];

const rfc = [
  ['', 'd41d8cd98f00b204e9800998ecf8427e'],
  ['a', '0cc175b9c0f1b6a831c399e269772661'],
  ['abc', '900150983cd24fb0d6963f7d28e17f72'],
  ['message digest', 'f96b697d7cb7938d525a2f31aaf161d0'],
  ['abcdefghijklmnopqrstuvwxyz', 'c3fcd3d76192e4007dfb496cca67e13b'],
  ['ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789', 'd174ab98d277d9f5a5611c2c9f419d9f'],
  ['12345678901234567890123456789012345678901234567890123456789012345678901234567890', '57edf4a22be3c955ac49da2e2107b67a'],
];
let correctnessChecks = 0;
const correctnessLengths = [];
for (const [text, expected] of rfc) {
  const data = Buffer.from(text);
  assert.equal(digest(data), expected, 'Node oracle disagrees with RFC test vector');
  for (const v of variants) {
    assert.equal(v.hash(data), expected, `${v.name}: RFC vector ${JSON.stringify(text)}`);
    correctnessChecks++;
  }
}
const variedLengths = [0, 1, 2, 3, 7, 15, 16, 31, 32, 54, 55, 56, 57, 63, 64, 65, 119, 120, 127, 128, 129, 255, 256, 257, 1023, 1024, 1025, 16384, 65535, 65536, 65, 56, 0, 3];
for (const n of variedLengths) {
  const data = pattern(n);
  const expected = digest(data);
  for (const v of variants) {
    assert.equal(v.hash(data), expected, `${v.name}: deterministic binary input length ${n}`);
    correctnessChecks++;
  }
  correctnessLengths.push(n);
}
for (const text of ['小麦生长模型', 'MD5 测试 🌾🔐', 'é\u0000abc\u0000末尾']) {
  const data = Buffer.from(text, 'utf8');
  for (const v of variants) {
    assert.equal(v.hash(data), digest(data), `${v.name}: UTF-8 input`);
    correctnessChecks++;
  }
}
console.log(`Correctness passed: ${correctnessChecks} module/hash checks.`);

// Only the synchronous exported WASM function calls are inside the timed loop.
// Input copying, output encoding, and the Node crypto oracle are outside timing.
function measure(v, length, iterations) {
  const fn = v.fn;
  const input = v.input;
  const output = v.output;
  const t0 = performance.now();
  for (let i = 0; i < iterations; i++) fn(input, length, output);
  return performance.now() - t0;
}

function calibrate(v, length, expected) {
  // Repeated calls both warm V8/WASM and estimate a 120 ms batch size.
  const warmStart = performance.now();
  let warmIterations = 0;
  while (performance.now() - warmStart < 80) {
    measure(v, length, 1);
    warmIterations++;
  }
  let n = 1;
  let elapsed = measure(v, length, n);
  while (elapsed < 25 && n < 100_000_000) {
    n = Math.min(100_000_000, Math.max(n + 1, Math.ceil(n * Math.min(10, 30 / Math.max(elapsed, 0.001)))));
    elapsed = measure(v, length, n);
  }
  assert.equal(v.result(), expected, `${v.name}: calibration corrupted digest`);
  return { iterations: Math.max(1, Math.min(100_000_000, Math.round(n * targetMs / elapsed))), warmIterations };
}

const workloads = [
  { label: 'abc (3 B)', data: Buffer.from('abc') },
  ...[32, 64, 1024, 16384].map(n => ({ label: `${n} B`, data: pattern(n) })),
];
const cases = [];
for (const { label, data } of workloads) {
  const expected = digest(data);
  const stats = variants.map(v => {
    v.prepare(data);
    return { name: v.name, ...calibrate(v, data.length, expected), samples: [] };
  });
  for (let round = 0; round < samplesPerCase; round++) {
    const order = [[0,1,2], [2,1,0], [1,2,0], [0,2,1], [2,0,1], [1,0,2], [0,1,2]][round];
    for (const i of order) {
      const v = variants[i];
      const s = stats[i];
      const elapsedMs = measure(v, data.length, s.iterations);
      assert.equal(v.result(), expected, `${v.name}: timed workload ${label} corrupted digest`);
      s.samples.push({ round, position: order.indexOf(i), iterations: s.iterations, elapsedMs, usPerHash: elapsedMs * 1000 / s.iterations });
    }
  }
  for (const s of stats) {
    const values = s.samples.map(x => x.usPerHash);
    s.medianUsPerHash = median(values);
    s.minUsPerHash = Math.min(...values);
    s.maxUsPerHash = Math.max(...values);
    s.hashesPerSecond = 1_000_000 / s.medianUsPerHash;
    s.bytesPerSecond = s.hashesPerSecond * data.length;
  }
  const row = { label, inputBytes: data.length, expectedMd5: expected, variants: stats,
    speedupVsPreviousVmp: stats[1].medianUsPerHash / stats[2].medianUsPerHash,
    previousSlowdownVsNative: stats[1].medianUsPerHash / stats[0].medianUsPerHash,
    optimizedSlowdownVsNative: stats[2].medianUsPerHash / stats[0].medianUsPerHash,
    retainedThroughputPercent: 100 * stats[0].medianUsPerHash / stats[2].medianUsPerHash };
  cases.push(row);
  console.log(`${label}: native ${stats[0].medianUsPerHash.toFixed(3)} us; before ${stats[1].medianUsPerHash.toFixed(3)} us; optimized ${stats[2].medianUsPerHash.toFixed(3)} us; speedup ${row.speedupVsPreviousVmp.toFixed(2)}x; slowdown-vs-native ${row.optimizedSlowdownVsNative.toFixed(2)}x`);
}

const result = {
  generatedAt: new Date().toISOString(),
  protectionBefore: config.protectionBefore || JSON.parse(readFileSync(resolve(here, 'protection_before_optimization.json'), 'utf8')),
  protectionOptimized: config.protectionOptimized || JSON.parse(readFileSync(resolve(here, 'protection_optimized.json'), 'utf8')),
  fixture: 'Portable loop-based MD5 explicitly encoded as WASM by build_md5.py; md5.c is a source reference, not the compiler used. This benchmark does not cover arbitrary compiler outputs or all MD5 implementations.',
  environment: { node: process.version, v8: process.versions.v8, platform: platform(), arch: arch(), osRelease: release(), cpu: cpus()[0]?.model, logicalCpus: cpus().length },
  scope: 'Same freestanding WASM MD5: native, previous correctness-fixed VMP, optimized VMP. Repeated hashing of a prefilled input buffer, no host crypto, copying, or hexadecimal conversion in timed loop. Includes JavaScript-to-WASM function-call overhead. Node crypto is a correctness oracle only.',
  methodology: { targetMs, samplesPerCase, statistic: 'median of per-batch microseconds/hash', order: 'all six permutations of three variants, plus first permutation repeated', warmup: 'at least 80 ms per variant/workload, then adaptive calibration', firstLoadCaveat: 'Single observed in-process compile/instantiate duration per artifact; these numbers are not robust cold-start benchmarks and may be affected by runtime caches.' },
  artifacts: variants.map(v => ({ name: v.name, path: v.path, sizeBytes: v.bytes, sha256: v.sha256, firstLoad: v.firstLoad })),
  correctness: { passed: true, moduleHashChecks: correctnessChecks, rfcVectors: rfc.length, deterministicLengths: correctnessLengths, utf8Cases: 3, oracle: 'node:crypto MD5 plus RFC 1321 known results', scopeLimit: 'Finite test set, not a proof of equivalence.' },
  cases,
};
const outPath = resolve(here, config.output || 'optimization_results.json');
writeFileSync(outPath, JSON.stringify(result, null, 2) + '\n');
console.log(`Saved ${outPath}`);
