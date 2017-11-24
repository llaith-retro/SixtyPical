# encoding: UTF-8

from sixtypical.ast import Program, Routine, Block, Instr
from sixtypical.model import (
    ConstantRef, LocationRef, PartRef,
    REG_A, REG_X, REG_Y, FLAG_Z, FLAG_N, FLAG_V, FLAG_C
)


class Context(object):
    def __init__(self):
        self._store = {}

    def __str__(self):
        return '\n'.join("%s: %s" % (name, value)
                         for (name, value) in sorted(self._store.iteritems())
                         if not isinstance(value, Routine))

    def get(self, ref):
        if isinstance(ref, ConstantRef):
            return ref.value
        elif isinstance(ref, LocationRef):
            return self._store[ref.name]
        elif isinstance(ref, PartRef):
            value = self.get(ref.ref)
            if ref.height == 0:
                return value & 255
            elif ref.height == 1:
                return (value >> 8) & 255
            else:
                raise NotImplementedError
        else:
            raise ValueError(ref)

    def set(self, ref, value):
        if isinstance(ref, PartRef):
            old = self.get(ref.ref)
            if ref.height == 0:
                value = (old & (255 << 8)) | value
            elif ref.height == 1:
                value = (value << 8) | (old & 255)
            else:
                raise NotImplementedError
            ref = ref.ref
        assert isinstance(ref, LocationRef)
        self._store[ref.name] = value


class Evaluator(object):

    def eval_program(self, program):
        assert isinstance(program, Program)
        context = Context()
        for ref in (REG_A, REG_X, REG_Y, FLAG_Z, FLAG_N, FLAG_V, FLAG_C):
            context.set(ref, 0)
        main = None

        for defn in program.defns:
            if defn.initial is not None:
                context.set(defn.location, defn.initial)

        for routine in program.routines:
            context.set(routine.location, routine)
            if routine.name == 'main':
                main = routine

        self.eval_routine(main, context)
        return context

    def eval_routine(self, routine, context):
        assert isinstance(routine, Routine)
        self.next_routine = routine
        while self.next_routine:
            routine = self.next_routine
            self.next_routine = None
            self.eval_block(routine.block, context)

    def eval_block(self, block, context):
        assert isinstance(block, Block)
        for i in block.instrs:
            self.eval_instr(i, context)
            if self.next_routine:
                break

    def eval_instr(self, instr, context):
        assert isinstance(instr, Instr)
        opcode = instr.opcode
        dest = instr.dest
        src = instr.src

        if opcode == 'ld':
            result = context.get(src)
            context.set(FLAG_Z, 1 if result == 0 else 0)
            context.set(FLAG_N, 1 if result & 128 else 0)
            context.set(dest, result)
        elif opcode == 'st':
            context.set(dest, context.get(src))
        elif opcode == 'add':
            carry = context.get(FLAG_C)
            val = context.get(src)
            now = context.get(dest)
            result = now + val + carry
            if result > 255:
                result &= 255
                context.set(FLAG_C, 1)
            else:
                context.set(FLAG_C, 0)
            context.set(FLAG_Z, 1 if result == 0 else 0)
            context.set(FLAG_N, 1 if result & 128 else 0)
            context.set(dest, result)
        elif opcode == 'sub':
            carry = context.get(FLAG_C)
            val = context.get(src)
            now = context.get(dest)
            result = now - val - carry
            if result < 0:
                result &= 255
                context.set(FLAG_C, 1)
            else:
                context.set(FLAG_C, 0)
            context.set(FLAG_Z, 1 if result == 0 else 0)
            context.set(FLAG_N, 1 if result & 128 else 0)
            context.set(dest, result)
        elif opcode == 'inc':
            val = context.get(dest)
            result = (val + 1) & 255
            context.set(FLAG_Z, 1 if result == 0 else 0)
            context.set(FLAG_N, 1 if result & 128 else 0)
            context.set(dest, result)
        elif opcode == 'dec':
            val = context.get(dest)
            result = (val - 1) & 255
            context.set(FLAG_Z, 1 if result == 0 else 0)
            context.set(FLAG_N, 1 if result & 128 else 0)
            context.set(dest, result)
        elif opcode == 'cmp':
            val = context.get(src)
            now = context.get(dest)
            result = now - val
            context.set(FLAG_Z, 1 if result == 0 else 0)
            context.set(FLAG_N, 1 if result & 128 else 0)
            if result < 0:
                result &= 255
                context.set(FLAG_C, 1)
            else:
                context.set(FLAG_C, 0)
        elif opcode == 'and':
            result = context.get(dest) & context.get(src)
            context.set(FLAG_Z, 1 if result == 0 else 0)
            context.set(FLAG_N, 1 if result & 128 else 0)
            context.set(dest, result)
        elif opcode == 'or':
            result = context.get(dest) | context.get(src)
            context.set(FLAG_Z, 1 if result == 0 else 0)
            context.set(FLAG_N, 1 if result & 128 else 0)
            context.set(dest, result)
        elif opcode == 'xor':
            result = context.get(dest) ^ context.get(src)
            context.set(FLAG_Z, 1 if result == 0 else 0)
            context.set(FLAG_N, 1 if result & 128 else 0)
            context.set(dest, result)
        elif opcode == 'shl':
            val = context.get(dest)
            carry = context.get(FLAG_C)
            context.set(FLAG_C, 1 if val & 128 else 0)
            result = ((val << 1) + carry) & 255
            context.set(FLAG_Z, 1 if result == 0 else 0)
            context.set(FLAG_N, 1 if result & 128 else 0)
            context.set(dest, result)
        elif opcode == 'shr':
            val = context.get(dest)
            carry = context.get(FLAG_C)
            context.set(FLAG_C, 1 if val & 1 else 0)
            result = (val >> 1) + (carry * 128)
            context.set(FLAG_Z, 1 if result == 0 else 0)
            context.set(FLAG_N, 1 if result & 128 else 0)
            context.set(dest, result)
        elif opcode == 'call':
            self.eval_routine(context.get(instr.location), context)
        elif opcode == 'goto':
            self.next_routine = context.get(instr.location)
        elif opcode == 'if':
            val = context.get(src)
            test = (val != 0) if not instr.inverted else (val == 0)
            if test:
                self.eval_block(instr.block1, context)
            elif instr.block2:
                self.eval_block(instr.block2, context)
        elif opcode == 'repeat':
            self.eval_block(instr.block, context)
            while context.get(src) == 0:
                self.eval_block(instr.block, context)
        elif opcode == 'copy':
            context.set(dest, context.get(src))
            # these are trashed; so could be anything really
            context.set(REG_A, 0)
            context.set(FLAG_Z, 0)
            context.set(FLAG_N, 0)
        elif opcode == 'copy[]':
            addr = context.get(dest)
            # memloc = memory[addr + context.get(REG_Y)]
            # context.set(memloc, context.get(src))
            context.set(dest, context.get(src))
            # these are trashed; so could be anything really
            context.set(REG_A, 0)
            context.set(FLAG_Z, 0)
            context.set(FLAG_N, 0)
        elif opcode == 'with-sei':
            self.eval_block(instr.block)
        else:
            raise NotImplementedError
