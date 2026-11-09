import {parse,wat} from './wast_reader.mjs';
/** Differential runner for module/invoke commands in official core WAST files. */
import wabtFactory from 'wabt';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import assert from 'node:assert/strict';
const wabt=await wabtFactory();
const source=process.argv[2];
if(!source) throw Error('Usage: node bench/test_spec.mjs /path/to/WebAssembly/testsuite [report.json] [suite,...]');
const suites=(process.argv[4] || 'i32,i64,f32,f64,conversions,select,local_get,local_set,local_tee,call,if,loop,block,br,br_if,br_table,call_indirect,unwind,return,func,int_exprs,float_exprs,endianness,load,store,align').split(',');
function compile(text) {const m=wabt.parseWat('spec.wat',text);try{m.resolveNames();m.validate({multi_memory:true});return Buffer.from(m.toBinary({}).buffer);}finally{m.destroy();}}
const constantCache=new Map();
function constant(c) {const key=wat(c);if(!constantCache.has(key)){const type=c[0].split('.')[0];const bytes=compile(`(module (func (export "v") (result ${type}) ${key}))`);constantCache.set(key,new WebAssembly.Instance(new WebAssembly.Module(bytes)).exports.v());}return constantCache.get(key);}
function outcome(e,call) {try{return {value:e[call.name](...call.args)};}catch(error){if(error instanceof WebAssembly.RuntimeError)return {trap:true};throw error;}}
const dir=fs.mkdtempSync(path.join(os.tmpdir(),'wasm_spec_'));
const cases=[], jobs=[], intake=[];
try {
 for(const suite of suites) {
  const commands=parse(fs.readFileSync(path.join(source,`${suite}.wast`),'utf8'));let current;const named=new Map();
  for(const c of commands) {
   if(c[0]==='module') {
    if(c.includes('binary')||c.includes('quote')) {current=null;intake.push({suite,kind:'unsupported module encoding'});continue;}
    const name=`${suite}_${cases.filter(x=>x.suite===suite).length}`;
    try {
     const bytes=compile(wat(c));
     const instance=new WebAssembly.Instance(new WebAssembly.Module(bytes),{});
     const input=path.join(dir,name+'.wasm'),output=path.join(dir,name+'_vmp.wasm');fs.writeFileSync(input,bytes);
     current={name,suite,original:instance.exports,calls:[],output};cases.push(current);
     if(typeof c[1]==='string'&&c[1].startsWith('$'))named.set(c[1],current);
     jobs.push({name,input,output,seed:20261109,notJeb:false});
    } catch(error) {current=null;intake.push({suite,kind:'original module unsupported by runner',error:String(error)});}
   } else if(['assert_return','assert_trap','assert_exhaustion','invoke'].includes(c[0])) {
    const inv=c[0]==='invoke'?c:c[1];
    if(!Array.isArray(inv)||inv[0]!=='invoke')continue;
    const namedTarget=inv[1].startsWith('$');const target=namedTarget?named.get(inv[1]):current;
    if(!target)continue;
    const idx=namedTarget?2:1;const name=JSON.parse(inv[idx]);
    if(c[0]==='assert_exhaustion'){intake.push({suite,kind:'stack exhaustion excluded'});continue;}
    const args=inv.slice(idx+1).map(constant);
    target.calls.push({name,args,expected:outcome(target.original,{name,args})});
   }
  }
 }
 fs.writeFileSync(path.join(dir,'jobs.json'),JSON.stringify(jobs));
 const built=spawnSync(process.env.PYTHON||'python3',[new URL('protect_fixtures.py',import.meta.url).pathname,path.join(dir,'jobs.json')],{encoding:'utf8',timeout:240000,maxBuffer:32*1024*1024});
 if(built.status!==0)throw Error(built.stderr||built.error);
 const generation=JSON.parse(built.stdout);const records=[];let checks=0;
 for(let i=0;i<cases.length;i++){
  const f=cases[i],r={name:f.name,suite:f.suite,calls:f.calls.length,checks:0,failures:[]};
  if(!generation[i].passed)r.error=generation[i].error;
  else try {
   const bytes=fs.readFileSync(f.output);
   // Both validators are required before invoking protected code.
   const m=new WebAssembly.Module(bytes);const w=wabt.readWasm(Uint8Array.from(bytes), {readDebugNames:false,multi_memory:true});try{w.validate({multi_memory:true});}finally{w.destroy();}
   const e=new WebAssembly.Instance(m,{}).exports;
   for(const c of f.calls){try{assert.deepStrictEqual(outcome(e,c),c.expected);checks++;r.checks++;}catch(error){r.failures.push({export:c.name,args:c.args.map(String),error:String(error)});}}
  }catch(error){r.error=String(error);}
  r.passed=!r.error&&!r.failures.length;records.push(r);
 }
 const report={passed:records.every(r=>r.passed),source:{repository:'https://github.com/WebAssembly/testsuite',commit:spawnSync('git',['-C',source,'rev-parse','HEAD'],{encoding:'utf8'}).stdout.trim()},scope:'Differential module/invoke commands only; invalid/malformed module assertions, register/linking and stack exhaustion are not conformance-tested.',suites,modules:records.length,validatedModules:records.filter(r=>!r.error).length,rejectedModules:records.filter(r=>r.error).length,behaviorFailures:records.reduce((sum,r)=>sum+r.failures.length,0),checks,intake,records};
 fs.writeFileSync(process.argv[3]||new URL('spec_results.json',import.meta.url),JSON.stringify(report,null,2)+'\n');
 console.log(JSON.stringify({...report,records:records.filter(r=>!r.passed)},null,2));process.exitCode=report.passed?0:1;
}finally{fs.rmSync(dir,{recursive:true,force:true});}
