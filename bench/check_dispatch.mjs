import fs from 'node:fs';
import assert from 'node:assert/strict';

const [suite, ...paths] = process.argv.slice(2);
let checks = 0;
const failures = [];
for (const path of paths) {
  let e;
  try { e = new WebAssembly.Instance(new WebAssembly.Module(fs.readFileSync(path)), {}).exports; }
  catch (error) { failures.push({path, error: String(error)}); continue; }
  function check(name, args, expected, tolerance = 0) {
    let actual;
    try {
      actual = e[name](...args);
      if (tolerance) assert(Math.abs(actual - expected) <= tolerance * Math.max(1, Math.abs(expected)), `${name}: ${actual} != ${expected}`);
      else assert.equal(actual, expected);
      checks++;
    } catch (error) { failures.push({path, name, args: args.map(String), actual: String(actual), expected: String(expected), error: String(error),
      knownPreexisting: name === 'implicit_if' && args[0] !== 0 && path.endsWith('_vmp.wasm')}); }
  }
  for (let round = 0; round < 12; round++) {
    if (suite === 'i32_control_memory_calls') {
      for (const [a, b] of [[0,0],[1,2],[-1,7],[0x7fffffff,19],[-2147483648,-1],[123456,9987]]) {
        const x = ((a ^ b) + Math.imul(a,b)) | 0;
        check('arith', [a,b], (x << 5) | (x >>> 27));
      }
      for (const x of [-100,-6,-5,-1,0,1,15,16,100]) check('nested', [x], x<0 ? x < -5 ? 11 : 22 : x<16 ? 33 : 44);
      for (const x of [0,1,2,10,63]) check('sum_loop', [x], x*(x+1)/2);
      for (const x of [-100,0,1,7,100]) check('caller', [x], x*9+4);
      for (const x of [0,1,2,5,8]) {
        let answer=1; for(let i=2;i<=x;i++) answer*=i;
        check('factorial', [x], answer);
      }
      for (const x of [-100,-1,0,1,100,123456]) {
        check('memory_roundtrip', [4096,x], Math.imul(x,3) ^ ((x+7)|0));
        assert.equal(new DataView(e.memory.buffer).getInt32(4108,true),Math.imul(x,3)); checks++;
        assert.equal(e.counter.value,(x+7)|0); checks++;
      }
      for(const x of [-100,-1,0,1,99]) check('early',[x],x<0 ? -7 : x+5);
      for(const x of [0,1,-1]) check('implicit_if',[x],x===0 ? 88 : 77);
      check('implicit_br',[],123);
    } else if (suite === 'i64') {
      for(const [a,b] of [[0n,0n],[1n,2n],[-1n,7n],[1n<<40n,-33n],[(1n<<63n)-1n,20n]]) {
        const ua=BigInt.asUintN(64,a);
        const rot=BigInt.asUintN(64,(ua<<7n)|(ua>>57n));
        check('wide',[a,b],BigInt.asIntN(64,BigInt.asUintN(64,a+b)^rot));
      }
      for(const a of [0n,1n,-1n,1n<<40n,(1n<<63n)-1n]) check('square',[a],BigInt.asIntN(64,(a+5n)*(a+5n)));
    } else if(suite === 'f32') {
      for(const [a,b] of [[0,2],[1.5,2.25],[-3.5,1.25],[0.1,0.2],[1e6,0.125]])
        check('float32',[a,b],Math.fround(Math.fround(Math.fround(a)*Math.fround(b))+Math.fround(a)));
      for(const a of [-100.25,-0.5,0,0.25,7.5]) check('abs32',[a],Math.abs(Math.fround(a)));
    } else if(suite === 'f64') {
      for(const [a,b] of [[0,2],[1.5,2.25],[-3.5,1.25],[0.1,0.2],[1e6,0.125]]) check('float64',[a,b],(a*b)/(b+1),1e-12);
      for(const a of [-100.25,-0.5,0,0.25,7.5]) check('square64',[a],a*a,1e-12);
    }
    if(failures.length > 25) break;
  }
}
console.log(JSON.stringify({suite, passed: failures.length===0, checks, failures,
  passedSupportedScope: failures.every(x=>x.knownPreexisting), knownPreexistingFailureCount: failures.filter(x=>x.knownPreexisting).length},null,2));
process.exitCode=failures.length ? 1 : 0;
