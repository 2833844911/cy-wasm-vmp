/** Native memarg semantics, bit-exact float loads and app-memory isolation. */
import wabtFactory from 'wabt';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';
const wabt=await wabtFactory();
const loads=[['i32','load'],['i64','load'],['f32','load'],['f64','load'],
 ...['i32','i64'].flatMap(type=>['8_s','8_u','16_s','16_u',...(type==='i64'?['32_s','32_u']:[])].map(op=>[type,'load'+op]))];
const functions=[],names=[];
for(const [type,op] of loads)for(const offset of [0,1,13,4294967295]){
 const name=`${type}_${op}_${offset}`,result=type==='f32'?'i32':type==='f64'?'i64':type;
 names.push({name,offset});
 functions.push(`(func (export "${name}") (param i32) (result ${result}) local.get 0 ${type}.${op} offset=${offset} align=1 ${type==='f32'?'i32.reinterpret_f32':type==='f64'?'i64.reinterpret_f64':''})`);
}
const data=Buffer.from([0,127,128,255,1,0,0,128,0x45,0x23,0xc1,0x7f,0,0,0,128,1,0,0,0,0,0,0xf8,0x7f,0,0,0,0,0,0,0,128]);
const escaped=[...data].map(x=>'\\'+x.toString(16).padStart(2,'0')).join('');
const m=wabt.parseWat('loads.wat',`(module (memory (export "memory") 1 2) (data (i32.const 1024) "${escaped}") ${functions.join(' ')})`);
m.validate();const source=Buffer.from(m.toBinary({}).buffer);m.destroy();
function instantiate(bytes){const compiled=new WebAssembly.Module(bytes);const w=wabt.readWasm(Uint8Array.from(bytes),{multi_memory:true});try{w.validate({multi_memory:true});}finally{w.destroy();}return new WebAssembly.Instance(compiled).exports;}
function outcome(e,name,arg){try{return {value:e[name](arg)};}catch(error){if(error instanceof WebAssembly.RuntimeError)return {trap:true};throw error;}}
const directory=fs.mkdtempSync(path.join(os.tmpdir(),'vmp_scalar_loads_'));
try{
 const input=path.join(directory,'original.wasm');fs.writeFileSync(input,source);
 const original=instantiate(source);
 assert.equal(original.f32_load_0(1036),-2147483648,'f32 negative-zero fixture');
 assert.equal(original.f64_load_0(1048),-(1n<<63n),'f64 negative-zero fixture');
 assert.equal(original.f32_load_0(1032),0x7fc12345,'f32 NaN payload fixture');
 assert.equal(original.f64_load_0(1040),0x7ff8000000000001n,'f64 NaN payload fixture');
 const inputs=[0,1,1024,1025,1028,1032,1036,1040,1048,65528,65532,65535,65536,-1,-4,-16,2147483647,-2147483648];
 const expected=names.flatMap(f=>inputs.map(arg=>({name:f.name,arg,result:outcome(original,f.name,arg)})));
 const jobs=[20261109,20261110,20261111].map((seed,i)=>({name:`loads_${seed}`,input,output:path.join(directory,`loads_${seed}.wasm`),seed,notJeb:i!==1,factor:i===2?3:1}));
 const jobFile=path.join(directory,'jobs.json');fs.writeFileSync(jobFile,JSON.stringify(jobs));
 const generated=spawnSync(process.env.PYTHON||'python3',[new URL('protect_fixtures.py',import.meta.url).pathname,jobFile],{encoding:'utf8',timeout:120000});
 assert.equal(generated.status,0,generated.stderr);assert(JSON.parse(generated.stdout).every(r=>r.passed),generated.stdout);
 let checks=0,traps=0;const records=[];
 for(const job of jobs){const bytes=fs.readFileSync(job.output);let e=instantiate(bytes);
  for(const c of expected){const actual=outcome(e,c.name,c.arg);assert.deepStrictEqual(actual,c.result,`${job.name}: ${c.name}(${c.arg})`);checks++;
   assert.deepStrictEqual(new Uint8Array(e.memory.buffer),new Uint8Array(original.memory.buffer),'Load altered business memory');
   if(actual.trap){traps++;e=instantiate(bytes);} // SP recovery is outside this change.
  }
  records.push({seed:job.seed,bytes:bytes.length,passed:true});
 }
 const report={passed:true,scalarOpcodes:loads.length,functions:names.length,builds:jobs.length,checks,traps,
  validators:['WABT','V8'],scope:'Native immediate offsets including uint32 max, exact app bounds, signed/narrow loads, bit-preserving float reinterpretation and unchanged business memory; fresh instances after traps.',records};
 if(process.argv[2])fs.writeFileSync(process.argv[2],JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report,null,2));
}finally{fs.rmSync(directory,{recursive:true,force:true});}
