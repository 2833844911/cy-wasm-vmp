#!/usr/bin/env python3
"""Generate a freestanding MD5 WASM fixture from source-level operations.

No compiler, binary parser, external download, or package is required. This is
an explicit encoding of the algorithm in md5.c using standard WASM 1.0 integer
operations. ABI: md5_hash(ptr,len,out)->status, input_ptr(), output_ptr().
"""
from pathlib import Path
import struct


def uleb(value):
    out = bytearray()
    while True:
        byte = value & 127
        value >>= 7
        out.append(byte | (128 if value else 0))
        if not value:
            return bytes(out)


def sleb(value):
    if value >= (1 << 31):
        value -= 1 << 32
    out = bytearray()
    while True:
        byte = value & 127
        value >>= 7
        done = (value == 0 and not byte & 64) or (value == -1 and byte & 64)
        out.append(byte | (0 if done else 128))
        if done:
            return bytes(out)


def vec(items):
    return uleb(len(items)) + b"".join(items)


def string(value):
    encoded = value.encode()
    return uleb(len(encoded)) + encoded


def section(number, payload):
    return bytes([number]) + uleb(len(payload)) + payload


def const(value):
    return b"\x41" + sleb(value)


def get(index):
    return b"\x20" + uleb(index)


def put(index):
    return b"\x21" + uleb(index)


def call(index):
    return b"\x10" + uleb(index)


def load(address, offset=0):
    return address + b"\x28" + uleb(2) + uleb(offset)


def store(address, value, offset=0):
    return address + value + b"\x36" + uleb(2) + uleb(offset)


def load8(address):
    return address + b"\x2d\x00\x00"


def store8(address, value):
    return address + value + b"\x3a\x00\x00"


def binary(opcode, left, right):
    return left + right + bytes([opcode])


def add(left, right):
    return binary(0x6a, left, right)


def mul(left, right):
    return binary(0x6c, left, right)


def bitand(left, right):
    return binary(0x71, left, right)


def bitor(left, right):
    return binary(0x72, left, right)


def xor(left, right):
    return binary(0x73, left, right)


def invert(value):
    return xor(value, const(0xffffffff))


def branch_if(condition, depth):
    return condition + b"\x0d" + uleb(depth)


def choose(condition, yes, no=b""):
    return condition + b"\x04\x40" + yes + (b"\x05" + no if no else b"") + b"\x0b"


def loop(condition_to_exit, body):
    return b"\x02\x40\x03\x40" + branch_if(condition_to_exit, 1) + body + b"\x0c\x00\x0b\x0b"


def function(local_count, instructions):
    declarations = vec([uleb(local_count) + b"\x7f"]) if local_count else b"\x00"
    body = declarations + instructions + b"\x0b"
    return uleb(len(body)) + body


K = [
    0xd76aa478,0xe8c7b756,0x242070db,0xc1bdceee,
    0xf57c0faf,0x4787c62a,0xa8304613,0xfd469501,
    0x698098d8,0x8b44f7af,0xffff5bb1,0x895cd7be,
    0x6b901122,0xfd987193,0xa679438e,0x49b40821,
    0xf61e2562,0xc040b340,0x265e5a51,0xe9b6c7aa,
    0xd62f105d,0x02441453,0xd8a1e681,0xe7d3fbc8,
    0x21e1cde6,0xc33707d6,0xf4d50d87,0x455a14ed,
    0xa9e3e905,0xfcefa3f8,0x676f02d9,0x8d2a4c8a,
    0xfffa3942,0x8771f681,0x6d9d6122,0xfde5380c,
    0xa4beea44,0x4bdecfa9,0xf6bb4b60,0xbebfbc70,
    0x289b7ec6,0xeaa127fa,0xd4ef3085,0x04881d05,
    0xd9d4d039,0xe6db99e5,0x1fa27cf8,0xc4ac5665,
    0xf4292244,0x432aff97,0xab9423a7,0xfc93a039,
    0x655b59c3,0x8f0ccc92,0xffeff47d,0x85845dd1,
    0x6fa87e4f,0xfe2ce6e0,0xa3014314,0x4e0811a1,
    0xf7537e82,0xbd3af235,0x2ad7d2bb,0xeb86d391,
]
S = [7,12,17,22]*4 + [5,9,14,20]*4 + [4,11,16,23]*4 + [6,10,15,21]*4
STATE = 69664
PADDING = 69728
INPUT = 4096
OUTPUT = 69632


def compress_function():
    # parameter block=0; locals a=1,b=2,c=3,d=4,i=5,f=6,g=7,value=8,next=9
    a,b,c,d,i,f,g,value,nxt = map(get, range(1,10))
    initial = b"".join(load(const(STATE), n*4) + put(n+1) for n in range(4))
    round1 = bitor(bitand(b,c),bitand(invert(b),d)) + put(6) + i + put(7)
    round2 = bitor(bitand(d,b),bitand(invert(d),c)) + put(6) + bitand(add(mul(const(5),i),const(1)),const(15)) + put(7)
    round3 = xor(xor(b,c),d) + put(6) + bitand(add(mul(const(3),i),const(5)),const(15)) + put(7)
    round4 = xor(c,bitor(b,invert(d))) + put(6) + bitand(mul(const(7),i),const(15)) + put(7)
    rounds = choose(binary(0x49,i,const(16)),round1,
        choose(binary(0x49,i,const(32)),round2,
            choose(binary(0x49,i,const(48)),round3,round4)))
    total = add(add(add(a,f),load(add(const(1024),mul(i,const(4))))),load(add(get(0),mul(g,const(4)))))
    update = total + put(8)
    update += add(b,binary(0x77,value,load8(add(const(1280),i)))) + put(9)
    update += d + put(1) + c + put(4) + b + put(3) + nxt + put(2)
    update += add(i,const(1)) + put(5)
    body = initial + const(0) + put(5)
    body += loop(binary(0x4f,i,const(64)),rounds + update)
    body += b"".join(store(const(STATE),add(load(const(STATE),n*4),get(n+1)),n*4) for n in range(4))
    return function(9,body)


def hash_function():
    # parameters input=0,len=1,out=2; locals offset=3,remainder=4,padded=5,i=6
    length,offset,rem,padded,i = get(1),get(3),get(4),get(5),get(6)
    body = choose(binary(0x4b,length,const(65536)),const(1)+b"\x0f")
    body += b"".join(store(const(STATE),const(v),n*4) for n,v in enumerate([0x67452301,0xefcdab89,0x98badcfe,0x10325476]))
    body += const(0) + put(3)
    body += loop(binary(0x49,binary(0x6b,length,offset),const(64)),
        add(get(0),offset)+call(0)+add(offset,const(64))+put(3))
    body += binary(0x6b,length,offset)+put(4)
    body += choose(binary(0x49,rem,const(56)),const(64)+put(5),const(128)+put(5))
    body += const(0)+put(6)
    body += loop(binary(0x4f,i,padded),store8(add(const(PADDING),i),const(0))+add(i,const(1))+put(6))
    body += const(0)+put(6)
    body += loop(binary(0x4f,i,rem),store8(add(const(PADDING),i),load8(add(add(get(0),offset),i)))+add(i,const(1))+put(6))
    body += store8(add(const(PADDING),rem),const(128))
    body += store(add(const(PADDING),binary(0x6b,padded,const(8))),mul(length,const(8)))
    body += const(PADDING)+call(0)
    body += choose(binary(0x46,padded,const(128)),const(PADDING+64)+call(0))
    body += b"".join(store(get(2),load(const(STATE),n*4),n*4) for n in range(4))
    body += const(0)
    return function(4,body)


def build():
    types = vec([b"\x60\x01\x7f\x00", b"\x60\x03\x7f\x7f\x7f\x01\x7f", b"\x60\x00\x01\x7f"])
    functions = vec([uleb(0),uleb(1),uleb(2),uleb(2)])
    memory = vec([b"\x01"+uleb(512)+uleb(4096)])  # 32 MiB initial / 256 MiB maximum.
    # The current VMP injector expects an existing Global section.
    globals_ = vec([b"\x7f\x01"+const(1048576)+b"\x0b"])
    exports = vec([
        string("memory")+b"\x02\x00",
        string("md5_hash")+b"\x00\x01",
        string("input_ptr")+b"\x00\x02",
        string("output_ptr")+b"\x00\x03",
    ])
    # output_ptr is deliberately last: the upstream VMP skips its last function.
    code = vec([compress_function(),hash_function(),function(0,const(INPUT)),function(0,const(OUTPUT))])
    table = struct.pack("<64I",*K)+bytes(S)
    data = vec([b"\x00"+const(1024)+b"\x0b"+uleb(len(table))+table])
    names = vec([uleb(0)+string("md5_transform"),uleb(1)+string("md5_hash"),uleb(2)+string("input_ptr"),uleb(3)+string("output_ptr")])
    name_section = string("name")+b"\x01"+uleb(len(names))+names
    return b"\x00asm\x01\x00\x00\x00"+b"".join([
        section(1,types),section(3,functions),section(5,memory),section(6,globals_),
        section(7,exports),section(10,code),section(11,data),section(0,name_section),
    ])


if __name__ == "__main__":
    path = Path(__file__).with_name("md5.wasm")
    module = build()
    path.write_bytes(module)
    print(f"Generated {path.name}: {len(module)} bytes")
