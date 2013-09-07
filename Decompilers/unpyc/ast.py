#!/usr/bin/env python
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
This module provides classes to build ASTs on decompilation stack.

Classes are divided into two categories: Operator and Data.
Operational ones incorporate priority of the operator.

From http://docs.python.org/reference/expressions.html#summary
(From lowest to highest priority)
 0.  Lambda expression:
     lambda
 1.  Boolean OR:
     or
 2.  Boolean AND:
     and
 3.  Boolean NOT (unary):
     not X
 4.  Comparisons, including membership tests and identity tests, ... :
     in, not in, is, is not, <, <=, >, >=, <>, !=, ==
 5.  Bitwise OR:
     |
 6.  Bitwise XOR:
     ^
 7.  Bitwise AND:
     &
 8.  Shifts:
     <<, >>
 9.  Addition and subtraction:
     +, -
 10. Multiplication, division, remainder:
     *, /, %
 11. Positive, negative, bitwise NOT (unary):
     +x, -x, ~x
 12. Exponentiation:
     **
 13. Subscription, slicing, call, attribute reference:
     x[index], x[index:index], x(arguments...), x.attribute
 14. Binding or tuple display, list display, dictionary display, string conversion:
     (expressions...), [expressions...], {key:datum...}, `expressions...`

'''
import opcodes
import decompile
import disasm

class Node:
    '''Basic class for the node of AST.'''

    def __init__(self, value, children=None):
        '''
        @param value: value of the node.
        @param children: children of the node.

        '''
        self.value = value
        self.children = children
        self.counter = 1

    def inc(self):
        '''Increases the reference counter.'''

        self.counter += 1

    def dec(self):
        '''Decreases the reference counter.'''

        self.counter -= 1
        if self.counter < 0:
            raise TypeError

    def isLastCopy(self):
        '''Ensures that it is the last copy of this object.'''

        if self.counter == 0:
            return True
        return False

    def saveTree(self, filename):
        '''
        Saves the image of AST built with the current node as a root node.

        @param filename:
            filename to which to save. 'png' extension will be appended.

        '''

        import graph
        import gv
        gr = graph.digraph()
        queue = [self]
        i = 0
        h = {}
        while len(queue):
            n = queue.pop()
            h[n] = i
            gr.add_node(i, [('label', n.value)])
            if n.children is not None:
                queue.extend(n.children)
            i += 1
        queue = [self]
        while len(queue):
            n = queue.pop()
            if n.children is not None:
                for c in n.children:
                    gr.add_edge(h[n], h[c])
                    queue.append(c)
        dot = gr.write(fmt='dot')
        gvv = gv.readstring(dot)
        gv.layout(gvv, 'dot')
        gv.render(gvv, 'png', str(filename) + '.png')

class OpNode(Node):
    '''Basic class for Operator nodes.'''

    def __init__(self, value, children, priority):
        '''
        @param value: value of this node.
        @param children: children of this node.
        @param priority: operator priority.

        '''
        Node.__init__(self, value, children)
        self.priority = priority

class UnaryOp(OpNode):
    '''Unary operators basic class.'''

    def __init__(self, value, child, priority):
        '''
        @param value: value of operator (~, -, +, ...).
        @param child: child node to which operator is applied.
        @param priority: operator priority.

        '''
        OpNode.__init__(self, value, [child], priority)

    def __str__(self):
        rchild = self.children[0]
        rstr = str(rchild)
        if isinstance(rchild, OpNode) and self.priority > rchild.priority:
            rstr = '(' + rstr + ')'
        return self.value + rstr

class BinaryOp(OpNode):
    '''Binary operators basic class.'''

    def __init__(self, value, lchild, rchild, priority):
        '''
        @param value: value of operator (+, -, *, /, ...).
        @param lchild: left child node to which operator is applied.
        @param rchild: right child node to which operator is applied.
        @param priority: operator priority.

        '''
        OpNode.__init__(self, value, [lchild, rchild], priority)

    def __str__(self):
        (lchild, rchild) = self.children
        lstr = str(lchild)
        rstr = str(rchild)
        if isinstance(lchild, OpNode) and self.priority > lchild.priority:
            lstr = '(' + lstr + ')'
        if isinstance(rchild, OpNode) and self.priority > rchild.priority:
            rstr = '(' + rstr + ')'
        return lstr + ' ' + self.value + ' ' + rstr

class Iterator(UnaryOp):
    '''Used to denote result of GET_ITER.'''

    def __init__(self, child):
        UnaryOp.__init__(self, '<iter>', child, -1)

    def __str__(self):
        return str(self.children[0])

class InplaceOp(BinaryOp):
    '''Basic class for inplace operators.'''

    def __init__(self, value, lchild, rchild):
        BinaryOp.__init__(self, value + '=', lchild, rchild, -1)

class InplaceFloorDivisionOp(InplaceOp):
    def __init__(self, lchild, rchild):
        InplaceOp.__init__(self, '//', lchild, rchild)

class InplaceDivisionOp(InplaceOp):
    def __init__(self, lchild, rchild):
        InplaceOp.__init__(self, '/', lchild, rchild)

class InplaceAdditionOp(InplaceOp):
    def __init__(self, lchild, rchild):
        InplaceOp.__init__(self, '+', lchild, rchild)

class InplaceSubtractionOp(InplaceOp):
    def __init__(self, lchild, rchild):
        InplaceOp.__init__(self, '-', lchild, rchild)

class InplaceMultiplicationOp(InplaceOp):
    def __init__(self, lchild, rchild):
        InplaceOp.__init__(self, '*', lchild, rchild)

class InplaceRemainderOp(InplaceOp):
    def __init__(self, lchild, rchild):
        InplaceOp.__init__(self, '%', lchild, rchild)

class InplaceExponentiationOp(InplaceOp):
    def __init__(self, lchild, rchild):
        InplaceOp.__init__(self, '**', lchild, rchild)

class InplaceLShiftOp(InplaceOp):
    def __init__(self, lchild, rchild):
        InplaceOp.__init__(self, '<<', lchild, rchild)

class InplaceRShiftOp(InplaceOp):
    def __init__(self, lchild, rchild):
        InplaceOp.__init__(self, '>>', lchild, rchild)

class InplaceBitwiseANDOp(InplaceOp):
    def __init__(self, lchild, rchild):
        InplaceOp.__init__(self, '&', lchild, rchild)

class InplaceBitwiseXOROp(InplaceOp):
    def __init__(self, lchild, rchild):
        InplaceOp.__init__(self, '^', lchild, rchild)

class InplaceBitwiseOROp(InplaceOp):
    def __init__(self, lchild, rchild):
        InplaceOp.__init__(self, '|', lchild, rchild)

class BooleanOROp(BinaryOp):
    def __init__(self, lchild, rchild):
        BinaryOp.__init__(self, 'or', lchild, rchild, 1)

class BooleanANDOp(BinaryOp):
    def __init__(self, lchild, rchild):
        BinaryOp.__init__(self, 'and', lchild, rchild, 2)

class BooleanNOTOp(UnaryOp):
    def __init__(self, child):
        UnaryOp.__init__(self, 'not', child, 3)

    def __str__(self):
        rchild = self.children[0]
        rstr = str(rchild)
        if isinstance(rchild, OpNode) and self.priority > rchild.priority:
            return self.value + '(' + rstr + ')'
        return self.value + ' ' + rstr

class CompareOp(BinaryOp):
    def __init__(self, sign, lchild, rchild):
        BinaryOp.__init__(self, sign, lchild, rchild, 4)

class BitwiseOROp(BinaryOp):
    def __init__(self, lchild, rchild):
        BinaryOp.__init__(self, '|', lchild, rchild, 5)

class BitwiseXOROp(BinaryOp):
    def __init__(self, lchild, rchild):
        BinaryOp.__init__(self, '^', lchild, rchild, 6)

class BitwiseANDOp(BinaryOp):
    def __init__(self, lchild, rchild):
        BinaryOp.__init__(self, '&', lchild, rchild, 7)

class LShiftOp(BinaryOp):
    def __init__(self, lchild, rchild):
        BinaryOp.__init__(self, '<<', lchild, rchild, 8)

class RShiftOp(BinaryOp):
    def __init__(self, lchild, rchild):
        BinaryOp.__init__(self, '>>', lchild, rchild, 8)

class AdditionOp(BinaryOp):
    def __init__(self, lchild, rchild):
        BinaryOp.__init__(self, '+', lchild, rchild, 9)

class SubtractionOp(BinaryOp):
    def __init__(self, lchild, rchild):
        BinaryOp.__init__(self, '-', lchild, rchild, 9)

class MultiplicationOp(BinaryOp):
    def __init__(self, lchild, rchild):
        BinaryOp.__init__(self, '*', lchild, rchild, 10)

class DivisionOp(BinaryOp):
    def __init__(self, lchild, rchild):
        BinaryOp.__init__(self, '/', lchild, rchild, 10)

class FloorDivisionOp(BinaryOp):
    def __init__(self, lchild, rchild):
        BinaryOp.__init__(self, '//', lchild, rchild, 10)

class RemainderOp(BinaryOp):
    def __init__(self, lchild, rchild):
        BinaryOp.__init__(self, '%', lchild, rchild, 10)

class PositiveOp(UnaryOp):
    def __init__(self, child):
        UnaryOp.__init__(self, '+', child, 11)

class NegativeOp(UnaryOp):
    def __init__(self, child):
        UnaryOp.__init__(self, '-', child, 11)

class BitwiseNOTOp(UnaryOp):
    def __init__(self, child):
        UnaryOp.__init__(self, '~', child, 11)

class ExponentiationOp(BinaryOp):
    def __init__(self, lchild, rchild):
        BinaryOp.__init__(self, '**', lchild, rchild, 12)

class SubscriptionOp(OpNode):
    def __init__(self, lchild, rchild):
        OpNode.__init__(self, '<subscription>', [lchild, rchild], 13)

    def __str__(self):
        (lchild, rchild) = self.children
        lstr = str(lchild)
        rstr = str(rchild)
        if isinstance(lchild, OpNode) and self.priority > lchild.priority:
            lstr = '(' + lstr + ')'
        return lstr + '[' + rstr + ']'

class SliceOp(OpNode):
    def __init__(self, lchild):
        OpNode.__init__(self, '<slice>', [lchild], 13)

    def __str__(self):
        lchild = self.children[0]
        lstr = str(lchild)
        if isinstance(lchild, OpNode) and self.priority > lchild.priority:
            lstr = '(' + lstr + ')'
        return lstr + '[:]'

class Slice1Op(OpNode):
    def __init__(self, lchild, rchild):
        OpNode.__init__(self, '<slice+1>', [lchild, rchild], 13)

    def __str__(self):
        (lchild, rchild) = self.children
        lstr = str(lchild)
        rstr = str(rchild)
        if isinstance(lchild, OpNode) and self.priority > lchild.priority:
            lstr = '(' + lstr + ')'
        return lstr + '[' + rstr + ':]'

class Slice2Op(OpNode):
    def __init__(self, lchild, rchild):
        OpNode.__init__(self, '<slice+2>', [lchild, rchild], 13)

    def __str__(self):
        (lchild, rchild) = self.children
        lstr = str(lchild)
        rstr = str(rchild)
        if isinstance(lchild, OpNode) and self.priority > lchild.priority:
            lstr = '(' + lstr + ')'
        return lstr + '[:' + rstr + ']'

class Slice3Op(OpNode):
    def __init__(self, lchild, rchild1, rchild2):
        OpNode.__init__(self, '<slice+3>', [lchild, rchild1, rchild2], 13)

    def __str__(self):
        (lchild, rchild1, rchild2) = self.children
        lstr = str(lchild)
        rstr1 = str(rchild1)
        rstr2 = str(rchild2)
        if isinstance(lchild, OpNode) and self.priority > lchild.priority:
            lstr = '(' + lstr + ')'
        return lstr + '[' + rstr1 + ':' + rstr2 + ']'

class BigSliceOp(OpNode):
    def __init__(self, rchild1, rchild2, rchild3):
        OpNode.__init__(self, '<big_slice>', [rchild1, rchild2, rchild3], 13)

    def __str__(self):
        (rchild1, rchild2, rchild3) = self.children
        rstr1 = str(rchild1)
        rstr2 = str(rchild2)
        rstr3 = str(rchild3)
        if isinstance(rchild1, Constant) and rchild1.value is None:
            rstr1 = ''
        if isinstance(rchild2, Constant) and rchild2.value is None:
            rstr2 = ''
        return rstr1 + ':' + rstr2 + ':' + rstr3

class CallOp(OpNode):
    def __init__(self, lchild, rchildren):
        OpNode.__init__(self, '<call>', [lchild, rchildren], 13)

    def __str__(self):
        (lchild, rchildren) = self.children
        lstr = str(lchild)
        rstr = ', '.join(str(c) for c in rchildren)
        if isinstance(lchild, OpNode) and self.priority > lchild.priority:
            lstr = '(' + lstr + ')'
        return lstr + '(' + rstr + ')'

class AttributeOp(BinaryOp):
    def __init__(self, lchild, rchild):
        BinaryOp.__init__(self, '.', lchild, rchild, 13)

    def __str__(self):
        (lchild, rchild) = self.children
        lstr = str(lchild)
        rstr = str(rchild)
        if isinstance(lchild, OpNode) and self.priority > lchild.priority:
            lstr = '(' + lstr + ')'
        if isinstance(rchild, OpNode) and self.priority > rchild.priority:
            rstr = '(' + rstr + ')'
        return lstr + '.' + rstr

class ConvertOp(OpNode):
    def __init__(self, child):
        OpNode.__init__(self, '<convert>', [child], 14)

    def __str__(self):
        rchild = self.children[0]
        rstr = str(rchild)
        return '`' + rstr + '`'

class DataNode(Node):
    '''Basic class for data nodes.'''
    def __init__(self, value, children=None):
        Node.__init__(self, value, children)

    def __str__(self):
        return self.value

class Variable(DataNode):
    pass

class Constant(DataNode):
    def __str__(self):
        return `self.value`

    def __strnq__(self):
        return self.value

class HashPair(DataNode):
    def __init__(self, key, value):
        Node.__init__(self, '<hash_pair>', [key, value])

    def __str__(self):
        return '%s: %s' % (str(self.children[0]), str(self.children[1]))

class NewHash(DataNode):
    def __init__(self):
        DataNode.__init__(self, '<hash>', [])

    def addPair(self, key, value):
        self.children.append(HashPair(key, value))

    def __str__(self):
        return '{' + ', '.join(str(hp) for hp in self.children) + '}'

class NewList(DataNode):
    def __init__(self, children):
        DataNode.__init__(self, children, children)

    def __str__(self):
        return '[' + ', '.join(str(e) for e in self.children) + ']'

class NewTuple(DataNode):
    def __init__(self, children):
        DataNode.__init__(self, children, children)

    def __str__(self):
        if len(self.children) == 1:
            try:
                return '(' + self.children[0] + ',)'
            except:
                print "XXX",self.children
        return '(' + ', '.join(str(e) for e in self.children) + ')'

class NewFunction(DataNode):
    def __init__(self, value):
        DataNode.__init__(self, value, [])
        # children are defParams

    def addDefParam(self, param):
        self.children.append(param)

    def getParams(self):
        argc = self.value.argcount.value
        params = []
        ldp = len(self.children)
        childindex = 1
        for index in xrange(argc):
            x = self.value.varnames.value[index].value
            if argc - index <= ldp:
                x += '=' + str(self.children[ldp-childindex])
                childindex += 1
            params.append(x)
        ##XXX Rich
        try:
            if self.value.flags.value & opcodes.rflags['VARARGS']:
                params.append('*' + self.value.varnames.value[argc].value)
        except IndexError, err:
            print "xxx: vararg fail: ",err
            params.append('*'+"args")
        try:
            if self.value.flags.value & opcodes.rflags['VARKEYWORDS']:
                params.append('**' + self.value.varnames.value[argc+1].value)
        except IndexError, err:
            print "xxx: keyword fail: ",err
            params.append('**'+"kwargs")
        ##XXX /Rich
        return ', '.join(params)

class RawCO(DataNode):
    pass

class NewLambda(NewFunction):
    def __str__(self):
        od = disasm.Disassembler(self.value, optimizeJumps=True)
        # cut out 'return ' and '\n'
        x = decompile.Decompiler(od).decompile()[7:-1]
        return '(lambda ' + self.getParams() + ': ' + x + ')'

class NewClass(DataNode):
    def __init__(self, classname, baseclasses, methods):
        self.classname = classname
        self.baseclasses = baseclasses
        self.methods = methods
        DataNode.__init__(self, '<class>', [classname, baseclasses, methods])

class DummyLocals(DataNode):
    def __init__(self):
                DataNode.__init__(self, '<dummy_locals>')

class DummyEx(DataNode):
    def __init__(self, value):
                DataNode.__init__(self, value)

class DummyEx1(DummyEx):
    def __init__(self):
                DummyEx.__init__(self, '<dummy_ex1>')

class DummyEx2(DummyEx):
    def __init__(self):
                DummyEx.__init__(self, '<dummy_ex2>')

class DummyEx3(DummyEx):
    def __init__(self):
                DummyEx.__init__(self, '<dummy_ex3>')

class YieldedValue(DataNode):
    pass

class Import(DataNode):
    def __init__(self, module, names, level):
        (self.module, self.names, self.level) = (module, names, level)
        self.froms = []
        DataNode.__init__(self, '<import>', [module, level])

    def addFrom(self, name, asname):
        self.froms.append((name, asname))

class ImportFrom(DataNode):
    def __init__(self, importobj, name):
        (self.importobj, self.name) = (importobj, name)
        DataNode.__init__(self, [importobj])

if __name__ == '__main__':
    # (a * b + (a + b) * c) / a
    a = DataNode('a')
    a2 = DataNode('a')
    a3 = DataNode('a')
    b = DataNode('b')
    b2 = DataNode('b')
    c = DataNode('c')
    expr = DivisionOp(AdditionOp(MultiplicationOp(a, b),
                                 MultiplicationOp(AdditionOp(a2, b2), c)),
                      a3)
    print expr
    expr.saveTree('xxx')
