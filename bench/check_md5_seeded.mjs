import fs from 'node:fs';
import {createHash} from 'node:crypto';
import assert from 'node:assert/strict';
const base = process.argv[2] ? new URL(process.argv[2].replace(/\/?$/, '/') , new URL('../', import.meta.url)) : new URL('./', import.meta.url);
const cases = ['', 'a', 'abc', 'message digest', 'abcdefghijklmnopqrstuvwxyz',
  'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789',
  '12345678901234567890123456789012345678901234567890123456789012345678901234567890',
  '小麦生长模型', 'MD5 测试 🌾🔐', 'é\u0000abc\u0000末尾'].map(x=>Buffer.from(x));
let rng=20261109;
const next=()=>{rng=(Math.imul(rng,1664525)+1013904223)>>>0; return rng;};
for(const n of [0,1,55,56,57,63,64,65,119,120,127,128,129,255,256,257,1024,4096,16384,65536,
  ...Array.from({length:96},()=>next()%2049)]) {
  cases.push(Buffer.from(Uint8Array.from({length:n},()=>next()&255)));
}
const records=[];
for(const name of ['md5_vmp_optimized.wasm','md5_vmp_seed20261110.wasm','md5_vmp_seed20261111.wasm']) {
  const bytes=fs.readFileSync(new URL(name,base));
  const {instance:{exports:e}}=await WebAssembly.instantiate(bytes);
  const p=e.input_ptr(), out=e.output_ptr();
  for(const b of cases) {
    new Uint8Array(e.memory.buffer,p,b.length).set(b);
    assert.equal(e.md5_hash(p,b.length,out),0,`${name}: status`);
    assert.equal(Buffer.from(e.memory.buffer,out,16).toString('hex'),createHash('md5').update(b).digest('hex'),`${name}: ${b.length}B`);
  }
  records.push({name,sha256:createHash('sha256').update(bytes).digest('hex'),hashChecks:cases.length,passed:true});
}
assert.equal(new Set(records.map(r=>r.sha256)).size,records.length,'Seeded builds must differ');
const report={passed:true,totalHashChecks:records.reduce((sum,r)=>sum+r.hashChecks,0),records};
fs.writeFileSync(new URL('seeded_correctness.json',base),JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify(report,null,2));
