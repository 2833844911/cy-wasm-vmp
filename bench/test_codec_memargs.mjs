/** Verify scalar memory-index memargs independently of the VMP transform. */
import wabtFactory from 'wabt';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';
const wabt=await wabtFactory();
const kinds=[
 ['i32','i32.load'],['i64','i64.load'],['f32','f32.load'],['f64','f64.load'],
 ...['i32','i64'].flatMap(kind=>['8_s','8_u','16_s','16_u',...(kind==='i64'?['32_s','32_u']:[])].map(width=>[kind,`${kind}.load${width}`])),
 ['i32','i32.store'],['i64','i64.store'],['f32','f32.store'],['f64','f64.store'],
 ...['i32','i64'].flatMap(kind=>['8','16',...(kind==='i64'?['32']:[])].map(width=>[kind,`${kind}.store${width}`])),
];
const functions=[];
for(const memory of [0,1])for(const [kind,op] of kinds){
 const store=op.includes('.store')?op:`${kind}.store`,load=op.includes('.load')?op:`${kind}.load`;
 functions.push(`(func (export "f${functions.length}") (result ${kind}) i32.const 16 ${kind}.const 54321 ${store} ${memory} offset=257 align=1 i32.const 16 ${load} ${memory} offset=257 align=1)`);
}
const compiled=wabt.parseWat('memargs.wat',`(module (memory 1)(memory 1) ${functions.join(' ')})`,{multi_memory:true});
compiled.validate({multi_memory:true});
const fixtures=[{name:'all_scalar_memargs',bytes:Buffer.from(compiled.toBinary({}).buffer)},
 {name:'explicit_memory_zero',bytes:Buffer.from('0061736d010000000105016000017f0302010005030100010a0a0108004100284000050b','hex')}];
compiled.destroy();
const directory=fs.mkdtempSync(path.join(os.tmpdir(),'codec_memargs_'));
const records=[];let checks=0;
try{
 for(const fixture of fixtures){
  const input=path.join(directory,fixture.name+'.wasm'),output=path.join(directory,fixture.name+'_roundtrip.wasm'),report=path.join(directory,fixture.name+'.json');
  fs.writeFileSync(input,fixture.bytes);
  const run=spawnSync(process.env.PYTHON||'python3',[new URL('codec_roundtrip.py',import.meta.url).pathname,input,output,report],{encoding:'utf8',timeout:30000});
  assert.equal(run.status,0,run.stderr);
  const bytes=fs.readFileSync(output),metadata=JSON.parse(fs.readFileSync(report,'utf8'));
  const decoded=wabt.readWasm(Uint8Array.from(bytes),{readDebugNames:false,multi_memory:true});
  try{decoded.validate({multi_memory:true});}finally{decoded.destroy();}
  const original=new WebAssembly.Instance(new WebAssembly.Module(fixture.bytes)).exports;
  const rebuilt=new WebAssembly.Instance(new WebAssembly.Module(bytes)).exports;
  for(const key of Object.keys(original)){assert.deepStrictEqual(rebuilt[key](),original[key]());checks++;}
  if(fixture.name==='all_scalar_memargs'){
   assert.equal(new Set(metadata.operations.map(op=>op.opcode)).size,23);
   assert.equal(new Set(metadata.operations.map(op=>op.memoryIndex)).size,2);
   assert(metadata.operations.every(op=>op.alignment===0&&op.offset===257));
  }else assert.deepStrictEqual(metadata.operations,[{opcode:0x28,memoryIndex:0,alignment:0,offset:5}]);
  records.push({name:fixture.name,passed:true,scalarAccesses:metadata.operations.length});
 }
 const report={passed:true,checks,validators:['WABT','V8'],records};
 if(process.argv[2])fs.writeFileSync(process.argv[2],JSON.stringify(report,null,2)+'\n');
 console.log(JSON.stringify(report,null,2));
}finally{fs.rmSync(directory,{recursive:true,force:true});}
