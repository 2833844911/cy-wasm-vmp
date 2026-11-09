"""Stable module-wide representatives for equivalent generic handlers."""
import random


class HandlerDeduplicator:
    def __init__(self, expansion_factor):
        if not isinstance(expansion_factor, int) or isinstance(expansion_factor, bool):
            raise ValueError('instruction_expansion_factor must be an integer')
        self.limit = max(1, expansion_factor)
        self.representatives = {}
        self.aliases = {}

    def register(self, key, handler_id):
        """Keep at most ``limit`` handlers per key, never replacing earlier IDs.

        Earlier functions may already contain a representative's opcode, so a
        later function must not shuffle or replace the retained representatives.
        Different variants retain independent IDs and randomized table layout.
        """
        keepers = self.representatives.setdefault(key, [])
        if len(keepers) < self.limit:
            keepers.append(handler_id)
            representative = handler_id
        else:
            representative = random.choice(keepers)
        self.aliases[handler_id] = representative
        return representative
