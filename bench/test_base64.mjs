/** Exercise the repository's compiled C++/Emscripten module through its JS glue. */
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import wabtFactory from 'wabt';
const wabt=await wabtFactory();
import vm from 'node:vm';
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';
import assert from 'node:assert/strict';
const root=fileURLToPath(new URL('../',import.meta.url));
const require=createRequire(import.meta.url);
const glue=fs.readFileSync(root+'base64.js','utf8').split('async function demo()')[0]+'\nmodule.exports=Base64Module;';
const context={module:{exports:{}},require,__dirname:root,process,console,Buffer,WebAssembly,TextDecoder,TextEncoder,setTimeout,clearTimeout};
vm.runInNewContext(glue,context,{filename:root+'base64.js'});
const factory=context.module.exports;
let checks=0;const records=[];
const directory=fs.mkdtempSync(path.join(os.tmpdir(),'base64_vmp_'));
try {
const original=root+'base64_2.wasm';
const jobs=[20261109,20261110].map(seed=>({name:`base64_${seed}`,input:original,output:path.join(directory,`base64_${seed}.wasm`),seed,notJeb:seed===20261109}));
fs.writeFileSync(path.join(directory,'jobs.json'),JSON.stringify(jobs));
const built=spawnSync(process.env.PYTHON||'python3',[new URL('protect_fixtures.py',import.meta.url).pathname,path.join(directory,'jobs.json')],{encoding:'utf8',timeout:60000});
assert.equal(built.status,0,built.stderr);
assert(JSON.parse(built.stdout).every(r=>r.passed),built.stdout);
for(const filename of [original,...jobs.map(j=>j.output)]) {
 const bytes=fs.readFileSync(filename);
 const m=wabt.readWasm(Uint8Array.from(bytes), {readDebugNames:false});try{m.validate();}finally{m.destroy();}
 const api=await factory({wasmBinary:bytes});
 const candidates=Object.keys(api).filter(k=>typeof api[k]==='function'&&!k.startsWith('_'));
 const name=candidates.find(k=>/base64|encode/i.test(k));
 assert(name,`No Base64 export found: ${Object.keys(api).join(',')}`);
 for(const input of ['', 'a','abc','Hello World','中文 🌾',...Array.from({length:40},(_,i)=>'aB9+/'.repeat(i))]) {
  assert.equal(api[name](input),Buffer.from(input).toString('base64'));checks++;
 }
 records.push({filename:filename.split('/').pop(),passed:true});
}
const report={passed:true,checks,validators:['WABT','V8'],records};
if(process.argv[2]) fs.writeFileSync(process.argv[2],JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify(report,null,2));
}finally{fs.rmSync(directory,{recursive:true,force:true});}
