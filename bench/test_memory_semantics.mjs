/** Differential checks of application-visible memory; private VMP memory is hidden. */
import wabtFactory from 'wabt';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import assert from 'node:assert/strict';
const wabt=await wabtFactory();
const fixtures=[];
function add(name,wat,actions,{freshActions=false,importMemory=null,windows=[],failedInstantiation=false}={}){
 fixtures.push({name,wat,actions,freshActions,importMemory,windows,failedInstantiation});
}
const action=(name,args=[])=>({name,args});
const memory='(memory (export "memory") 1 3)';
const sizing=`(func (export "size") (result i32) memory.size)
 (func (export "grow") (param i32) (result i32) local.get 0 memory.grow)
 (func (export "read") (param i32) (result i32) local.get 0 i32.load8_u)`;
add('size_grow_old_pages_and_max',`(module ${memory} ${sizing})`,[
 action('size'),action('grow',[0]),action('size'),action('grow',[1]),action('size'),
 action('read',[65536]),action('grow',[1]),action('size'),action('grow',[1]),action('size'),
 action('grow',[-1]),action('size'),action('grow',[0]),
]);
add('zero_minimum_maximum',`(module (memory (export "memory") 0 0) ${sizing})`,[
 action('size'),action('grow',[0]),action('grow',[1]),action('size'),action('read',[0]),
],{freshActions:true});
add('zero_minimum_grow',`(module (memory (export "memory") 0 2) ${sizing})`,[
 action('size'),action('grow',[1]),action('size'),action('read',[0]),action('grow',[1]),action('size'),action('grow',[1]),
]);
for(const [type,load,width,value] of [
 ['i32','i32.load8_u',1,37],['i32','i32.load16_u',2,12345],['i32','i32.load',4,12345678],
 ['i64','i64.load',8,1234567890123n],['f32','f32.load',4,1.25],['f64','f64.load',8,-2.5],
]){
 const store=load.includes('8_')?'i32.store8':load.includes('16_')?'i32.store16':`${type}.store`;
 add(`boundary_${load.replace('.','_')}`,`(module ${memory}
  (func (export "load") (param i32) (result ${type}) local.get 0 ${load})
  (func (export "store") (param i32 ${type}) local.get 0 local.get 1 ${store})
 )`,[
  action('load',[65536-width]),action('load',[65537-width]),action('load',[65536]),action('load',[-1]),
  action('store',[65536-width,value]),action('store',[65537-width,value]),action('store',[65536,value]),action('store',[-1,value]),
 ],{freshActions:true,windows:[[65520,16]]});
}
add('effective_address_offset_bounds',`(module ${memory}
 (func (export "read") (param i32) (result i32) local.get 0 i32.load offset=13)
 (func (export "write") (param i32) local.get 0 i32.const 17 i32.store offset=13)
)`,[action('read',[65519]),action('read',[65520]),action('read',[-1]),action('write',[65519]),action('write',[65520])],{freshActions:true,windows:[[65520,16]]});
for(const kind of ['i32','i64']) {
 add(`effective_address_overflow_${kind}`,`(module ${memory}
  (func (export "read") (param i32) (result ${kind}) local.get 0 ${kind}.load offset=4))`,
  [0,65528,65529,65532,65533,-4,-1].map(x=>action('read',[x])),{freshActions:true});
}
add('memory_fill_bounds',`(module ${memory}
 (func (export "fill") (param i32 i32 i32) local.get 0 local.get 1 local.get 2 memory.fill))`,[
 action('fill',[65535,37,1]),action('fill',[65535,37,2]),action('fill',[65536,37,0]),action('fill',[65537,37,0]),
 action('fill',[-1,37,1]),action('fill',[0,37,-1]),
],{freshActions:true,windows:[[0,32],[65520,16]]});
add('memory_copy_bounds',`(module ${memory} (data (i32.const 0) "abcdefgh")
 (func (export "copy") (param i32 i32 i32) local.get 0 local.get 1 local.get 2 memory.copy))`,[
 action('copy',[65532,0,4]),action('copy',[65533,0,4]),action('copy',[0,65532,4]),action('copy',[0,65533,4]),
 action('copy',[65536,65536,0]),action('copy',[65537,0,0]),action('copy',[0,65537,0]),action('copy',[-1,0,1]),
],{freshActions:true,windows:[[0,32],[65520,16]]});
add('memory_copy_overlap',`(module ${memory} (data (i32.const 0) "abcdefgh")
 (func (export "copy") (param i32 i32 i32) local.get 0 local.get 1 local.get 2 memory.copy))`,[
 action('copy',[1,0,7]),action('copy',[0,1,7]),action('copy',[8,0,8]),action('copy',[0,0,16]),
],{windows:[[0,32]]});
add('passive_memory_init_bounds',`(module ${memory} (data "abcdefgh")
 (func (export "init") (param i32 i32 i32) local.get 0 local.get 1 local.get 2 memory.init 0)
 (func (export "drop") data.drop 0))`,[
 action('init',[65532,0,4]),action('init',[65533,0,4]),action('init',[0,5,4]),action('init',[65536,8,0]),action('init',[65537,8,0]),
],{freshActions:true,windows:[[0,16],[65520,16]]});
add('passive_drop_state',`(module ${memory} (data "abcdefgh")
 (func (export "init") (param i32 i32 i32) local.get 0 local.get 1 local.get 2 memory.init 0)
 (func (export "drop") data.drop 0))`,[
 action('init',[0,0,8]),action('drop'),action('init',[8,0,0]),action('init',[8,0,1]),
],{windows:[[0,32]]});
add('active_data_and_protected_start',`(module ${memory} (data (i32.const 65528) "abcdefgh")
 (func $start i32.const 65528 i32.const 99 i32.store8) (start $start)
 (func (export "read") (result i32) i32.const 65528 i32.load)
 (func (export "tick") (result i32) i32.const 0 i32.const 0 i32.load i32.const 1 i32.add i32.store i32.const 0 i32.load)
)`,[action('read'),action('tick'),action('tick'),action('read'),action('tick')],{windows:[[0,16],[65520,16]]});
add('active_data_imported_global_offset',`(module (import "env" "value" (global i32)) ${memory}
 (data (global.get 0) "abcd")
 (func $start global.get 0 i32.const 1 i32.add i32.const 99 i32.store8) (start $start)
 (func (export "read") (result i32) global.get 0 i32.load))`,[action('read'),action('read')],{windows:[[32,32]]});
add('overlapping_active_data_segments',`(module ${memory}
 (data (i32.const 0) "abcdefgh") (data (i32.const 2) "XY")
 (func (export "read") (result i64) i32.const 0 i64.load)
 (func (export "tick") (result i32) i32.const 8 i32.const 8 i32.load i32.const 1 i32.add i32.store i32.const 8 i32.load))`,
 [action('read'),action('tick'),action('read'),action('tick')],{windows:[[0,32]]});
add('imported_memory_failed_active_initialization',`(module (import "env" "memory" (memory 1 1))
 (export "memory" (memory 0)) (data (i32.const 0) "abcdefgh") (data (i32.const 65535) "XY")
 (func (export "run") (result i32) i32.const 7))`,[],{importMemory:{initial:1,maximum:1},failedInstantiation:true});
add('active_segment_end_exact',`(module ${memory} (data (i32.const 65535) "x")
 (func (export "read") (result i32) i32.const 65535 i32.load8_u))`,[action('read'),action('read')],{windows:[[65520,16]]});
for(const maximum of [1,2]){
 add(`imported_memory_limits_${maximum}`,`(module (import "env" "memory" (memory 1 ${maximum}))
 (export "memory" (memory 0)) ${sizing})`,[
 action('size'),action('grow',[1]),action('size'),action('grow',[1]),action('size'),action('read',[65536]),
 ],{importMemory:{initial:1,maximum}});
}
add('imported_memory_data_and_start',`(module
 (import "env" "inc" (func $inc (param i32) (result i32)))
 (import "env" "memory" (memory 1 2)) (import "env" "value" (global i32))
 (export "memory" (memory 0)) (data (i32.const 32) "abcd")
 (func $start i32.const 0 global.get 0 call $inc i32.store) (start $start)
 (func (export "read") (result i32) i32.const 0 i32.load i32.const 32 i32.load i32.xor)
 (func (export "grow") (param i32) (result i32) local.get 0 memory.grow))`,[
 action('read'),action('grow',[1]),action('read'),action('grow',[1]),
],{importMemory:{initial:1,maximum:2},windows:[[0,48]]});
for(const marker of [1024,33554432,4294967295]) {
 add(`heap_marker_constant_${marker}`,`(module ${memory}
  (global (export "__heap_base") i32 (i32.const ${marker}))
  (func (export "read") (result i32) global.get 0))`,[action('read'),action('read')]);
}
add('heap_marker_imported_initializer',`(module (import "env" "value" (global i32)) ${memory}
 (global (export "__heap_base") i32 (global.get 0))
 (func (export "read") (result i32) global.get 1))`,[action('read'),action('read')]);
add('no_application_memory',`(module
 (func (export "run") (param i32) (result i32) local.get 0 i32.const 3 i32.mul))`,[
 action('run',[0]),action('run',[7]),action('run',[-1]),action('run',[123456]),
]);
add('business_data_at_old_vmp_base',`(module (memory (export "memory") 256 512)
 (data (i32.const 10485760) "APPDATA!")
 (func (export "read") (result i32) i32.const 10485760 i32.load)
 (func (export "write") (param i32) i32.const 10485760 local.get 0 i32.store)
 (func (export "sum") (param i32) (result i32) (local i32) (local i32)
  block loop local.get 1 local.get 0 i32.ge_u br_if 1
  local.get 2 local.get 1 i32.add local.set 2 local.get 1 i32.const 1 i32.add local.set 1 br 0 end end local.get 2)
)`,[action('read'),action('sum',[100]),action('read'),action('write',[1234567]),action('sum',[100]),action('read')],{windows:[[10485760,32],[11534320,32]]});
add('business_write_old_frame_region',`(module (memory (export "memory") 256 512)
 (func (export "write") (param i32) i32.const 11533312 local.get 0 i32.store)
 (func (export "read") (result i32) i32.const 11533312 i32.load)
 (func (export "call") (result i32) i32.const 5 i32.const 7 i32.mul))`,[
 action('write',[777]),action('call'),action('read'),action('write',[888]),action('call'),action('read'),
],{windows:[[11533312,32]]});
const directory=fs.mkdtempSync(path.join(os.tmpdir(),'wasm_memory_semantics_'));
const records=[],jobs=[];
const options={multi_memory:true};
function module(bytes){
 const compiled=new WebAssembly.Module(bytes);
 const decoded=wabt.readWasm(Uint8Array.from(bytes),{readDebugNames:false,...options});
 try{decoded.validate(options);}finally{decoded.destroy();}
 return compiled;
}
function instantiate(compiled,f){
 const memory=f.importMemory?new WebAssembly.Memory(f.importMemory):null;
 const imports={env:{inc:x=>(x+1)|0,value:new WebAssembly.Global({value:'i32'},41),...(memory?{memory}:{})}};
 const instance=new WebAssembly.Instance(compiled,imports);
 if(memory){assert.equal(instance.exports.memory,memory,'Imported memory identity changed');assert.equal(memory.buffer.byteLength,f.importMemory.initial*65536,'Imported memory initial size changed');}
 return instance.exports;
}
function invoke(exports,a){
 try{return {value:exports[a.name](...a.args)};}
 catch(error){if(error instanceof WebAssembly.RuntimeError)return {trap:true};throw error;}
}
function compareState(original,protected_,f){
 const a=original.memory,b=protected_.memory;
 assert.equal(Boolean(b),Boolean(a),'Application-visible memory export appeared or disappeared');
 if(original.__heap_base)assert.equal(protected_.__heap_base.value,original.__heap_base.value,'Application heap marker changed');
 if(!a)return;
 assert.equal(b.buffer.byteLength,a.buffer.byteLength,'Application memory size changed');
 for(const [offset,length] of f.windows){
  assert.deepStrictEqual(new Uint8Array(b.buffer,offset,length),new Uint8Array(a.buffer,offset,length),`Memory bytes differ at ${offset}`);
 }
 // Compare boundary bytes even in fixtures without explicit windows.
 for(const [offset,length] of [[0,Math.min(a.buffer.byteLength,32)],[Math.max(0,a.buffer.byteLength-32),Math.min(a.buffer.byteLength,32)]]){
  assert.deepStrictEqual(new Uint8Array(b.buffer,offset,length),new Uint8Array(a.buffer,offset,length),`Boundary memory differs at ${offset}`);
 }
}
try{
 for(const f of fixtures){
  const source=wabt.parseWat(f.name,f.wat,options);source.resolveNames();source.validate(options);
  const input=path.join(directory,f.name+'.wasm');fs.writeFileSync(input,Buffer.from(source.toBinary({}).buffer));source.destroy();
  const original=module(fs.readFileSync(input));
  for(const [seed,notJeb,factor] of [[20261109,false,1],[20261110,true,1],[20261111,true,3]]){
   const output=path.join(directory,`${f.name}_${seed}.wasm`);
   jobs.push({name:f.name,input,output,seed,notJeb,factor});records.push({name:f.name,seed,notJeb,factor,output,original,f});
  }
 }
 const jobPath=path.join(directory,'jobs.json');fs.writeFileSync(jobPath,JSON.stringify(jobs));
 const built=spawnSync(process.env.PYTHON||'python3',[new URL('protect_fixtures.py',import.meta.url).pathname,jobPath],{encoding:'utf8',maxBuffer:16*1024*1024,timeout:180000});
 if(built.status!==0)throw Error(built.stderr||built.error||'Fixture generation failed');
 const generation=JSON.parse(built.stdout);let checks=0,stateChecks=0,failedInstantiationChecks=0;
 for(let i=0;i<records.length;i++){
  const r=records[i],g=generation[i],f=r.f;
  if(!g.passed){r.error=g.error;r.log=g.log;}
  else try{
   const protectedModule=module(fs.readFileSync(r.output));
   assert.deepStrictEqual(WebAssembly.Module.exports(protectedModule),WebAssembly.Module.exports(r.original),'Public exports changed');
   assert.deepStrictEqual(WebAssembly.Module.imports(protectedModule),WebAssembly.Module.imports(r.original),'Application import types changed');
   if(f.importMemory){
    const maximum=f.importMemory.maximum;
    for(const spec of [{initial:0,maximum},{initial:1,maximum:1},{initial:1,maximum},{initial:1,maximum:maximum+1},{initial:maximum,maximum}]){
     const acceptance=compiled=>{
      const supplied=new WebAssembly.Memory(spec);
      try{
       const e=new WebAssembly.Instance(compiled,{env:{memory:supplied,inc:x=>(x+1)|0,value:new WebAssembly.Global({value:'i32'},41)}}).exports;
       assert.equal(e.memory,supplied);return 'accepted';
      }catch(error){if(error instanceof WebAssembly.LinkError)return 'link-error';if(error instanceof WebAssembly.RuntimeError)return 'runtime-error';throw error;}
     };
     assert.equal(acceptance(protectedModule),acceptance(r.original),`Import limit compatibility changed: ${JSON.stringify(spec)}`);stateChecks++;
    }
   }
   if(f.failedInstantiation){
    const observe=compiled=>{
     const supplied=new WebAssembly.Memory(f.importMemory);
     const bytes=new Uint8Array(supplied.buffer);
     for(let index=0;index<bytes.length;index++)bytes[index]=(index*13+7)&255;
     let error;
     try{new WebAssembly.Instance(compiled,{env:{memory:supplied}});}catch(caught){error=caught;}
     assert(error instanceof WebAssembly.RuntimeError,'Expected data-segment instantiation trap');
     return {trap:true,bytes:bytes.slice()};
    };
    for(let round=0;round<3;round++){
     assert.deepStrictEqual(observe(protectedModule),observe(r.original),'Failed instantiation changed host memory differently');
     failedInstantiationChecks++;stateChecks++;
    }
   }else for(let round=0;round<3;round++){
    let original=instantiate(r.original,f),protected_=instantiate(protectedModule,f);
    compareState(original,protected_,f);stateChecks++;
    for(const a of f.actions){
     if(f.freshActions){original=instantiate(r.original,f);protected_=instantiate(protectedModule,f);}
     const expected=invoke(original,a),actual=invoke(protected_,a);
     assert.deepStrictEqual(actual,expected,`${r.name}: ${a.name}(${a.args.map(String).join(',')})`);checks++;
     compareState(original,protected_,f);stateChecks++;
     // Preserve stateful grow/data tests, but do not reuse private SP after a trap.
     if(expected.trap&&!f.freshActions)break;
    }
   }
   r.passed=true;r.outputBytes=fs.statSync(r.output).size;
  }catch(error){r.error=String(error);}
  delete r.f;delete r.original;delete r.output;
 }
 const report={passed:records.every(r=>r.passed),fixtures:fixtures.length,builds:records.length,checks,stateChecks,failedInstantiationChecks,
  validators:['WABT','V8'],environment:{node:process.version,platform:process.platform,arch:process.arch},
  scope:'Original vs protected application memory sizes, grow results/max, exact-bound loads/stores and bulk memory, imported memory identity/limits, data/start behavior including overlapping segments and failed-instantiation host memory, hidden private memory and old reserved-region collisions. Fresh instances after traps; no post-trap SP recovery claim.',records};
 if(process.argv[2])fs.writeFileSync(process.argv[2],JSON.stringify(report,null,2)+'\n');
 console.log(JSON.stringify({...report,records:records.filter(r=>!r.passed)},null,2));process.exitCode=report.passed?0:1;
}finally{fs.rmSync(directory,{recursive:true,force:true});}
