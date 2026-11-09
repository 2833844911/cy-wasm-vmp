/** Verify reused handlers avoid construction as well as preserving behavior. */
import wabtFactory from 'wabt';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import assert from 'node:assert/strict';
const wabt=await wabtFactory();
const directory=fs.mkdtempSync(path.join(os.tmpdir(),'wasm_early_dedup_'));
try{
 const functions=Array.from({length:64},(_,index)=>`(func (export "f${index}") (param i32) (result i32) (local i32)
  local.get 0 i32.const 5 i32.add local.set 1 local.get 1 i32.clz)`).join('\n');
 const parsed=wabt.parseWat('early-dedup.wat',`(module (memory 1) ${functions})`);
 parsed.validate();
 const source=Buffer.from(parsed.toBinary({}).buffer);parsed.destroy();
 const input=path.join(directory,'source.wasm');fs.writeFileSync(input,source);
 const original=new WebAssembly.Instance(new WebAssembly.Module(source)).exports;
 const records=[];let checks=0;
 for(const factor of [1,3,64]){
  const output=path.join(directory,`factor_${factor}.wasm`);
  const generated=spawnSync(process.env.PYTHON||'python3',[new URL('measure_handler_construction.py',import.meta.url).pathname,input,output,String(factor)],{encoding:'utf8',timeout:60000});
  assert.equal(generated.status,0,generated.stderr);
  const stats=JSON.parse(generated.stdout),bytes=fs.readFileSync(output);
  const decoded=wabt.readWasm(Uint8Array.from(bytes),{readDebugNames:false,multi_memory:true});
  try{decoded.validate({multi_memory:true});}finally{decoded.destroy();}
  const protectedExports=new WebAssembly.Instance(new WebAssembly.Module(bytes)).exports;
  for(let index=0;index<64;index++)for(const value of [0,1,-1,-5,-6,7,123456,2147483647,-2147483648]){
   assert.equal(protectedExports[`f${index}`](value),original[`f${index}`](value));checks++;
  }
  records.push({factor,passed:true,...stats});
 }
 assert(records.every(record=>record.genericOccurrences===records[0].genericOccurrences));
 // Body generation used to occur for every occurrence, so this count did not
 // fall with fewer retained variants. No wall-clock threshold is involved.
 assert(records[0].constructionCalls<records[1].constructionCalls);
 assert(records[1].constructionCalls<records[2].constructionCalls);
 assert(records[0].retainedGenericHandlers<records[1].retainedGenericHandlers);
 assert(records[1].retainedGenericHandlers<records[2].retainedGenericHandlers);
 const report={passed:true,originalFunctions:64,builds:records.length,checks,validators:['WABT','V8'],records};
 if(process.argv[2])fs.writeFileSync(process.argv[2],JSON.stringify(report,null,2)+'\n');
 console.log(JSON.stringify(report,null,2));
}finally{fs.rmSync(directory,{recursive:true,force:true});}
