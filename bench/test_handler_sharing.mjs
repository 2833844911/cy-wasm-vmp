/** Cross-function generic-handler sharing and expansion-factor integration test. */
import wabtFactory from 'wabt';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import assert from 'node:assert/strict';
const wabt=await wabtFactory();
const directory=fs.mkdtempSync(path.join(os.tmpdir(),'wasm_handler_sharing_'));
try {
  // local.set and clz go through generic handlers. Later functions must retain
  // representatives whose opcodes have already been emitted for earlier ones.
  const functions=Array.from({length:64},(_,i)=>`(func (export "f${i}") (param i32) (result i32) (local i32)
    local.get 0 i32.const 5 i32.add local.set 1 local.get 1 i32.clz)`).join('\n');
  const source=wabt.parseWat('sharing.wat',`(module (memory 512 4096) (global (mut i32) (i32.const 0)) ${functions})`);
  source.validate();
  const input=path.join(directory,'original.wasm');
  fs.writeFileSync(input,Buffer.from(source.toBinary({}).buffer));source.destroy();
  const original=new WebAssembly.Instance(new WebAssembly.Module(fs.readFileSync(input))).exports;
  const jobs=[];
  for(const seed of [20261109,20261110])for(const factor of [1,3,64])
    jobs.push({name:`sharing_${seed}_${factor}`,input,output:path.join(directory,`sharing_${seed}_${factor}.wasm`),seed,notJeb:seed===20261109,factor});
  const jobPath=path.join(directory,'jobs.json');fs.writeFileSync(jobPath,JSON.stringify(jobs));
  const built=spawnSync(process.env.PYTHON||'python3',[new URL('protect_fixtures.py',import.meta.url).pathname,jobPath],{encoding:'utf8',timeout:60000,maxBuffer:4*1024*1024});
  assert.equal(built.status,0,built.stderr);
  const generated=JSON.parse(built.stdout);assert(generated.every(r=>r.passed),built.stdout);
  const records=[];let checks=0;
  for(const job of jobs){
    const bytes=fs.readFileSync(job.output);
    const decoded=wabt.readWasm(Uint8Array.from(bytes),{readDebugNames:false,multi_memory:true});try{decoded.validate({multi_memory:true});}finally{decoded.destroy();}
    const actual=new WebAssembly.Instance(new WebAssembly.Module(bytes)).exports;
    for(let i=0;i<64;i++)for(const x of [0,1,-1,-5,-6,7,123456,2147483647,-2147483648]){
      assert.equal(actual[`f${i}`](x),original[`f${i}`](x),`${job.name}: f${i}(${x})`);checks++;
    }
    records.push({seed:job.seed,factor:job.factor,bytes:bytes.length,passed:true});
  }
  for(const seed of [20261109,20261110]){
    const sizes=Object.fromEntries(records.filter(r=>r.seed===seed).map(r=>[r.factor,r.bytes]));
    assert(sizes[1]<sizes[3]&&sizes[3]<sizes[64],`Expected configured handler variants to increase size: ${JSON.stringify(sizes)}`);
  }
  const report={passed:true,fixtures:1,originalFunctions:64,builds:jobs.length,checks,validators:['WABT','V8'],records};
  if(process.argv[2])fs.writeFileSync(process.argv[2],JSON.stringify(report,null,2)+'\n');
  console.log(JSON.stringify(report,null,2));
}finally{fs.rmSync(directory,{recursive:true,force:true});}
