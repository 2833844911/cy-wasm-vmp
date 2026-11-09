"""Direct dispatch for the generated instruction interpreter.

Bytecode opcode words use compact randomized module-local IDs; immediate operands and
bytecode branch offsets retain their existing representation. Handler layout
is shuffled independently from opcode numbering.
"""
import random

from .utils import add_instr, pack_op


def _operand_value(operand):
    return operand['val'] if isinstance(operand, dict) else operand


def _handler_body(instructions, loop_depth):
    """Remove the dispatch guard and relocate external structured branches.

The original wrapper is ``if (pc == id) { body }`` inside the interpreter
loop. A branch to that wrapper exits the handler; under direct dispatch this
means starting the next interpreter iteration. Branches to inner labels stay
unchanged, while branches beyond the old loop keep their original target.
"""
    if (len(instructions) < 5 or
            [item[1] for item in instructions[:4]] != [0x20, 0x41, 0x46, 0x04] or
            instructions[-1][1] != 0x0B):
        raise ValueError('Unexpected VMP handler dispatch wrapper')

    body = []
    nesting = 0

    def relocate(depth):
        if depth < nesting:
            return depth
        # Original depths at this point: wrapper=nesting, loop=nesting+1.
        if depth <= nesting + 1:
            return nesting + loop_depth
        return depth + loop_depth - 1

    for instruction in instructions[4:-1]:
        opcode = instruction[1]
        if opcode in (0x0C, 0x0D):
            depth = _operand_value(instruction[2][0])
            instruction = add_instr(opcode, pack_op(relocate(depth)))
        elif opcode == 0x0E:
            operands = instruction[2]
            count = _operand_value(operands[0])
            instruction = add_instr(opcode, [pack_op(count)] + [
                pack_op(relocate(_operand_value(item))) for item in operands[1:]
            ])
        body.append(instruction)
        if opcode in (0x02, 0x03, 0x04):
            nesting += 1
        elif opcode == 0x0B:
            nesting -= 1
            if nesting < 0:
                raise ValueError('Unbalanced VMP handler body')
    if nesting:
        raise ValueError('Unbalanced VMP handler body')
    return body


def build_table_dispatch(blocks, opcodes, local_pc_idx):
    """Emit one ``br_table`` selection per virtual instruction.

The invalid-opcode arm traps instead of falling through into a handler. Every
normal handler returns directly to the existing interpreter loop.
"""
    if set(blocks) != set(opcodes):
        raise ValueError('Dispatch opcode/handler mismatch')
    if (len(set(opcodes.values())) != len(opcodes) or
            any(not isinstance(value, int) or value < 0 for value in opcodes.values())):
        raise ValueError('Dispatch opcode IDs must be unique nonnegative integers')
    if not blocks:
        return [add_instr(0x00)]

    layout = list(blocks)
    random.shuffle(layout)
    count = len(layout)
    positions = {key: position for position, key in enumerate(layout)}
    # Opcode chunks can contain holes. Route them to the invalid-opcode arm.
    targets = [count] * (max(opcodes.values()) + 1)
    for key, opcode in opcodes.items():
        targets[opcode] = positions[key]

    code = [add_instr(0x02, 0x40)]  # invalid-opcode exit
    code.extend(add_instr(0x02, 0x40) for _ in layout)
    code.append(add_instr(0x20, pack_op(local_pc_idx)))
    code.append(add_instr(0x0E, [pack_op(len(targets))] + [
        pack_op(target) for target in targets
    ] + [pack_op(count)]))
    for position, key in enumerate(layout):
        code.append(add_instr(0x0B))
        loop_depth = count - position
        code.extend(_handler_body(blocks[key], loop_depth))
        code.append(add_instr(0x0C, pack_op(loop_depth)))
    code.extend([add_instr(0x0B), add_instr(0x00)])
    return code
