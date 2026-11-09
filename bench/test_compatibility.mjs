/** Compile independent WAT fixtures, validate with WABT and V8, compare exports/traps. */
import wabtFactory from 'wabt';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import assert from 'node:assert/strict';
const wabt = await wabtFactory();
const fixtures = [];
const samples = {
  i32: [0, 1, -1, 7, -31, 2147483647, -2147483648],
  i64: [0n, 1n, -1n, 7n, -(1n<<40n), (1n<<63n)-1n, -(1n<<63n)],
  f32: [0, -0, 1.5, -2.75, 0.1, Infinity, NaN],
  f64: [0, -0, 1.5, -2.75, 0.1, Infinity, NaN],
};
function add(name, body, calls, {support = '', memory = true, global = true, dummy = true, selectedFunctions, expectReject = false} = {}) {
  const wat = `(module ${support} ${memory ? '(memory (export "memory") 512 4096)' : ''}
    ${global ? '(global (mut i32) (i32.const 123))' : ''}
    ${body} ${dummy ? '(func (result i32) i32.const 0)' : ''})`;
  fixtures.push({name, wat, calls, selectedFunctions, expectReject});
}
function numeric(op, input, output = input, unary = false) {
  const p = unary ? `(param ${input})` : `(param ${input} ${input})`;
  const code = unary ? 'local.get 0' : 'local.get 0 local.get 1';
  const args = samples[input].map((a, i) => unary ? [a] : [a, samples[input][(i+2)%samples[input].length]]);
  add(op, `(func (export "run") ${p} (result ${output}) ${code} ${op})`, args);
}
for (const type of ['i32', 'i64']) {
  for (const op of ['add','sub','mul','div_s','div_u','rem_s','rem_u','and','or','xor','shl','shr_s','shr_u','rotl','rotr']) numeric(`${type}.${op}`,type);
  for (const op of ['eq','ne','lt_s','lt_u','gt_s','gt_u','le_s','le_u','ge_s','ge_u']) numeric(`${type}.${op}`,type,'i32');
  for (const op of ['clz','ctz','popcnt']) numeric(`${type}.${op}`,type,type,true);
  numeric(`${type}.eqz`,type,'i32',true);
}
for (const type of ['f32','f64']) {
  for (const op of ['add','sub','mul','div','min','max','copysign']) numeric(`${type}.${op}`,type);
  for (const op of ['eq','ne','lt','gt','le','ge']) numeric(`${type}.${op}`,type,'i32');
  for (const op of ['abs','neg','ceil','floor','trunc','nearest','sqrt']) numeric(`${type}.${op}`,type,type,true);
}
for (const [op,input,output] of [
  ['i32.wrap_i64','i64','i32'], ['i64.extend_i32_s','i32','i64'], ['i64.extend_i32_u','i32','i64'],
  ['i32.extend8_s','i32','i32'], ['i32.extend16_s','i32','i32'],
  ['i64.extend8_s','i64','i64'], ['i64.extend16_s','i64','i64'], ['i64.extend32_s','i64','i64'],
  ['f32.demote_f64','f64','f32'],['f64.promote_f32','f32','f64'],
  ['i32.reinterpret_f32','f32','i32'],['i64.reinterpret_f64','f64','i64'],
  ['f32.reinterpret_i32','i32','f32'],['f64.reinterpret_i64','i64','f64'],
  ...['i32','i64'].flatMap(out=>['f32','f64'].flatMap(input=>['s','u'].flatMap(sign=>[
    [`${out}.trunc_${input}_${sign}`,input,out], [`${out}.trunc_sat_${input}_${sign}`,input,out]]))),
  ...['f32','f64'].flatMap(out=>['i32','i64'].flatMap(input=>['s','u'].map(sign=>[`${out}.convert_${input}_${sign}`,input,out])))
]) numeric(op,input,output,true);
for (const type of ['i32','i64','f32','f64']) {
  const variants = type[0] === 'f' ? [''] : type === 'i32' ? ['', '8_s','8_u','16_s','16_u'] : ['', '8_s','8_u','16_s','16_u','32_s','32_u'];
  for (const width of variants) {
    const storeWidth = width ? width.split('_')[0] : '';
    add(`${type}.load${width}`, `(func (export "run") (param ${type}) (result ${type})
      i32.const 4096 local.get 0 ${type}.store${storeWidth} offset=13 align=1
      i32.const 4096 ${type}.load${width} offset=13 align=1)`, samples[type].map(x=>[x]));
  }
  add(`${type}.select`, `(func (export "run") (param ${type} ${type} i32) (result ${type}) local.get 0 local.get 1 local.get 2 select)`,
      [0,1,-1].map(x=>[samples[type][3],samples[type][4],x]));
}
for (const type of ['i32','i64','f32','f64']) {
  add(`${type}.typed_select`, `(func (export "run") (param ${type} ${type} i32) (result ${type}) local.get 0 local.get 1 local.get 2 select (result ${type}))`,
      [0,1,-1].map(x=>[samples[type][3],samples[type][4],x]));
}
add('br_if_function', '(func (export "run") (param i32) (result i32) i32.const 77 local.get 0 br_if 0 drop i32.const 88)', [[0],[1],[-1]]);
add('br_function_stack_cleanup', '(func (export "run") (result i32) i32.const 999 i32.const 77 br 0)', [[]]);
add('block_result', '(func (export "run") (param i32) (result i32) (block (result i32) i32.const 77 local.get 0 br_if 0 drop i32.const 88))', [[0],[1],[-1]]);
add('block_stack_cleanup', '(func (export "run") (result i32) (block (result i32) i32.const 999 i32.const 77 br 0) i32.const 1 i32.add)', [[]]);
add('if_result', '(func (export "run") (param i32) (result i32) local.get 0 if (result i32) i32.const 11 else i32.const 22 end)', [[0],[1],[-1]]);
add('br_table', `(func (export "run") (param i32) (result i32) (local i32)
  block block block local.get 0 br_table 0 1 2 end i32.const 11 local.set 1 br 1 end i32.const 22 local.set 1 end local.get 1)`, [[0],[1],[2],[99],[-1]]);
add('br_table_value', '(func (export "run") (param i32) (result i32) block (result i32) i32.const 77 local.get 0 br_table 0 0 end)', [[0],[1],[-1]]);
add('call_import', '(func (export "run") (param i32) (result i32) local.get 0 call $inc)', [[0],[7],[-1]], {support:'(import "env" "inc" (func $inc (param i32) (result i32)))'});
add('call_indirect', '(func (export "run") (param i32) (result i32) local.get 0 i32.const 0 call_indirect (type $t))', [[0],[7],[-1]],
  {support:'(type $t (func (param i32) (result i32))) (table 1 funcref) (elem (i32.const 0) $inc) (func $inc (type $t) local.get 0 i32.const 5 i32.add)'});
add('multi_value', '(func (export "run") (param i32 i64) (result i64 i32) local.get 1 local.get 0)', [[7,9n],[-1,-99n]]);
add('mixed_call', '(func $mix (param i32 f64 i64 f32) (result f64 i64) local.get 1 local.get 2) (func (export "run") (param i32 f64 i64 f32) (result f64 i64) local.get 0 local.get 1 local.get 2 local.get 3 call $mix)', [[7,1.5,99n,-2.25]]);
add('memory_fill_copy', '(func (export "run") (param i32) (result i32) i32.const 4096 local.get 0 i32.const 16 memory.fill i32.const 8192 i32.const 4096 i32.const 16 memory.copy i32.const 8192 i32.load)', [[0],[37],[255]]);
add('memory_grow', '(func (export "run") (param i32) (result i32) local.get 0 memory.grow)', [[0],[1],[2]]);
add('memory_oob', '(func (export "run") (param i32) (result i32) local.get 0 i32.load)', [[4096],[-1],[33554432]]);
add('unreachable', '(func (export "run") (result i32) unreachable)', [[]]);
add('no_global', '(func (export "run") (param i32) (result i32) local.get 0 i32.const 3 i32.mul)', [[0],[7]], {global:false});
add('no_memory', '(func (export "run") (param i32) (result i32) local.get 0 i32.const 3 i32.mul)', [[0],[7]], {memory:false});
add('single_function', '(func (export "run") (param i32) (result i32) local.get 0 i32.const 3 i32.mul)', [[0],[7]], {dummy:false,selectedFunctions:[0]});
add('start_data', '(func $init i32.const 0 i32.const 99 i32.store) (start $init) (func (export "run") (result i32) i32.const 0 i32.load)', [[]], {support:'(data (i32.const 0) "abcd")'});
add('passive_data', '(func (export "run") (result i32) i32.const 4096 i32.const 0 i32.const 4 memory.init 0 data.drop 0 i32.const 4096 i32.load)', [[]], {support:'(data "abcd")'});
add('imported_global', '(func (export "run") (result i32) global.get 0)', [[]], {support:'(import "env" "g" (global i32))'});

// 0x0b can be a constant/index byte, not just an expression terminator.
for(const [kind,value] of [['i32','11'],['i64','11'],['f32','0x1p-105'],['f64','0x1p-847']]) {
  add(`global_immediate_0b_${kind}`, '(func (export "run") (result '+kind+') global.get 0)', [[]],
      {global:false,support:`(global ${kind} (${kind}.const ${value}))`});
}
add('global_init_index_11', '(func (export "run") (result i32) global.get 12)', [[]],
    {global:false,support:Array.from({length:12},(_,i)=>`(import "env" "g" (global $g${i} i32))`).join(' ')+ ' (global i32 (global.get $g11))'});

// Non-function imports must not shift the injected start function index.
add('imported_global_active_data', '(func (export "run") (result i32) i32.const 0 i32.load global.get 0 i32.xor)', [[]],
    {support:'(import "env" "g" (global i32)) (data (i32.const 0) "abcd")'});
add('imported_memory_active_data', '(func (export "run") (result i32) i32.const 0 i32.load)', [[]],
    {memory:false,support:'(import "env" "mem" (memory 512 4096)) (data (i32.const 0) "abcd")'});

// Index 128 needs a multi-byte signed LEB block type; index 64 must not mean void.
for (const index of [64,128]) {
  const types=Array.from({length:index},(_,i)=>`(type $unused${i} (func))`).join(' ')+` (type $result (func (result i32)))`;
  add(`block_type_${index}`, '(func (export "run") (result i32) block (type $result) i32.const 42 end)', [[]], {support:types});
}
add('loop_stack_cleanup', `(func (export "run") (result i32) (local i32)
 i32.const 1 loop local.get 0 i32.const 1 i32.add local.set 0 i32.const 2
 local.get 0 i32.const 10 i32.lt_s br_if 0 drop end)`, [[]]);
add('branch_stack_cleanup', '(func (export "run") (result i32) i32.const 1 block (result i32) i32.const 4 i32.const 8 br 0 end i32.add)', [[]]);
add('block_params_multi_results', '(func (export "run") (param i32 i64) (result i64 i32) local.get 0 local.get 1 block (param i32 i64) (result i64 i32) local.set 1 local.set 0 local.get 1 local.get 0 end)', [[7,99n],[-1,-99n]]);
add('empty_selection', '(func (export "run") (result i32) i32.const 42)', [[]], {selectedFunctions:[]});
add('reject_simd', '(func (export "run") (result i32) v128.const i32x4 1 2 3 4 i32x4.extract_lane 0)', [[]], {expectReject:true});
add('reject_references', '(func (export "run") (result i32) ref.null func ref.is_null)', [[]], {expectReject:true});

const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'wasm_compatibility_'));
const records = [], jobs = [];
let checks = 0;
const imports = () => ({env:{get mem(){return new WebAssembly.Memory({initial:512,maximum:4096});},inc:x=>(x+1)|0,g: new WebAssembly.Global({value:'i32'},42)}});
function outcome(e, args) {
  try { return {value:e.run(...args)}; }
  catch(error) { if(error instanceof WebAssembly.RuntimeError) return {trap:true}; throw error; }
}
function load(bytes) {
  assert(WebAssembly.validate(bytes), 'V8 rejected binary');
  const decoded = wabt.readWasm(Uint8Array.from(bytes), {readDebugNames:false});
  try { decoded.validate(); } finally { decoded.destroy(); }
  return new WebAssembly.Instance(new WebAssembly.Module(bytes),imports()).exports;
}
try {
  for (const f of fixtures) {
    const input=path.join(dir,`${f.name}.wasm`);
    const m=wabt.parseWat(f.name,f.wat); m.resolveNames(); m.validate();
    fs.writeFileSync(input,Buffer.from(m.toBinary({}).buffer)); m.destroy();
    const original=load(fs.readFileSync(input));
    // Expectations come from the independent original engine, never protected bytes.
    const expected=f.calls.map(args=>outcome(original,args));
    for(const [seed,factor] of [[20261109,1],[20261110,1],[20261111,3]]) {
      const output=path.join(dir,`${f.name}_${seed}.wasm`);
      jobs.push({name:f.name,input,output,seed,notJeb:seed!==20261110,factor,selectedFunctions:f.selectedFunctions});
      records.push({name:f.name,seed,factor,expected,calls:f.calls,output,expectReject:f.expectReject});
    }
  }
  fs.writeFileSync(path.join(dir,'jobs.json'),JSON.stringify(jobs));
  const built=spawnSync(process.env.PYTHON || 'python3',[new URL('protect_fixtures.py',import.meta.url).pathname,path.join(dir,'jobs.json')],{encoding:'utf8',maxBuffer:8*1024*1024,timeout:240000});
  if(built.status!==0) throw Error(built.stderr || built.error || 'fixture builder failed');
  const results=JSON.parse(built.stdout);
  for(let i=0;i<records.length;i++) {
    const r=records[i], generation=results[i];
    if(r.expectReject) {
      r.passed=!generation.passed && /Unsupported WASM/.test(generation.error);
      r.rejection=generation.error;
      if(!r.passed) r.error='Unsupported feature was not rejected clearly';
    } else if(!generation.passed) { r.error=generation.error;r.log=generation.log; }
    else try {
      const e=load(fs.readFileSync(r.output));
      for(let j=0;j<r.calls.length;j++) { assert.deepStrictEqual(outcome(e,r.calls[j]),r.expected[j]);checks++; }
      r.passed=true;r.bytes=fs.statSync(r.output).size;
    } catch(error) {r.error=String(error);}
    delete r.expected;delete r.calls;delete r.output;
    r.seconds=generation.seconds;r.protectedFunctions=generation.protectedFunctions;
  }
  const report={passed:records.every(r=>r.passed),fixtures:fixtures.length,builds:records.length,checks,
    validators:['WABT','V8'],environment:{node:process.version,platform:process.platform,arch:process.arch},records};
  const target=process.argv[2] || new URL('compatibility_results.json',import.meta.url);
  fs.writeFileSync(target,JSON.stringify(report,null,2)+'\n');
  console.log(JSON.stringify({...report,records:records.filter(r=>!r.passed)},null,2));
  process.exitCode=report.passed?0:1;
} finally {fs.rmSync(dir,{recursive:true,force:true});}
