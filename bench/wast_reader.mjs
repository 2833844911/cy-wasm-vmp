import assert from 'node:assert/strict';
export function parse(text) {
  // A small S-expression reader; comments can nest, quoted strings are opaque.
  const root=[], stack=[root];let i=0;
  while(i<text.length) {
    if(/\s/.test(text[i])) {i++;continue;}
    if(text.startsWith(';;',i)) {i=text.indexOf('\n',i);if(i<0)break;continue;}
    if(text.startsWith('(;',i)) {let depth=1;i+=2;while(depth&&i<text.length){if(text.startsWith('(;',i)){depth++;i+=2;}else if(text.startsWith(';)',i)){depth--;i+=2;}else i++;}continue;}
    if(text[i]==='('){const node=[];stack.at(-1).push(node);stack.push(node);i++;continue;}
    if(text[i]===')'){assert(stack.length>1);stack.pop();i++;continue;}
    let start=i;
    if(text[i]==='"'){i++;while(i<text.length){if(text[i]==='\\'){i+=2;continue;}if(text[i++]==='"')break;}}
    else while(i<text.length&&!/[\s()]/.test(text[i]))i++;
    stack.at(-1).push(text.slice(start,i));
  }
  assert.equal(stack.length,1);return root;
}
export const wat=x=>Array.isArray(x)?`(${x.map(wat).join(' ')})`:x;
