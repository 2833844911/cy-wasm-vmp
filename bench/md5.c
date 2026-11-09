/*
 * Freestanding MD5 fixture for original-WASM / VMP-WASM comparisons.
 * No allocator, libc, imports, I/O, or host hash implementation is used.
 * Supported message length: 0..65536 bytes.
 *
 * WASM ABI:
 *   input_ptr() -> i32: writable 65536-byte input area
 *   output_ptr() -> i32: writable 16-byte digest area
 *   md5_hash(input_ptr, byte_length, output_ptr) -> i32: 0 success, 1 too long
 * The digest contains the conventional 16 MD5 bytes in little-endian order.
 */

typedef unsigned char u8;
typedef unsigned int u32;

#define EXPORT(name) __attribute__((export_name(name)))

static u8 input_buffer[65536];
static u8 output_buffer[16];

static const u32 md5_constants[64] = {
    0xd76aa478u, 0xe8c7b756u, 0x242070dbu, 0xc1bdceeeu,
    0xf57c0fafu, 0x4787c62au, 0xa8304613u, 0xfd469501u,
    0x698098d8u, 0x8b44f7afu, 0xffff5bb1u, 0x895cd7beu,
    0x6b901122u, 0xfd987193u, 0xa679438eu, 0x49b40821u,
    0xf61e2562u, 0xc040b340u, 0x265e5a51u, 0xe9b6c7aau,
    0xd62f105du, 0x02441453u, 0xd8a1e681u, 0xe7d3fbc8u,
    0x21e1cde6u, 0xc33707d6u, 0xf4d50d87u, 0x455a14edu,
    0xa9e3e905u, 0xfcefa3f8u, 0x676f02d9u, 0x8d2a4c8au,
    0xfffa3942u, 0x8771f681u, 0x6d9d6122u, 0xfde5380cu,
    0xa4beea44u, 0x4bdecfa9u, 0xf6bb4b60u, 0xbebfbc70u,
    0x289b7ec6u, 0xeaa127fau, 0xd4ef3085u, 0x04881d05u,
    0xd9d4d039u, 0xe6db99e5u, 0x1fa27cf8u, 0xc4ac5665u,
    0xf4292244u, 0x432aff97u, 0xab9423a7u, 0xfc93a039u,
    0x655b59c3u, 0x8f0ccc92u, 0xffeff47du, 0x85845dd1u,
    0x6fa87e4fu, 0xfe2ce6e0u, 0xa3014314u, 0x4e0811a1u,
    0xf7537e82u, 0xbd3af235u, 0x2ad7d2bbu, 0xeb86d391u
};

static const u8 md5_shifts[64] = {
    7,12,17,22, 7,12,17,22, 7,12,17,22, 7,12,17,22,
    5, 9,14,20, 5, 9,14,20, 5, 9,14,20, 5, 9,14,20,
    4,11,16,23, 4,11,16,23, 4,11,16,23, 4,11,16,23,
    6,10,15,21, 6,10,15,21, 6,10,15,21, 6,10,15,21
};

static u32 read_le32(const u8 *p) {
    return (u32)p[0] | ((u32)p[1] << 8) |
           ((u32)p[2] << 16) | ((u32)p[3] << 24);
}

static void write_le32(u8 *p, u32 value) {
    p[0] = (u8)value;
    p[1] = (u8)(value >> 8);
    p[2] = (u8)(value >> 16);
    p[3] = (u8)(value >> 24);
}

/* Keep the MD5 compression function distinct for selective-protection tests. */
__attribute__((noinline))
static void md5_transform(u32 state[4], const u8 block[64]) {
    u32 words[16];
    for (u32 i = 0; i < 16; ++i) {
        words[i] = read_le32(block + 4 * i);
    }

    u32 a = state[0], b = state[1], c = state[2], d = state[3];
    for (u32 i = 0; i < 64; ++i) {
        u32 f, g;
        if (i < 16) {
            f = (b & c) | (~b & d);
            g = i;
        } else if (i < 32) {
            f = (d & b) | (~d & c);
            g = (5 * i + 1) & 15;
        } else if (i < 48) {
            f = b ^ c ^ d;
            g = (3 * i + 5) & 15;
        } else {
            f = c ^ (b | ~d);
            g = (7 * i) & 15;
        }
        u32 value = a + f + md5_constants[i] + words[g];
        u32 shift = md5_shifts[i];
        u32 next_b = b + ((value << shift) | (value >> (32 - shift)));
        a = d;
        d = c;
        c = b;
        b = next_b;
    }
    state[0] += a;
    state[1] += b;
    state[2] += c;
    state[3] += d;
}

EXPORT("input_ptr")
u8 *md5_input_ptr(void) {
    return input_buffer;
}

EXPORT("output_ptr")
u8 *md5_output_ptr(void) {
    return output_buffer;
}

EXPORT("md5_hash")
u32 md5_hash(const u8 *input, u32 length, u8 *output) {
    if (length > 65536u) {
        return 1;
    }
    u32 state[4] = {0x67452301u, 0xefcdab89u, 0x98badcfeu, 0x10325476u};
    u32 offset = 0;
    while (length - offset >= 64u) {
        md5_transform(state, input + offset);
        offset += 64;
    }

    u8 padding[128];
    u32 remainder = length - offset;
    u32 padded_length = remainder < 56 ? 64 : 128;
    for (u32 i = 0; i < padded_length; ++i) {
        padding[i] = 0;
    }
    for (u32 i = 0; i < remainder; ++i) {
        padding[i] = input[offset + i];
    }
    padding[remainder] = 0x80;
    /* Upper length word is zero throughout the supported 0..65536 range. */
    write_le32(padding + padded_length - 8, length * 8u);
    md5_transform(state, padding);
    if (padded_length == 128) {
        md5_transform(state, padding + 64);
    }
    for (u32 i = 0; i < 4; ++i) {
        write_le32(output + 4 * i, state[i]);
    }
    return 0;
}
