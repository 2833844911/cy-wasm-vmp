/** Regressions for typed operand stacks and nested virtual frame allocation. */
import wabtFactory from 'wabt';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import assert from 'node:assert/strict';
const wabt=await wabtFactory();
const fixtures=[];
const moduleText=body=>`(module (memory (export "memory") 512 4096) (global (mut i32) (i32.const 0)) ${body})`;
const push=(kind,count,value='0')=>`${kind}.const ${value} `.repeat(count);
const drops=count=>'drop '.repeat(count);
function add(name,body,calls,expectedTrap=false){fixtures.push({name,wat:moduleText(body),calls,expectedTrap});}
for(const [kind,counts,sentinel] of [
 ['i32',[255,256,257,300,2048,4097],'7'],
 ['i64',[127,128,129,300,1024,2049],'1234567890123'],
 ['f32',[255,257,300],'7.25'],
 ['f64',[127,129,300],'-9.5'],
]){
 for(const count of counts){
  // Callee's frame crosses the old fixed 1024-byte boundary and used to erase
  // the sentinel retained by its caller. Values and algorithms are source-built.
  add(`child_${kind}_${count}`,`(func $deep (result ${kind}) ${push(kind,count)} ${drops(count-1)})
   (func (export "run") (result ${kind}) ${kind}.const ${sentinel} call $deep drop)`,[[]]);
 }
}
add('mixed_multivalue_call',`(func $deep (result i32 i64 f32 f64)
 ${Array.from({length:100},()=> 'i32.const 0 i64.const 0 f32.const 0 f64.const 0').join(' ')}
 ${drops(400)} i32.const 11 i64.const 22 f32.const 3.5 f64.const 4.5)
 (func (export "run") (result i32 i64 f32 f64)
 i32.const 7 i64.const 9876543210123 f32.const -2.25 f64.const 19.5
 call $deep drop drop drop drop)`,[[]]);
add('large_multivalue_call_results',`(func $deep (result ${'i32 '.repeat(300)}) ${push('i32',300)})
 (func (export "run") (result i32) i32.const 7 call $deep ${drops(300)})`,[[]]);
add('deep_caller_live_values',`(func $deep (result i32) ${push('i64',300)} ${drops(300)} i32.const 99)
 (func (export "run") (result i32)
 i32.const 7 ${push('i32',400)} call $deep drop ${drops(400)})`,[[]]);
add('recursive_deep_stack',`(func $rec (param i32) (result i32) (local i32)
 local.get 0 i32.eqz if (result i32) i32.const 1 else
 i32.const 7 ${push('i32',300)}
 local.get 0 i32.const 1 i32.sub call $rec local.set 1
 ${drops(300)} local.get 1 i32.add end)
 (func (export "run") (param i32) (result i32) local.get 0 call $rec)`,[[0],[1],[2],[8],[16]]);
add('branch_peak_stack',`(func $deep (param i32) (result i32)
 local.get 0 if (result i32) ${push('i32',300)} ${drops(299)}
 else ${push('i64',180)} ${drops(180)} i32.const 3 end)
 (func (export "run") (param i32) (result i32) i32.const 7 local.get 0 call $deep drop)`,[[0],[1],[-1]]);
// The interpreter reserves a bounded stack arena; exhausting it must trap,
// rather than corrupt bytecode or a caller frame. This intentionally differs
// from native engine resource limits; high-depth original execution is not
// used as an equivalence oracle. Low depths still have to match the original.
add('recursive_arena_exhaustion',`(func $rec (param i32) (result i32) (local i32)
 local.get 0 i32.eqz if (result i32) i32.const 1 else
 i32.const 1 ${push('i32',4096)}
 local.get 0 i32.const 1 i32.sub call $rec local.set 1
 ${drops(4096)} local.get 1 i32.add end)
 (func (export "run") (param i32) (result i32) local.get 0 call $rec)`,[[100]],true);
for(const heap of [1024,33554432,4294967295]) {
 add(`heap_marker_${heap}`, `(global (export "__heap_base") i32 (i32.const ${heap}))
  (func (export "run") (result i32) i32.const 7)`,[[]]);
}
const dir=fs.mkdtempSync(path.join(os.tmpdir(),'vmp_stack_frames_'));
const records=[],jobs=[];
function instance(bytes){
 const module=new WebAssembly.Module(bytes);
 const decoded=wabt.readWasm(Uint8Array.from(bytes),{readDebugNames:false,multi_memory:true});
 try{decoded.validate({multi_memory:true});}finally{decoded.destroy();}
 return new WebAssembly.Instance(module).exports;
}
try{
 for(const f of fixtures){
  const input=path.join(dir,f.name+'.wasm');
  const m=wabt.parseWat(f.name,f.wat);m.resolveNames();m.validate({multi_memory:true});
  fs.writeFileSync(input,Buffer.from(m.toBinary({}).buffer));m.destroy();
  const original=instance(fs.readFileSync(input));
  const expected=f.expectedTrap ? null : f.calls.map(args=>original.run(...args));
  const baselineCalls=f.expectedTrap ? [[0],[1],[2]] : [];
  const baselineExpected=baselineCalls.map(args=>original.run(...args));
  for(const [seed,notJeb,factor] of [[20261109,false,1],[20261110,true,1],[20261111,true,3]]){
   const output=path.join(dir,`${f.name}_${seed}.wasm`);
   jobs.push({name:f.name,input,output,seed,notJeb,factor});
   records.push({name:f.name,seed,notJeb,factor,expected,baselineCalls,baselineExpected,expectedTrap:f.expectedTrap,calls:f.calls,output});
  }
 }
 fs.writeFileSync(path.join(dir,'jobs.json'),JSON.stringify(jobs));
 const built=spawnSync(process.env.PYTHON||'python3',[new URL('protect_fixtures.py',import.meta.url).pathname,path.join(dir,'jobs.json')],{encoding:'utf8',maxBuffer:16*1024*1024,timeout:180000});
 if(built.status!==0)throw Error(built.stderr||built.error||'Fixture generation failed');
 const generation=JSON.parse(built.stdout);
 let checks=0,arenaTrapChecks=0;
 for(let i=0;i<records.length;i++){
  const r=records[i],g=generation[i];
  if(!g.passed){r.error=g.error;r.log=g.log;}
  else try{
   const bytes=fs.readFileSync(r.output);
   const e=instance(bytes);
   assert(g.stackFloor>0 && g.stackFloor%16===0);
   assert.equal(g.memoryIndex,1);
   assert.equal(g.stackTop,g.stackFloor+g.stackCapacity);
   if(e.__heap_base) {
    const originalHeap=Number(r.name.split('_').at(-1));
    assert.equal(e.__heap_base.value>>>0,originalHeap);
   }
   for(const size of Object.values(g.frameSizes))assert(size>=16 && size%16===0 && size<=g.stackCapacity);
   r.frameSizes=g.frameSizes;r.stackCapacity=g.stackCapacity;
   for(let j=0;j<r.baselineCalls.length;j++){assert.deepStrictEqual(e.run(...r.baselineCalls[j]),r.baselineExpected[j]);checks++;}
   // Repeat calls to detect restoration errors that a first invocation can hide.
   for(let round=0;round<3;round++)for(let j=0;j<r.calls.length;j++){
    if(r.expectedTrap){
      const fresh=instance(bytes);
      const businessBytes=new Uint8Array(fresh.memory.buffer);
      const before=businessBytes.slice();
      assert.throws(()=>fresh.run(...r.calls[j]),WebAssembly.RuntimeError);
      assert.deepStrictEqual(businessBytes,before,'Private stack exhaustion changed business memory');
      arenaTrapChecks++;
    }
    else {assert.deepStrictEqual(e.run(...r.calls[j]),r.expected[j]);checks++;}
   }
   r.passed=true;r.outputBytes=fs.statSync(r.output).size;
  }catch(error){r.error=String(error);}
  delete r.expected;delete r.calls;delete r.baselineExpected;delete r.baselineCalls;delete r.output;
 }
 const report={passed:records.every(r=>r.passed),fixtures:fixtures.length,builds:records.length,checks,arenaTrapChecks,
  validators:['WABT','V8'],environment:{node:process.version,platform:process.platform,arch:process.arch},
  scope:'Typed operand stacks at and beyond the old 1024-byte frame, mixed/multi-value calls, recursive calls, branch peaks and repeated invocations. Expected values come from independent original WASM execution. Bounded-arena exhaustion checks are separately counted and intentionally expect a protected runtime trap; high-depth original execution is not claimed to complete within native engine limits.',records};
 if(process.argv[2])fs.writeFileSync(process.argv[2],JSON.stringify(report,null,2)+'\n');
 console.log(JSON.stringify({...report,records:records.filter(r=>!r.passed)},null,2));
 process.exitCode=report.passed?0:1;
}finally{fs.rmSync(dir,{recursive:true,force:true});}
