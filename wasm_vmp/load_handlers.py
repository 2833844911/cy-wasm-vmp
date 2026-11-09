"""In-place scalar loads with native application memory addressing semantics."""
from .utils import add_instr, pack_op


def build_load_body(original_instruction, result_type, stack_local):
    """Replace the i32 address on the private stack with the loaded value.

    The original business instruction (including memarg) runs unchanged, so
    address+offset is checked by the engine without an intermediate i32 wrap.
    Untagged accesses below address the private VMP stack when over() finalizes
    the interpreter; the original instruction already carries its memory tag.
    """
    if not 0x28 <= original_instruction[1] <= 0x35:
        raise ValueError('Expected a scalar load instruction')
    store, size = {'i32': (0x36, 4), 'i64': (0x37, 8),
                   'f32': (0x38, 4), 'f64': (0x39, 8)}[result_type]
    body = [
        # Destination address remains below the loaded value on the WASM stack.
        add_instr(0x20, pack_op(stack_local)), add_instr(0x41, pack_op(4)), add_instr(0x6B),
        add_instr(0x20, pack_op(stack_local)), add_instr(0x41, pack_op(4)), add_instr(0x6B),
        add_instr(0x28, [pack_op(0), pack_op(0)]),
        original_instruction,
        add_instr(store, [pack_op(0), pack_op(0)]),
    ]
    if size == 8:
        body.extend([add_instr(0x20, pack_op(stack_local)), add_instr(0x41, pack_op(4)),
                     add_instr(0x6A), add_instr(0x21, pack_op(stack_local))])
    return body
