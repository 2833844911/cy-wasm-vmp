"""Size virtual operand-stack frames from the reachable, typed AST."""
TYPE_BYTES = {'i32': 4, 'i64': 8, 'f32': 4, 'f64': 8}


def operand_frame_bytes(nodes, results):
    """Return a 16-byte-aligned peak, including call results and both branches.

    The analyzer records byte heights before and after each reachable node.
    Locals live in interpreter locals and do not occupy this memory frame.
    """
    def width(types):
        try:
            return sum(TYPE_BYTES[kind] for kind in types)
        except KeyError as error:
            raise ValueError(f'Cannot size VMP frame with unresolved type {error.args[0]}') from error

    peak = width(results)
    pending = list(nodes)
    while pending:
        node = pending.pop()
        before = node['stack_bytes_before']
        after = node['stack_bytes_after']
        peak = max(peak, before, after)
        pending.extend(node['children'])
        pending.extend(node['else_children'])
    return max(16, (peak + 15) & ~15)
