/** Binary syntax/type validation only: never instantiate or run corpus modules. */
import wabtFactory from 'wabt';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import {parse,wat} from './wast_reader.mjs';
const wabt=await wabtFactory();
const source=process.argv[2];
if(!source)throw Error('Usage: node bench/test_syntax.mjs /path/to/testsuite [report.json]');
const requested='address,align,binary,binary-leb128,block,br,br_if,br_table,call,call_indirect,const,conversions,custom,data,data_drop0,elem,endianness,exports,float_exprs,float_literals,forward,func,func_ptrs,global,i32,i64,f32,f64,if,imports,int_exprs,int_literals,labels,left-to-right,linking,load,local_get,local_init,local_set,local_tee,loop,memory,memory_copy,memory_fill,memory_grow,memory_init,memory_redundancy,memory_size,memory_trap,names,nop,return,select,start,store,switch,table,table_copy,table_fill,table_get,table_grow,table_init,table_set,table_size,token,type,type-canon,type-equivalence,unreachable,unreached-invalid,unreached-valid,unwind,utf8-custom-section-id,utf8-import-field,utf8-import-module,utf8-invalid-encoding'.split(',');
const suites=requested.filter(s=>fs.existsSync(path.join(source,s+'.wast')));
function stringBytes(token){
 const text=token.slice(1,-1), bytes=[];
 for(let i=0;i<text.length;){
  if(text[i]!=='\\'){const code=text.codePointAt(i),char=String.fromCodePoint(code);bytes.push(...Buffer.from(char));i+=char.length;continue;}
  i++;
  if(/^[0-9a-fA-F]{2}$/.test(text.slice(i,i+2))){bytes.push(parseInt(text.slice(i,i+2),16));i+=2;}
  else {const escapes={n:10,r:13,t:9,'"':34,"'":39,'\\':92};if(!(text[i] in escapes))throw Error('Unsupported string escape');bytes.push(escapes[text[i++]]);}
 }
 return Buffer.from(bytes);
}
function compile(node){
 const kind=node.indexOf('binary');
 if(kind>=0)return Buffer.concat(node.slice(kind+1).map(stringBytes));
 const quote=node.indexOf('quote');
 const text=quote>=0?Buffer.concat(node.slice(quote+1).map(stringBytes)).toString('utf8'):wat(node);
 const m=wabt.parseWat('syntax.wat',text);
 try{m.resolveNames();m.validate();return Buffer.from(m.toBinary({}).buffer);}finally{m.destroy();}
}
function validate(bytes){
 // Record both independently even if the first one fails.
 let v8,wabtError;
 try{new WebAssembly.Module(bytes);}catch(error){v8=String(error);}
 try{const m=wabt.readWasm(Uint8Array.from(bytes),{readDebugNames:false});try{m.validate();}finally{m.destroy();}}catch(error){wabtError=String(error);}
 return {v8:v8||null,wabt:wabtError||null};
}
const dir=fs.mkdtempSync(path.join(os.tmpdir(),'wasm_syntax_'));
const jobs=[], records=[], intake=[],negative={tested:0,rejected:0,unprocessed:[],unexpectedlyAccepted:[]};
try{
 for(const suite of suites){
  let number=0;
  for(const command of parse(fs.readFileSync(path.join(source,suite+'.wast'),'utf8'))){
   if(command[0]==='module'){
    const name=`${suite}_${number++}`;
    try{
     const bytes=compile(command),original=validate(bytes);
     if(original.v8||original.wabt){intake.push({name,stage:'original validation',...original});continue;}
     const input=path.join(dir,name+'.wasm');fs.writeFileSync(input,bytes);
     for(const [seed,notJeb] of [[20261109,false],[20261110,true]]){
      const output=path.join(dir,`${name}_${seed}.wasm`);
      jobs.push({name,input,output,seed,notJeb});records.push({name,suite,seed,inputBytes:bytes.length,output});
     }
    }catch(error){intake.push({name,stage:'original compilation',error:String(error)});}
   }else if(['assert_invalid','assert_malformed'].includes(command[0])&&Array.isArray(command[1])&&command[1][0]==='module'){
    negative.tested++;
    try{const bytes=compile(command[1]),errors=validate(bytes);if(errors.v8||errors.wabt)negative.rejected++;else negative.unexpectedlyAccepted.push({suite,kind:command[0]});}
    catch(error){if(/parseWat failed|validate failed|resolveNames failed/.test(String(error)))negative.rejected++;else negative.unprocessed.push({suite,error:String(error)});}
   }
  }
 }
 fs.writeFileSync(path.join(dir,'jobs.json'),JSON.stringify(jobs));
 const built=spawnSync(process.env.PYTHON||'python3',[new URL('protect_fixtures.py',import.meta.url).pathname,path.join(dir,'jobs.json')],{encoding:'utf8',timeout:240000,maxBuffer:64*1024*1024});
 if(built.status!==0)throw Error(built.stderr||built.error);
 const results=JSON.parse(built.stdout);
 for(let i=0;i<records.length;i++){
  const r=records[i],g=results[i];
  if(!g.passed){r.status=/Unsupported WASM/.test(g.error)?'unsupported':'generation_error';r.error=g.error;}
  else{
   const bytes=fs.readFileSync(r.output),errors=validate(bytes);
   r.status=errors.v8||errors.wabt?'invalid_output':'valid';r.outputBytes=bytes.length;
   if(r.status!=='valid')r.errors=errors;
  }
  delete r.output;
 }
 const count=status=>records.filter(r=>r.status===status).length;
 const report={passed:count('invalid_output')===0&&count('generation_error')===0&&negative.unexpectedlyAccepted.length===0,suites:suites.length,originalModules:records.length/2,builds:records.length,
  validOutputs:count('valid'),invalidOutputs:count('invalid_output'),unsupported:count('unsupported'),generationErrors:count('generation_error'),
  scope:'Syntax/type checks only. No instantiation or runtime equivalence claim. Negative assertions test independent validators, not the VMP parser; unsupported features may be rejected before their declared invalidity is evaluated.',
  source:{repository:'https://github.com/WebAssembly/testsuite',commit:spawnSync('git',['-C',source,'rev-parse','HEAD'],{encoding:'utf8'}).stdout.trim()},
  environment:{node:process.version,wabt:'1.0.39'},negative,intake,records};
 fs.writeFileSync(process.argv[3]||new URL('syntax_results.json',import.meta.url),JSON.stringify(report,null,2)+'\n');
 console.log(JSON.stringify({...report,intakeCount:intake.length,intake:undefined,records:records.filter(r=>r.status==='invalid_output'||r.status==='generation_error')},null,2));
 process.exitCode=report.passed?0:1;
}finally{fs.rmSync(dir,{recursive:true,force:true});}
