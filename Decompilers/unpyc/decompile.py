#!/usr/bin/env python
##WingHeader v1 
###############################################################################
## File       :  decompile.py
## Description:  
##            :  
## Created_On :  Sat Oct 16 12:55:01 2010
## Created_By :  Rich Smith
## Modified_On:  Wed Dec  8 18:34:02 2010
## Modified_By:  Rich Smith
##
## (c) Copyright 2010, Rich Smith all rights reserved.
###############################################################################
#!/usr/bin/python

# [The "BSD licence"]
# Copyright (c) 2008-2009 Dmitri Kornev
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * The name of the author may not be used to endorse or promote products
#       derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE AUTHOR ''AS IS'' AND ANY
# EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL Dmitri Kornev BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

'''
Core functions for decompiling basic blocks.

'''

import sys
import traceback

from opcodes import cmp_op
import parse
import disasm
import structure

from ast import *
from text import d_indentText as indentText, \
                 d_ind as ind

def dbgprint(s):
    #print >> sys.stderr, s
    pass

# TODO: defined new stack... not to call dec() after each pop()

class Decompiler:
    '''Decompiler itself.'''

    def __init__(self, disassembler, debugDraw=False):
        '''
        @param disassembler:
            L{Disassembler} to get command list, code blocks and such.
        @param debugDraw:
            if true, intermediate CFGs are saved. See L{structure}
            for more details.

        '''
        self.disassembler = disassembler
        self.debugDraw = debugDraw
        self.co = disassembler.co
        self.postponedStores = []
        
        #RICH TEMP
        self.richy_count = 0

    def findCoByName(self, name):
        '''
        @return: code object with a given name.

        '''
        for x in self.co.consts.value:
            if isinstance(x, parse.pyCode) and x.name.value == name:
                return x
        return None

    @staticmethod
    def checkStack(stack, depth):
        '''
        @return:
            True if stack is of given depth. Instances of DummyEx are
            ignored.

        '''
        counter = 0
        for x in stack:
            if not isinstance(x, DummyEx):
                counter += 1
        return counter == depth

    def STORE(self, lvalue, rvalue, curIndent, emptystack):
        '''
        This method handles all STORE_* commands.

        @param lvalue: destination, where data is stored.
        @param rvalue: source of data.
        @param curIndent: current indent in the generated source code.
        @param emptystack: should be True if no postponed stores are expected.

        '''
        r = ''
        if isinstance(rvalue, NewFunction):
            r += ind(curIndent) + 'def ' + lvalue + '('
            r += rvalue.getParams()
            r += '):\n'
            da = disasm.Disassembler(rvalue.value, optimizeJumps=True)
            x = Decompiler(da).decompile(startIndent=curIndent+1)
            #FixMe
            if x != None:
                if x in ('', '\n'): x = ind(curIndent + 1) + 'pass\n'
                r += x + '\n'
        elif isinstance(rvalue, NewClass):
            r += 'class ' + lvalue + '('
            r += ', '.join(x.value for x in rvalue.baseclasses.value)
            r += '):\n'
            # offset=6 to avoid __module__ = __name__ duplication
            co = self.findCoByName(rvalue.classname.value)
            da = disasm.Disassembler(co, optimizeJumps=True)
            dc = Decompiler(da)
            x = dc.decompile(offset=6, startIndent=curIndent+1)
            #FixMe
            if x != None:
                x += '\n'
                if x in ('', '\n'): x = ind(curIndent + 1) + 'pass\n'
                r += x + '\n'
        elif isinstance(rvalue, Import):
            if rvalue.module.split('.')[0] != lvalue:
                # TODO: recheck if rvalue can be != self.co.names... here...
                r += ind(curIndent) + \
                     'import %s as %s\n' % (rvalue.module, lvalue)
            else:
                r += ind(curIndent) + 'import %s\n' % rvalue.module
        elif isinstance(rvalue, ImportFrom):
            rvalue.importobj.addFrom(rvalue.name, lvalue)
        elif isinstance(rvalue, InplaceOp):
            storedIn = str(lvalue) + ' '
            if storedIn == str(rvalue)[:len(storedIn)]:
                r += ind(curIndent) + str(rvalue) + '\n'
            else:
                r += ind(curIndent) + '# INPLACE_* op used not as INPLACE!!!\n'
                # TODO: possible error
                r += ind(curIndent) + str(lvalue) + ' = ' + \
                     rvalue.children[0] + ' ' + rvalue.value + \
                     ' ' + rvalue.children[1] + '\n'
        elif isinstance(rvalue, Iterator):
            r += ind(curIndent) + 'for ' + str(lvalue) + ' in ' + \
                 str(rvalue) + ':\n'
        elif isinstance(rvalue, DummyEx):
            # quite a hack here... take a look at mergeCompoundNodes
            # for more info
            r += '# as ' + str(lvalue) + '\n'
        else:
            if not emptystack:
                self.postponedStores.append((lvalue, rvalue))
            else:
                if len(self.postponedStores) == 0:
                    r += ind(curIndent) + str(lvalue) + ' = ' + \
                         str(rvalue) + '\n'
                else:
                    self.postponedStores.append((lvalue, rvalue))
                    r += ind(curIndent) + '(' + \
                        ', '.join(str(x[0]) for x in self.postponedStores) + \
                        ') = (' + \
                        ', '.join(str(x[1]) for x in self.postponedStores) + \
                        ')\n'
                    self.postponedStores = []
        return r

    ####################################
    # actions for commands in bytecode #
    ####################################

    def _STOP_CODE(self, cmd, prevcmd, nextcmd, stack, curIndent):
        pass

    def _POP_TOP(self, cmd, prevcmd, nextcmd, stack, curIndent):
        # TODO: tests/all_opcodes/prints.py fails becaues of POP_TOP
        # TODO: POP_TOP should process postponedStores...
        r = ''
        ## XXX Rich
        try:
            o = stack.pop()
        except IndexError, err:
            print "XXXX: pop from empty stack caught _POP_TOP, returning: ",r
            return r
        o.dec()
        if o.isLastCopy():
            if isinstance(o, Import):
                level = '.' * o.level.value
                a = []
                for f in o.froms:
                    if f[0] != f[1]:
                        a.append('%s as %s' % (f[0], f[1]))
                    else:
                        a.append(f[0])
                r += ind(curIndent) + \
                     'from %s%s import %s\n' % (level, o.module, ', '.join(a))
            elif isinstance(o, DummyEx):
                pass
            elif not isinstance(o, CompareOp) and \
                 not isinstance(o, YieldedValue):
                r += ind(curIndent) + str(o) + '\n'
        return r

    def _ROT_TWO(self, cmd, prevcmd, nextcmd, stack, curIndent):
        (stack[-1], stack[-2]) = \
        (stack[-2], stack[-1])

    def _ROT_THREE(self, cmd, prevcmd, nextcmd, stack, curIndent):
        (stack[-1], stack[-2], stack[-3]) = \
        (stack[-2], stack[-3], stack[-1])

    def _DUP_TOP(self, cmd, prevcmd, nextcmd, stack, curIndent):
        stack.append(stack[-1])
        stack[-1].inc()

    def _ROT_FOUR(self, cmd, prevcmd, nextcmd, stack, curIndent):
        (stack[-1], stack[-2], stack[-3], stack[-4]) = \
        (stack[-2], stack[-3], stack[-4], stack[-1])

    def _NOP(self, cmd, prevcmd, nextcmd, stack, curIndent):
        pass

    def _UNARY_POSITIVE(self, cmd, prevcmd, nextcmd, stack, curIndent):
        stack[-1] = PositiveOp(stack[-1])

    def _UNARY_NEGATIVE(self, cmd, prevcmd, nextcmd, stack, curIndent):
        stack[-1] = NegativeOp(stack[-1])

    def _UNARY_NOT(self, cmd, prevcmd, nextcmd, stack, curIndent):
        # TODO: old dead code... rewrite
        if stack[-1].__class__.__name__ == 'IfExpression':
            stack[-1] = IfExpression('not' + '(' + stack[-1].__repr__() + ')')
        else:
            stack[-1] = BooleanNOTOp(stack[-1])

    def _UNARY_CONVERT(self, cmd, prevcmd, nextcmd, stack, curIndent):
        stack[-1] = ConvertOp(stack[-1])

    def _UNARY_INVERT(self, cmd, prevcmd, nextcmd, stack, curIndent):
        stack[-1] = BitwiseNOTOp(stack[-1])

    def _LIST_APPEND(self, cmd, prevcmd, nextcmd, stack, curIndent):
        # TODO: LIST_APPEND
        pass

    def _BINARY_POWER(self, cmd, prevcmd, nextcmd, stack, curIndent):
        stack[-2] = ExponentiationOp(stack[-2], stack[-1])
        stack.pop().dec()

    def _BINARY_MULTIPLY(self, cmd, prevcmd, nextcmd, stack, curIndent):
        stack[-2] = MultiplicationOp(stack[-2], stack[-1])
        stack.pop().dec()

    def _BINARY_DIVIDE(self, cmd, prevcmd, nextcmd, stack, curIndent):
        stack[-2] = DivisionOp(stack[-2], stack[-1])
        stack.pop().dec()

    def _BINARY_MODULO(self, cmd, prevcmd, nextcmd, stack, curIndent):
        stack[-2] = RemainderOp(stack[-2], stack[-1])
        stack.pop().dec()

    def _BINARY_ADD(self, cmd, prevcmd, nextcmd, stack, curIndent):
        stack[-2] = AdditionOp(stack[-2], stack[-1])
        stack.pop().dec()

    def _BINARY_SUBTRACT(self, cmd, prevcmd, nextcmd, stack, curIndent):
        stack[-2] = SubtractionOp(stack[-2], stack[-1])
        stack.pop().dec()

    def _BINARY_SUBSCR(self, cmd, prevcmd, nextcmd, stack, curIndent):
        stack[-2] = SubscriptionOp(stack[-2], stack[-1])
        stack.pop().dec()

    def _BINARY_FLOOR_DIVIDE(self, cmd, prevcmd, nextcmd, stack, curIndent):
        stack[-2] = FloorDivisionOp(stack[-2], stack[-1])
        stack.pop().dec()

    def _BINARY_TRUE_DIVIDE(self, cmd, prevcmd, nextcmd, stack, curIndent):
        r = ind(curIndent) + '# from __future__ import division\n' + \
            ind(curIndent) + '# CAUTION! future division detected!\n'
        stack[-2] = DivisionOp(stack[-2], stack[-1])
        stack.pop().dec()
        return r

    def _INPLACE_FLOOR_DIVIDE(self, cmd, prevcmd, nextcmd, stack, curIndent):
        stack[-2] = InplaceFloorDivisionOp(stack[-2], stack[-1])
        stack.pop().dec()

    def _INPLACE_TRUE_DIVIDE(self, cmd, prevcmd, nextcmd, stack, curIndent):
        r = ind(curIndent) + '# from __future__ import division\n' + \
            ind(curIndent) + '# CAUTION! future division detected!\n'
        stack[-2] = InplaceDivisionOp(stack[-2], stack[-1])
        stack.pop().dec()
        return r

    def _SLICE(self, cmd, prevcmd, nextcmd, stack, curIndent):
        stack[-1] = SliceOp(stack[-1])

    def _SLICE_1(self, cmd, prevcmd, nextcmd, stack, curIndent):
        stack[-2] = Slice1Op(stack[-2], stack[-1])
        stack.pop().dec()

    def _SLICE_2(self, cmd, prevcmd, nextcmd, stack, curIndent):
        stack[-2] = Slice2Op(stack[-2], stack[-1])
        stack.pop().dec()

    def _SLICE_3(self, cmd, prevcmd, nextcmd, stack, curIndent):
        stack[-3] = Slice3Op(stack[-3], stack[-2], stack[-1])
        stack.pop().dec()
        stack.pop().dec()

    def _STORE_SLICE(self, cmd, prevcmd, nextcmd, stack, curIndent):
        e = SliceOp(stack[-1])
        emptyStack = self.checkStack(stack, 2)
        r = self.STORE(e, stack[-2], curIndent, emptyStack)
        stack.pop().dec()
        stack.pop().dec()
        return r

    def _STORE_SLICE_1(self, cmd, prevcmd, nextcmd, stack, curIndent):
        e = Slice1Op(stack[-2], stack[-1])
        r = self.STORE(e, stack[-3], curIndent, self.checkStack(stack, 3))
        stack.pop().dec()
        stack.pop().dec()
        stack.pop().dec()
        return r

    def _STORE_SLICE_2(self, cmd, prevcmd, nextcmd, stack, curIndent):
        e = Slice2Op(stack[-2], stack[-1])
        r = self.STORE(e, stack[-3], curIndent, self.checkStack(stack, 3))
        stack.pop().dec()
        stack.pop().dec()
        stack.pop().dec()
        return r

    def _STORE_SLICE_3(self, cmd, prevcmd, nextcmd, stack, curIndent):
        e = Slice3Op(stack[-3], stack[-2], stack[-1])
        r = self.STORE(e, stack[-4], curIndent, self.checkStack(stack, 4))
        stack.pop().dec()
        stack.pop().dec()
        stack.pop().dec()
        stack.pop().dec()
        return r

    def _DELETE_SLICE(self, cmd, prevcmd, nextcmd, stack, curIndent):
        r = ind(curIndent) + 'del ' + str(SliceOp(stack[-1])) + '\n'
        stack.pop().dec()
        return r

    def _DELETE_SLICE_1(self, cmd, prevcmd, nextcmd, stack, curIndent):
        r = ind(curIndent) + 'del ' + \
            str(Slice1Op(stack[-2], stack[-1])) + '\n'
        stack.pop().dec()
        stack.pop().dec()
        return r

    def _DELETE_SLICE_2(self, cmd, prevcmd, nextcmd, stack, curIndent):
        r = ind(curIndent) + 'del ' + \
            str(Slice2Op(stack[-2], stack[-1])) + '\n'
        stack.pop().dec()
        stack.pop().dec()
        return r

    def _DELETE_SLICE_3(self, cmd, prevcmd, nextcmd, stack, curIndent):
        r = ind(curIndent) + 'del ' + \
            str(Slice3Op(stack[-3], stack[-2], stack[-1])) + '\n'
        stack.pop().dec()
        stack.pop().dec()
        stack.pop().dec()
        return r

    def _STORE_MAP(self, cmd, prevcmd, nextcmd, stack, curIndent):
        stack[-3].addPair(stack[-1], stack[-2])
        stack.pop().dec()
        stack.pop().dec()

    def _INPLACE_ADD(self, cmd, prevcmd, nextcmd, stack, curIndent):
        stack[-2] = InplaceAdditionOp(stack[-2], stack[-1])
        stack.pop().dec()

    def _INPLACE_SUBTRACT(self, cmd, prevcmd, nextcmd, stack, curIndent):
        stack[-2] = InplaceSubtractionOp(stack[-2], stack[-1])
        stack.pop().dec()

    def _INPLACE_MULTIPLY(self, cmd, prevcmd, nextcmd, stack, curIndent):
        stack[-2] = InplaceMultiplicationOp(stack[-2], stack[-1])
        stack.pop().dec()

    def _INPLACE_DIVIDE(self, cmd, prevcmd, nextcmd, stack, curIndent):
        stack[-2] = InplaceDivisionOp(stack[-2], stack[-1])
        stack.pop().dec()

    def _INPLACE_MODULO(self, cmd, prevcmd, nextcmd, stack, curIndent):
        stack[-2] = InplaceRemainderOp(stack[-2], stack[-1])
        stack.pop().dec()

    def _STORE_SUBSCR(self, cmd, prevcmd, nextcmd, stack, curIndent):
        r = ''
        if isinstance(stack[-2], NewHash):
            stack[-2].addPair(stack[-1], stack[-3])
            #stack[-2].value[stack[-1]] = stack[-3]
            #stack[-2].order.append(stack[-1])
        else:
            e = SubscriptionOp(stack[-2], stack[-1])
            emptyStack = self.checkStack(stack, 3)
            r += self.STORE(e, stack[-3], curIndent, emptyStack)
        stack.pop().dec()
        stack.pop().dec()
        stack.pop().dec()
        return r

    def _DELETE_SUBSCR(self, cmd, prevcmd, nextcmd, stack, curIndent):
        r = ind(curIndent) + 'del ' + \
            str(SubscriptionOp(stack[-2], stack[-1])) + '\n'
        stack.pop().dec()
        stack.pop().dec()
        return r

    def _BINARY_LSHIFT(self, cmd, prevcmd, nextcmd, stack, curIndent):
        stack[-2] = LShiftOp(stack[-2], stack[-1])
        stack.pop().dec()

    def _BINARY_RSHIFT(self, cmd, prevcmd, nextcmd, stack, curIndent):
        stack[-2] = RShiftOp(stack[-2], stack[-1])
        stack.pop().dec()

    def _BINARY_AND(self, cmd, prevcmd, nextcmd, stack, curIndent):
        stack[-2] = BitwiseANDOp(stack[-2], stack[-1])
        stack.pop().dec()

    def _BINARY_XOR(self, cmd, prevcmd, nextcmd, stack, curIndent):
        stack[-2] = BitwiseXOROp(stack[-2], stack[-1])
        stack.pop().dec()

    def _BINARY_OR(self, cmd, prevcmd, nextcmd, stack, curIndent):
        stack[-2] = BitwiseOROp(stack[-2], stack[-1])
        stack.pop().dec()

    def _INPLACE_POWER(self, cmd, prevcmd, nextcmd, stack, curIndent):
        stack[-2] = InplaceExponentiationOp(stack[-2], stack[-1])
        stack.pop().dec()

    def _GET_ITER(self, cmd, prevcmd, nextcmd, stack, curIndent):
        stack[-1] = Iterator(stack[-1])

    def _PRINT_EXPR(self, cmd, prevcmd, nextcmd, stack, curIndent):
        # TODO: PRINT_EXPR in non-interactive mode??
        pass

    def _PRINT_ITEM(self, cmd, prevcmd, nextcmd, stack, curIndent):
        r = ''
        if nextcmd is not None and nextcmd.mnemonics == 'PRINT_NEWLINE':
            r += ind(curIndent) + 'print ' + str(stack[-1]) + '\n'
        else:
            r += ind(curIndent) + 'print ' + str(stack[-1]) + ',\n'
        stack.pop().dec()
        return r

    def _PRINT_NEWLINE(self, cmd, prevcmd, nextcmd, stack, curIndent):
        r = ''
        if prevcmd is None or prevcmd.mnemonics != 'PRINT_ITEM':
            r += ind(curIndent) + 'print\n'
        return r

    def _PRINT_ITEM_TO(self, cmd, prevcmd, nextcmd, stack, curIndent):
        r = ''
        if nextcmd is not None and nextcmd.mnemonics == 'PRINT_NEWLINE_TO':
            r += ind(curIndent) + 'print >> ' + \
                 str(stack[-1]) + ', ' + str(stack[-2]) + '\n'
        else:
            r += ind(curIndent) + 'print >> ' + \
                 str(stack[-1]) + ', ' + str(stack[-2]) + ',\n'
        stack.pop().dec()
        stack.pop().dec()
        return r

    def _PRINT_NEWLINE_TO(self, cmd, prevcmd, nextcmd, stack, curIndent):
        r = ''
        if prevcmd is None or prevcmd.mnemonics != 'PRINT_ITEM_TO':
            r += ind(curIndent) + 'print >> ' + str(stack[-1]) + '\n'
        stack.pop().dec()
        return r

    def _INPLACE_LSHIFT(self, cmd, prevcmd, nextcmd, stack, curIndent):
        stack[-2] = InplaceLShiftOp(stack[-2], stack[-1])
        stack.pop().dec()

    def _INPLACE_RSHIFT(self, cmd, prevcmd, nextcmd, stack, curIndent):
        stack[-2] = InplaceRShiftOp(stack[-2], stack[-1])
        stack.pop().dec()

    def _INPLACE_AND(self, cmd, prevcmd, nextcmd, stack, curIndent):
        stack[-2] = InplaceBitwiseANDOp(stack[-2], stack[-1])
        stack.pop().dec()

    def _INPLACE_XOR(self, cmd, prevcmd, nextcmd, stack, curIndent):
        stack[-2] = InplaceBitwiseXOROp(stack[-2], stack[-1])
        stack.pop().dec()

    def _INPLACE_OR(self, cmd, prevcmd, nextcmd, stack, curIndent):
        stack[-2] = InplaceBitwiseOROp(stack[-2], stack[-1])
        stack.pop().dec()

    def _BREAK_LOOP(self, cmd, prevcmd, nextcmd, stack, curIndent):
        # TODO: recheck BREAK_LOOP
        return ind(curIndent) + 'break\n'

    def _WITH_CLEANUP(self, cmd, prevcmd, nextcmd, stack, curIndent):
        # TODO: WITH_CLEANUP
        pass

    def _LOAD_LOCALS(self, cmd, prevcmd, nextcmd, stack, curIndent):
        stack.append(DummyLocals())

    def _RETURN_VALUE(self, cmd, prevcmd, nextcmd, stack, curIndent):
        r = ''
        try:
            o = stack.pop()
        except IndexError, err:
            print "XXXX: pop from empty stack caught, returning: ",r
            return r
        o.dec()
        noneInNames = False
        for x in self.co.names.value:
            if x.value == 'None':
                noneInNames = True
                break
        if self.co.name.value != '<module>' and \
           not isinstance(o, DummyLocals) and \
           (not isinstance(o, Constant) or
            o.value is not None or noneInNames):
                r += ind(curIndent) + 'return ' + str(o) + '\n'
        return r

    def _IMPORT_STAR(self, cmd, prevcmd, nextcmd, stack, curIndent):
        r = ind(curIndent) + 'from ' + stack[-1].module + ' import *\n'
        stack.pop().dec()
        return r

    def _EXEC_STMT(self, cmd, prevcmd, nextcmd, stack, curIndent):
        r = ''
        if stack[-2].value is None:
            r += ind(curIndent) + 'exec ' + str(stack[-3]) + '\n'
        # TODO: validate stack[-2] == stack[-1]
        elif stack[-2] == stack[-1]:
            r += ind(curIndent) + 'exec ' + str(stack[-3]) + \
                 ' in ' + str(stack[-2]) + '\n'
        else:
            r += ind(curIndent) + 'exec ' + str(stack[-3]) + \
                 ' in ' + str(stack[-2]) + ', ' + str(stack[-1]) + '\n'
        stack.pop().dec()
        stack.pop().dec()
        stack.pop().dec()
        return r

    def _YIELD_VALUE(self, cmd, prevcmd, nextcmd, stack, curIndent):
        # TODO: check weather POP_TOP always follows YIELD_VALUE
        r = ind(curIndent) + 'yield ' + str(stack[-1]) + '\n'
        stack[-1] = YieldedValue(stack[-1])
        return r

    def _POP_BLOCK(self, cmd, prevcmd, nextcmd, stack, curIndent):
        # TODO: POP_BLOCK
        pass

    def _END_FINALLY(self, cmd, prevcmd, nextcmd, stack, curIndent):
        # TODO: END_FINALLY
        pass

    def _BUILD_CLASS(self, cmd, prevcmd, nextcmd, stack, curIndent):
        methods = stack.pop()
        methods.dec()
        baseclasses = stack.pop()
        baseclasses.dec()
        classname = stack.pop()
        classname.dec()
        stack.append(NewClass(classname, baseclasses, methods))

    def _STORE_NAME(self, cmd, prevcmd, nextcmd, stack, curIndent):
        
        lvalue = self.co.names.value[cmd.argument].value
        emptyStack = self.checkStack(stack, 1)
        r = self.STORE(lvalue, stack[-1], curIndent, emptyStack)
        stack.pop().dec()
        return r

    def _DELETE_NAME(self, cmd, prevcmd, nextcmd, stack, curIndent):
        r = ind(curIndent) + 'del ' + \
            self.co.names.value[cmd.argument].value.__str__() + '\n'
        return r

    def _UNPACK_SEQUENCE(self, cmd, prevcmd, nextcmd, stack, curIndent):
        # TODO: UNPACK_SEQUENCE
        pass

    def _FOR_ITER(self, cmd, prevcmd, nextcmd, stack, curIndent):
        # TODO: recheck FOR_ITER
        pass

    def _STORE_ATTR(self, cmd, prevcmd, nextcmd, stack, curIndent):
        # TODO: recheck that Import check is unnecessary
        # if stack[-1].__class__.__name__ != 'Import':
        v = Variable(self.co.names.value[cmd.argument].value)
        e = AttributeOp(stack[-1], v)
        r = self.STORE(e, stack[-2], curIndent, self.checkStack(stack, 2))
        stack.pop().dec()
        stack.pop().dec()
        return r

    def _DELETE_ATTR(self, cmd, prevcmd, nextcmd, stack, curIndent):
        v = Variable(self.co.names.value[cmd.argument].value)
        stack[-1] = AttributeOp(stack[-1], v)
        r = ind(curIndent) + 'del ' + str(stack[-1]) + '\n'
        stack.pop().dec()
        return r

    def _STORE_GLOBAL(self, cmd, prevcmd, nextcmd, stack, curIndent):
        # TODO: STORE_GLOBAL
        pass

    def _DELETE_GLOBAL(self, cmd, prevcmd, nextcmd, stack, curIndent):
        # TODO: DELETE_GLOBAL
        pass

    def _DUP_TOPX(self, cmd, prevcmd, nextcmd, stack, curIndent):
        # TODO: DUP_TOPX
        if cmd.argument > 0:
            stack.extend(stack[-cmd.argument:])
        for x in stack[-cmd.argument:]:
            x.inc()

    def _LOAD_CONST(self, cmd, prevcmd, nextcmd, stack, curIndent):
        #print self.co
##        print "Call num %d"%(self.richy_count)
##        print "LEN %d"%len(self.co.consts.value)
##        print "ARG value: ",cmd.argument
##        print "CMD",cmd
        o = self.co.consts.value[cmd.argument]
##        try:
##            print "Value: %s"%o.value
##        except:
##            print "Value obj: ",o
##        try:
##            print "Value: %s"%o.value.value
##        except:
##            pass
            
        self.richy_count += 1
        if isinstance(o, parse.pyCode):
            stack.append(RawCO(o))
        else:
            o = o.value
            # TODO: if list... etc...
            if o.__class__ is tuple:
                o = tuple(z.value for z in o)
            stack.append(Constant(o))

    def _LOAD_NAME(self, cmd, prevcmd, nextcmd, stack, curIndent):
        stack.append(Variable(self.co.names.value[cmd.argument].value))

    def _BUILD_TUPLE(self, cmd, prevcmd, nextcmd, stack, curIndent):
        lst = []
        for z in range(cmd.argument):
            o = stack.pop()
            o.dec()
            lst.insert(0, o)
        stack.append(NewTuple(tuple(lst)))

    def _BUILD_LIST(self, cmd, prevcmd, nextcmd, stack, curIndent):
        lst = []
        for z in range(cmd.argument):
            o = stack.pop()
            o.dec()
            lst.insert(0, o)
        stack.append(NewList(lst))

    def _BUILD_MAP(self, cmd, prevcmd, nextcmd, stack, curIndent):
        # TODO: BUILD_MAP strange order!!
        stack.append(NewHash())

    def _LOAD_ATTR(self, cmd, prevcmd, nextcmd, stack, curIndent):
        if not isinstance(stack[-1], Import):
            v = Variable(self.co.names.value[cmd.argument].value)
            stack[-1] = AttributeOp(stack[-1], v)

    def _COMPARE_OP(self, cmd, prevcmd, nextcmd, stack, curIndent):
        op = cmp_op[cmd.argument]
        # stack[-2] = CompareOp(op, str(stack[-2]), str(stack[-1]))
        stack[-2] = CompareOp(op, stack[-2], stack[-1])
        stack.pop().dec()

    def _IMPORT_NAME(self, cmd, prevcmd, nextcmd, stack, curIndent):
        names = stack.pop()
        level = stack.pop()
        names.dec()
        level.dec()
        value = self.co.names.value[cmd.argument].value
        stack.append(Import(value, names, level))

    def _IMPORT_FROM(self, cmd, prevcmd, nextcmd, stack, curIndent):
        importobj = stack[-1]
        value = self.co.names.value[cmd.argument].value
        stack.append(ImportFrom(importobj, value))

    def _JUMP_FORWARD(self, cmd, prevcmd, nextcmd, stack, curIndent):
        # TODO: JUMP_FORWARD
        pass

    def _JUMP_IF_FALSE(self, cmd, prevcmd, nextcmd, stack, curIndent):
        # TODO: JUMP_IF_FALSE
        return ind(curIndent) + str(stack[-1]) + '\n'

    def _JUMP_IF_TRUE(self, cmd, prevcmd, nextcmd, stack, curIndent):
        return ind(curIndent) + str(stack[-1]) + '\n'

    def _JUMP_ABSOLUTE(self, cmd, prevcmd, nextcmd, stack, curIndent):
        # TODO: JUMP_ABSOLUTE
        pass

    def _LOAD_GLOBAL(self, cmd, prevcmd, nextcmd, stack, curIndent):
        # TODO: LOAD_GLOBAL
        stack.append(Variable(self.co.names.value[cmd.argument].value))

    def _CONTINUE_LOOP(self, cmd, prevcmd, nextcmd, stack, curIndent):
        return ind(curIndent) + 'continue\n'

    def _SETUP_LOOP(self, cmd, prevcmd, nextcmd, stack, curIndent):
        # TODO: SETUP_LOOP
        pass

    def _SETUP_EXCEPT(self, cmd, prevcmd, nextcmd, stack, curIndent):
        stack.extend((DummyEx1(), DummyEx2(), DummyEx3()))

    def _SETUP_FINALLY(self, cmd, prevcmd, nextcmd, stack, curIndent):
        # TODO: SETUP_FINALLY
        pass

    def _LOAD_FAST(self, cmd, prevcmd, nextcmd, stack, curIndent):
        stack.append(Variable(self.co.varnames.value[cmd.argument].value))

    def _STORE_FAST(self, cmd, prevcmd, nextcmd, stack, curIndent):
        
        value = self.co.varnames.value[cmd.argument].value

        try:
            r = self.STORE(value, stack[-1], curIndent, self.checkStack(stack, 1))
            stack.pop().dec()        
        except IndexError:
            r=""
        
        return r

    def _DELETE_FAST(self, cmd, prevcmd, nextcmd, stack, curIndent):
        # TODO: recheck __str__ or __repr__??
        value = self.co.varnames.value[cmd.argument].value
        r = ind(curIndent) + 'del ' + str(value) + '\n'
        return r

    def _RAISE_VARARGS(self, cmd, prevcmd, nextcmd, stack, curIndent):
        r = ''
        if cmd.argument == 0:
            r += 'raise\n'
        else:
            r += 'raise ' + \
                 ', '.join(str(x) for x in stack[-cmd.argument:]) + '\n'
        for _ in xrange(cmd.argument):
            stack.pop().dec()
        return r

    def _CALL_FUNCTION(self, cmd, prevcmd, nextcmd, stack, curIndent):
       
        positional = cmd.argument & 0xFF
        keyword = (cmd.argument >> 8) & 0xFF
        functionParams = []
        for index in range(keyword):
            paramValue = str(stack[-1]) # o.__repr__()
            paramKey = stack[-2].__str__() # o.__str__()
            functionParams.insert(0, paramKey + '=' + paramValue)
            stack.pop().dec()
            stack.pop().dec()
        for index in range(positional):
            o = stack.pop()
            o.dec()
            ##XXX Rich
            try:
                functionParams.insert(0, str(o)) # o.__repr__())
            except Exception, err:
                print "+",dir(o.value)
                print "=",o.value.str()
                #raw_input("XXX: _CALL_FUNCTION Error: %s"%(err))
        o = stack.pop()
        o.dec()
        if o.__class__ is NewFunction:
            functionName = o.value.name.value
        else:
            functionName = str(o) # o.__repr__()
        stack.append(CallOp(functionName, functionParams))

    def _MAKE_FUNCTION(self, cmd, prevcmd, nextcmd, stack, curIndent):
        f_co = stack.pop()
        f_co.dec()
        if f_co.value.name.value == '<lambda>':
            nf = NewLambda(f_co.value)
        else:
            nf = NewFunction(f_co.value)
        for index in range(cmd.argument):
            o = stack.pop()
            o.dec()
            nf.addDefParam(o)
        stack.append(nf)

    def _BUILD_SLICE(self, cmd, prevcmd, nextcmd, stack, curIndent):
        if cmd.argument == 2:
            stack[-2] = Slice3Op(stack[-2], stack[-1])
            stack.pop().dec()
        elif cmd.argument == 3:
            stack[-3] = BigSliceOp(stack[-3], stack[-2], stack[-1])
            stack.pop().dec()
            stack.pop().dec()

    def _MAKE_CLOSURE(self, cmd, prevcmd, nextcmd, stack, curIndent):
        # TODO: test MAKE_CLOSURE, LOAD_DEREF, STORE_DEREF, LOAD_CLOSURE
        f_co = stack.pop()
        f_co.dec()
        for _ in xrange(len(f_co.value.freevars.value)):
            try:
                #FixMe
                stack.pop().dec()
            except:
                print "XXX: make closure bug"
                break
        if f_co.value.name.value == '<lambda>':
            nf = NewLambda(f_co.value)
        else:
            nf = NewFunction(f_co.value)
        for index in range(cmd.argument):
            o = stack.pop()
            o.dec()
            nf.defParams.append(o)
        stack.append(nf)

    def _LOAD_CLOSURE(self, cmd, prevcmd, nextcmd, stack, curIndent):
        if cmd.argument < len(self.co.cellvars.value):
            stack.append(Variable(self.co.cellvars.value[cmd.argument].value))
        else:
            index = cmd.argument - len(self.co.cellvars.value)
            value = self.co.freevars.value[index].value
            stack.append(Variable(value))

    def _LOAD_DEREF(self, cmd, prevcmd, nextcmd, stack, curIndent):
        if cmd.argument < len(self.co.cellvars.value):
            stack.append(Variable(self.co.cellvars.value[cmd.argument].value))
        else:
            index = cmd.argument - len(self.co.cellvars.value)
            value = self.co.freevars.value[index].value
            stack.append(Variable(value))

    def _STORE_DEREF(self, cmd, prevcmd, nextcmd, stack, curIndent):
        r = ''
        
        if cmd.argument < len(self.co.cellvars.value):
            value = self.co.cellvars.value[cmd.argument].value
            emptyStack = self.checkStack(stack, 1)
            r += self.STORE(value, stack[-1], curIndent, emptyStack)
        else:
            index = cmd.argument - len(self.co.cellvars.value)
            value = self.co.freevars.value[index].value
            emptyStack = self.checkStack(stack, 1)
            r += self.STORE(value, stack[-1], curIndent, emptyStack)
        stack.pop().dec()
        return r

    def _CALL_FUNCTION_VAR(self, cmd, prevcmd, nextcmd, stack, curIndent):
        # TODO: remove copypaste from CALL_FUNCTION*
        star = str(stack[-1]) #__repr__()
        stack.pop().dec()
        positional = cmd.argument & 0xFF
        keyword = (cmd.argument >> 8) & 0xFF
        functionParams = []
        for index in range(keyword):
            paramValue = str(stack[-1]) # __repr__()
            paramKey = stack[-2].__strnq__() # __str__()
            functionParams.insert(0, paramKey + '=' + paramValue)
            stack.pop().dec()
            stack.pop().dec()
        for index in range(positional):
            functionParams.insert(0, str(stack[-1])) # __repr__()
            stack.pop().dec()
        o = stack.pop()
        o.dec()
        if o.__class__ is NewFunction:
            functionName = o.value.name.value
        else:
            functionName = str(o) # __repr__()
        functionParams.append('*' + star)
        stack.append(CallOp(functionName, functionParams))

    def _CALL_FUNCTION_KW(self, cmd, prevcmd, nextcmd, stack, curIndent):
        # TODO: remove copypaste from CALL_FUNCTION*
        starstar = str(stack[-1]) # __repr__()
        stack.pop().dec()
        positional = cmd.argument & 0xFF
        keyword = (cmd.argument >> 8) & 0xFF
        functionParams = []
        for index in range(keyword):
            paramValue = str(stack[-1]) # __repr__()
            paramKey = stack[-2].__strnq__() # __str__()
            functionParams.insert(0, paramKey + '=' + paramValue)
            stack.pop().dec()
            stack.pop().dec()
        for index in range(positional):
            functionParams.insert(0, str(stack[-1])) # __repr__()
            stack.pop().dec()
        o = stack.pop()
        o.dec()
        if o.__class__ is NewFunction:
            functionName = o.value.name.value
        else:
            functionName = str(o) # __repr__()
        functionParams.append('**' + starstar)
        stack.append(CallOp(functionName, functionParams))

    def _CALL_FUNCTION_VAR_KW(self, cmd, prevcmd, nextcmd,
                              stack, curIndent):
        # TODO: remove copypaste from CALL_FUNCTION*
        starstar = str(stack[-1]) # __repr__()
        star = str(stack[-2])  # __repr__()
        stack.pop().dec()
        stack.pop().dec()
        positional = cmd.argument & 0xFF
        keyword = (cmd.argument >> 8) & 0xFF
        functionParams = []
        for index in range(keyword):
            paramValue = str(stack[-1]) # __repr__()
            paramKey = stack[-2].__strnq__() # __str__()
            functionParams.insert(0, paramKey + '=' + paramValue)
            stack.pop().dec()
            stack.pop().dec()
        for index in range(positional):
            functionParams.insert(0, str(stack[-1])) # __str__()
            stack.pop().dec()
        o = stack.pop()
        o.dec()
        if o.__class__ is NewFunction:
            functionName = o.value.name.value
        else:
            functionName = str(o) # __repr__()
        functionParams.append('*' + star)
        functionParams.append('**' + starstar)
        stack.append(CallOp(functionName, functionParams))

    def _EXTENDED_ARG(self, cmd, prevcmd, nextcmd, stack, curIndent):
        # TODO: EXTENDED_ARG
        pass

    def codeDecompile(self, offset=0, length=0, startIndent=0,
                      showStack=False, stack=[], mode='plain'):
        '''
        Decompiles current code object.

        @param offset: start offset in co_code.
        @param length: length of the co_code substring to decompile.
        @param startIndent: initial indent for the generated source code.
        @param showStack: report current stack state after each command.
        @param stack: initial stack state.
        @param mode: decompilation mode ('plain' or 'conditional').

        '''
        callHash = {
            'STOP_CODE' : self._STOP_CODE,
            'POP_TOP' : self._POP_TOP,
            'ROT_TWO' : self._ROT_TWO,
            'ROT_THREE' : self._ROT_THREE,
            'DUP_TOP' : self._DUP_TOP,
            'ROT_FOUR' : self._ROT_FOUR,
            'NOP' : self._NOP,
            'UNARY_POSITIVE' : self._UNARY_POSITIVE,
            'UNARY_NEGATIVE' : self._UNARY_NEGATIVE,
            'UNARY_NOT' : self._UNARY_NOT,
            'UNARY_CONVERT' : self._UNARY_CONVERT,
            'UNARY_INVERT' : self._UNARY_INVERT,
            'LIST_APPEND' : self._LIST_APPEND,
            'BINARY_POWER' : self._BINARY_POWER,
            'BINARY_MULTIPLY' : self._BINARY_MULTIPLY,
            'BINARY_DIVIDE' : self._BINARY_DIVIDE,
            'BINARY_MODULO' : self._BINARY_MODULO,
            'BINARY_ADD' : self._BINARY_ADD,
            'BINARY_SUBTRACT' : self._BINARY_SUBTRACT,
            'BINARY_SUBSCR' : self._BINARY_SUBSCR,
            'BINARY_FLOOR_DIVIDE' : self._BINARY_FLOOR_DIVIDE,
            'BINARY_TRUE_DIVIDE' : self._BINARY_TRUE_DIVIDE,
            'INPLACE_FLOOR_DIVIDE' : self._INPLACE_FLOOR_DIVIDE,
            'INPLACE_TRUE_DIVIDE' : self._INPLACE_TRUE_DIVIDE,
            'SLICE' : self._SLICE,
            'SLICE+1' : self._SLICE_1,
            'SLICE+2' : self._SLICE_2,
            'SLICE+3' : self._SLICE_3,
            'STORE_SLICE' : self._STORE_SLICE,
            'STORE_SLICE+1' : self._STORE_SLICE_1,
            'STORE_SLICE+2' : self._STORE_SLICE_2,
            'STORE_SLICE+3' : self._STORE_SLICE_3,
            'DELETE_SLICE' : self._DELETE_SLICE,
            'DELETE_SLICE+1' : self._DELETE_SLICE_1,
            'DELETE_SLICE+2' : self._DELETE_SLICE_2,
            'DELETE_SLICE+3' : self._DELETE_SLICE_3,
            'STORE_MAP' : self._STORE_MAP,
            'INPLACE_ADD' : self._INPLACE_ADD,
            'INPLACE_SUBTRACT' : self._INPLACE_SUBTRACT,
            'INPLACE_MULTIPLY' : self._INPLACE_MULTIPLY,
            'INPLACE_DIVIDE' : self._INPLACE_DIVIDE,
            'INPLACE_MODULO' : self._INPLACE_MODULO,
            'STORE_SUBSCR' : self._STORE_SUBSCR,
            'DELETE_SUBSCR' : self._DELETE_SUBSCR,
            'BINARY_LSHIFT' : self._BINARY_LSHIFT,
            'BINARY_RSHIFT' : self._BINARY_RSHIFT,
            'BINARY_AND' : self._BINARY_AND,
            'BINARY_XOR' : self._BINARY_XOR,
            'BINARY_OR' : self._BINARY_OR,
            'INPLACE_POWER' : self._INPLACE_POWER,
            'GET_ITER' : self._GET_ITER,
            'PRINT_EXPR' : self._PRINT_EXPR,
            'PRINT_ITEM' : self._PRINT_ITEM,
            'PRINT_NEWLINE' : self._PRINT_NEWLINE,
            'PRINT_ITEM_TO' : self._PRINT_ITEM_TO,
            'PRINT_NEWLINE_TO' : self._PRINT_NEWLINE_TO,
            'INPLACE_LSHIFT' : self._INPLACE_LSHIFT,
            'INPLACE_RSHIFT' : self._INPLACE_RSHIFT,
            'INPLACE_AND' : self._INPLACE_AND,
            'INPLACE_XOR' : self._INPLACE_XOR,
            'INPLACE_OR' : self._INPLACE_OR,
            'BREAK_LOOP' : self._BREAK_LOOP,
            'WITH_CLEANUP' : self._WITH_CLEANUP,
            'LOAD_LOCALS' : self._LOAD_LOCALS,
            'RETURN_VALUE' : self._RETURN_VALUE,
            'IMPORT_STAR' : self._IMPORT_STAR,
            'EXEC_STMT' : self._EXEC_STMT,
            'YIELD_VALUE' : self._YIELD_VALUE,
            'POP_BLOCK' : self._POP_BLOCK,
            'END_FINALLY' : self._END_FINALLY,
            'BUILD_CLASS' : self._BUILD_CLASS,
            'STORE_NAME' : self._STORE_NAME,
            'DELETE_NAME' : self._DELETE_NAME,
            'UNPACK_SEQUENCE' : self._UNPACK_SEQUENCE,
            'FOR_ITER' : self._FOR_ITER,
            'STORE_ATTR' : self._STORE_ATTR,
            'DELETE_ATTR' : self._DELETE_ATTR,
            'STORE_GLOBAL' : self._STORE_GLOBAL,
            'DELETE_GLOBAL' : self._DELETE_GLOBAL,
            'DUP_TOPX' : self._DUP_TOPX,
            'LOAD_CONST' : self._LOAD_CONST,
            'LOAD_NAME' : self._LOAD_NAME,
            'BUILD_TUPLE' : self._BUILD_TUPLE,
            'BUILD_LIST' : self._BUILD_LIST,
            'BUILD_MAP' : self._BUILD_MAP,
            'LOAD_ATTR' : self._LOAD_ATTR,
            'COMPARE_OP' : self._COMPARE_OP,
            'IMPORT_NAME' : self._IMPORT_NAME,
            'IMPORT_FROM' : self._IMPORT_FROM,
            'JUMP_FORWARD' : self._JUMP_FORWARD,
            'JUMP_IF_FALSE' : self._JUMP_IF_FALSE,
            'JUMP_IF_TRUE' : self._JUMP_IF_TRUE,
            'JUMP_ABSOLUTE' : self._JUMP_ABSOLUTE,
            'LOAD_GLOBAL' : self._LOAD_GLOBAL,
            'CONTINUE_LOOP' : self._CONTINUE_LOOP,
            'SETUP_LOOP' : self._SETUP_LOOP,
            'SETUP_EXCEPT' : self._SETUP_EXCEPT,
            'SETUP_FINALLY' : self._SETUP_FINALLY,
            'LOAD_FAST' : self._LOAD_FAST,
            'STORE_FAST' : self._STORE_FAST,
            'DELETE_FAST' : self._DELETE_FAST,
            'RAISE_VARARGS' : self._RAISE_VARARGS,
            'CALL_FUNCTION' : self._CALL_FUNCTION,
            'MAKE_FUNCTION' : self._MAKE_FUNCTION,
            'BUILD_SLICE' : self._BUILD_SLICE,
            'MAKE_CLOSURE' : self._MAKE_CLOSURE,
            'LOAD_CLOSURE' : self._LOAD_CLOSURE,
            'LOAD_DEREF' : self._LOAD_DEREF,
            'STORE_DEREF' : self._STORE_DEREF,
            'CALL_FUNCTION_VAR' : self._CALL_FUNCTION_VAR,
            'CALL_FUNCTION_KW' : self._CALL_FUNCTION_KW,
            'CALL_FUNCTION_VAR_KW' : self._CALL_FUNCTION_VAR_KW,
            'EXTENDED_ARG' : self._EXTENDED_ARG
        }

        commands = self.disassembler.getCommands(offset, length).cmdList
        r = ''
        stackOfStacks = []
        curIndent = startIndent
        indentStack = []
        jumps = []
        cmdlen = len(commands)

        for index in xrange(cmdlen):
            try:
                cmd = commands[index]
                prevcmd = None
                nextcmd = None
                if index != cmdlen - 1: nextcmd = commands[index + 1]
                if index != 0: prevcmd = commands[index - 1]

                if cmd.mnemonics is not None:
                    # TODO: should be hash switch!
                    if mode == 'conditional' and \
                       cmd.mnemonics in ('JUMP_IF_TRUE', 'JUMP_IF_FALSE'):
                        return (r, stack[-1])
                    else:
                        
                        func = callHash[cmd.mnemonics]
                        ##XXX Rich 
                        try:
                            res = func(cmd, prevcmd, nextcmd,
                                       stack, curIndent)
                        except Exception, err:
                            print "XXX: %s"%err
                            #import traceback
                            #traceback.print_exc()
                            #raw_input()
                            res = None
                        ##XXX
                            
                        if res is not None:
                            r += res

                    if showStack:
                        print '---> stack: '
                        for x in stack:
                            print '     ' + str(x)
            except:
                raise
                print r
                r = ''
                print '------'
                print '***', sys.exc_info()
                print >> sys.stderr, \
                    '>>> Decompilation broken:\n' \
                    '>>> exception: ' + str(sys.exc_info()[1]) + \
                    '>>> stack trace:\n' + \
                    traceback.print_tb(sys.exc_info()[2]) + \
                    '>>> decompilation state info:\n' \
                    'co.name = %s\n' \
                    'lastoffset = %.8X\n' \
                    'lastcommand = %s\n' \
                    'lastargument = %s\n' % (self.co.name.value, cmd.offset,
                                             cmd.mnemonics, cmd.argument)
                print >> sys.stderr, '>>> decompilation stack info:\n'
                sys.exit(-1)
        # TODO: check and cleanup self.postponedStores
        if stack:
            dbgprint('>>> Warning: Decompilation finished with ' \
                     'nonempty stack:')
            for x in stack:
                dbgprint('\t' + str(x))
            dbgprint('<<<')

        if mode == 'conditional': return (r, None)
        return r

    def decompile(self, offset=0, startIndent=0):
        '''Entry point for the decompilation process.'''
        try:
            cb = self.disassembler.getAllCodeBlocks(offset)
            print "[+] All code blocks got"
            flowGraph = structure.getGraphFromCodeBlocks(cb, self.debugDraw)
            print "[+] Flow graph from code blocks got"
            flowGraph.DFADecompile(self)
            print "[+] DFA decompiled"
            flowGraph.simplifyComplexIFs()
            print "[+] Complex IF's simplified"
            flowGraph.preprocessWhileLoops()
            print "[+] WHILE loops preprocessed"
            flowGraph.simplifyAllCompound()
            print "[+] All compounds simplified"
            flowGraph.simplifyConsecutive()
            print "[+] Consecutives simplified"
            if len(flowGraph.nodes) == 1:
                r = flowGraph.nodes[flowGraph.root].code
            else:
                print "\n\n"
                print "!!!INCOMPLETE DISASSEMBLY!!!!"
                print "%d code block uncoalesced"%len(flowGraph.nodes)
                #r = '>>> Fatal error: could not structure control flow graph.'
                r=""
                ordered_nodes=flowGraph.nodes.keys()
                ordered_nodes.sort()
                for n in ordered_nodes:
                    if len(flowGraph.nodes[n].code) == 0:
                        continue
                    r += "#[NODE: %s]\n%s\n"%(n, flowGraph.nodes[n].code)
                
               
            return indentText(r, startIndent)
        except:
            traceback.print_exc()