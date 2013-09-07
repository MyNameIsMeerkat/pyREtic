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
Provides constants necessary for disassembly.

Constants are the following:
    - opcodes - maps opcode with mnemonics, attribute length and
                doc-string.
    - cmp_op - maps byte representation of comparison operations with
               their string representation.
    - marshal_types - maps byte representation of data types with their
                      string representation.
    - flags - maps byte representation of flags with their string
              representation.
    - rflags - reverse of flags mapping.
    - ropcodes - reverse of opcodes mapping.

'''

opcodes = {
    ############# from opcodes.h #############

         # with no arguments
    0x00 : ['STOP_CODE', 0,
            'Indicates end-of-code to the compiler, not used by the ' \
            'interpreter. '],
    0x01 : ['POP_TOP', 0, 'Removes the top-of-stack (TOS) item.'],
    0x02 : ['ROT_TWO', 0, 'Swaps the two top-most stack items.'],
    0x03 : ['ROT_THREE', 0,
            'Lifts second and third stack item one position up, moves top ' \
            'down to position three.'],
    0x04 : ['DUP_TOP', 0, 'Duplicates the reference on top of the stack.'],
    0x05 : ['ROT_FOUR', 0, 'Lifts second, third and forth stack item one ' \
            'position up, moves top down to position four.'],
    0x09 : ['NOP', 0, 'Do nothing code. Used as a placeholder by the ' \
            'bytecode optimizer.'],

    0x0A : ['UNARY_POSITIVE', 0, 'Implements TOS = +TOS.'],
    0x0B : ['UNARY_NEGATIVE', 0, 'Implements TOS = -TOS.'],
    0x0C : ['UNARY_NOT', 0, 'Implements TOS = not TOS.'],
    0x0D : ['UNARY_CONVERT', 0, 'Implements TOS = `TOS`.'],
    0x0F : ['UNARY_INVERT', 0, 'Implements TOS = ~TOS.'],
    0x12 : ['LIST_APPEND', 0,
            'Calls list.append(TOS1, TOS). Used to implement list ' \
            'comprehensions.'],
    0x13 : ['BINARY_POWER', 0, 'Implements TOS = TOS1 ** TOS. '],
    0x14 : ['BINARY_MULTIPLY', 0, 'Implements TOS = TOS1 * TOS.'],
    0x15 : ['BINARY_DIVIDE', 0, 'Implements TOS = TOS1 / TOS when ' \
            'from __future__ import division is not in effect.'],
    0x16 : ['BINARY_MODULO', 0, 'Implements TOS = TOS1 % TOS.'],
    0x17 : ['BINARY_ADD', 0, 'Implements TOS = TOS1 + TOS.'],
    0x18 : ['BINARY_SUBTRACT', 0, 'Implements TOS = TOS1 - TOS.'],
    0x19 : ['BINARY_SUBSCR', 0, 'Implements TOS = TOS1[TOS].'],
    0x1A : ['BINARY_FLOOR_DIVIDE', 0, 'Implements TOS = TOS1 // TOS.'],
    0x1B : ['BINARY_TRUE_DIVIDE', 0,'Implements TOS = TOS1 / TOS when ' \
            'from __future__ import division is in effect.'],
    0x1C : ['INPLACE_FLOOR_DIVIDE', 0,
            'Implements in-place TOS = TOS1 // TOS.'],
    0x1D : ['INPLACE_TRUE_DIVIDE', 0,
            'Implements in-place TOS = TOS1 / TOS when ' \
            'from __future__ import division is in effect.'],

    0x1E : ['SLICE', 0, 'Implements TOS = TOS[:].'],
    0x1F : ['SLICE+1', 0, 'Implements TOS = TOS1[TOS:].'],
    0x20 : ['SLICE+2', 0, 'Implements TOS = TOS1[:TOS].'],
    0x21 : ['SLICE+3', 0, 'Implements TOS = TOS2[TOS1:TOS].'],
    0x28 : ['STORE_SLICE', 0, 'Implements TOS[:] = TOS1.'],
    0x29 : ['STORE_SLICE+1', 0, 'Implements TOS1[TOS:] = TOS2.'],
    0x2A : ['STORE_SLICE+2', 0, 'Implements TOS1[:TOS] = TOS2.'],
    0x2B : ['STORE_SLICE+3', 0, 'Implements TOS2[TOS1:TOS] = TOS3.'],
    0x32 : ['DELETE_SLICE', 0, 'Implements del TOS[:].'],
    0x33 : ['DELETE_SLICE+1', 0, 'Implements del TOS1[TOS:].'],
    0x34 : ['DELETE_SLICE+2', 0, 'Implements del TOS1[:TOS].'],
    0x35 : ['DELETE_SLICE+3', 0, 'Implements del TOS2[TOS1:TOS].'],

    0x36 : ['STORE_MAP', 0,
            'Store a key and value pair in a dictionary. Pops the key and ' \
            'value while leaving the dictionary on the stack.', '2.6.2'],

    0x37 : ['INPLACE_ADD', 0, 'Implements in-place TOS = TOS1 + TOS.'],
    0x38 : ['INPLACE_SUBTRACT', 0, 'Implements in-place TOS = TOS1 - TOS.'],
    0x39 : ['INPLACE_MULTIPLY', 0, 'Implements in-place TOS = TOS1 * TOS.'],
    0x3A : ['INPLACE_DIVIDE', 0,
            'Implements in-place TOS = TOS1 / TOS when ' \
            'from __future__ import division is not in effect.'],
    0x3B : ['INPLACE_MODULO', 0, 'Implements in-place TOS = TOS1 % TOS.'],
    0x3C : ['STORE_SUBSCR', 0, 'Implements TOS1[TOS] = TOS2.'],
    0x3D : ['DELETE_SUBSCR', 0, 'Implements del TOS1[TOS]. '],
    0x3E : ['BINARY_LSHIFT', 0, 'Implements TOS = TOS1 << TOS. '],
    0x3F : ['BINARY_RSHIFT', 0, 'Implements TOS = TOS1 >> TOS.'],
    0x40 : ['BINARY_AND', 0, 'Implements TOS = TOS1 & TOS.'],
    0x41 : ['BINARY_XOR', 0, 'Implements TOS = TOS1 ^ TOS. '],
    0x42 : ['BINARY_OR', 0, 'Implements TOS = TOS1 | TOS.'],
    0x43 : ['INPLACE_POWER', 0, 'Implements in-place TOS = TOS1 ** TOS.'],
    0x44 : ['GET_ITER', 0, 'Implements TOS = iter(TOS).'],
    0x46 : ['PRINT_EXPR', 0,
            'Implements the expression statement for the interactive mode. ' \
            'TOS is removed from the stack and printed. In non-interactive ' \
            'mode, an expression statement is terminated with POP_STACK.'],
    0x47 : ['PRINT_ITEM', 0,
            'Prints TOS to the file-like object bound to sys.stdout. There ' \
            'is one such instruction for each item in the print statement.'],
    0x48 : ['PRINT_NEWLINE', 0,
            'Prints a new line on sys.stdout. This is generated as the ' \
            'last operation of a print statement, unless the statement ' \
            'ends with a comma.'],
    0x49 : ['PRINT_ITEM_TO', 0,
            'Like PRINT_ITEM, but prints the item second from TOS to the ' \
            'file-like object at TOS. This is used by the extended print ' \
            'statement.'],
    0x4A : ['PRINT_NEWLINE_TO', 0,
            'Like PRINT_NEWLINE, but prints the new line on the file-like ' \
            'object on the TOS. This is used by the extended print ' \
            'statement.'],
    0x4B : ['INPLACE_LSHIFT', 0, 'Implements in-place TOS = TOS1 << TOS.'],
    0x4C : ['INPLACE_RSHIFT', 0, 'Implements in-place TOS = TOS1 >> TOS.'],
    0x4D : ['INPLACE_AND', 0, 'Implements in-place TOS = TOS1 & TOS.'],
    0x4E : ['INPLACE_XOR', 0, 'Implements in-place TOS = TOS1 ^ TOS.'],
    0x4F : ['INPLACE_OR', 0, 'Implements in-place TOS = TOS1 | TOS. '],
    0x50 : ['BREAK_LOOP', 0, 'Terminates a loop due to a break statement.'],
    0x51 : ['WITH_CLEANUP', 0,
            'Cleans up the stack when a with statement block exits. On top ' \
            'of the stack are 1-3 values indicating how/why the finally ' \
            'clause was entered: ' \
            '1) TOP = None ' \
            '2) (TOP, SECOND) = (WHY_{RETURN,CONTINUE}), retval ' \
            '3) TOP = WHY_*; no retval below it '\
            '4) (TOP, SECOND, THIRD) = exc_info(). '\
            'Under them is EXIT, the context manager\'s __exit__() bound ' \
            'method. In the last case, EXIT(TOP, SECOND, THIRD) is called, ' \
            'otherwise EXIT(None, None, None). EXIT is removed from the ' \
            'stack, leaving the values above it in the same order. In ' \
            'addition, if the stack represents an exception, and the ' \
            'function call returns a "true" value, this information is ' \
            '"zapped", to prevent END_FINALLY from re-raising the ' \
            'exception. (But non-local gotos should still be resumed.) ' \
            'All of the following opcodes expect arguments. An argument is ' \
            'two bytes, with the more significant byte last.'],
    0x52 : ['LOAD_LOCALS', 0,
            'Pushes a reference to the locals of the current scope on the ' \
            'stack. This is used in the code for a class definition: After ' \
            'the class body is evaluated, the locals are passed to the ' \
            'class definition.'],
    0x53 : ['RETURN_VALUE', 0,
            'Returns with TOS to the caller of the function.'],
    0x54 : ['IMPORT_STAR', 0,
            'Loads all symbols not starting with "_" directly from the ' \
            'module TOS to the local namespace. The module is popped after ' \
            'loading all names. This opcode implements ' \
            'from module import *.'],
    0x55 : ['EXEC_STMT', 0,
            'Implements exec TOS2,TOS1,TOS. The compiler fills missing ' \
            'optional parameters with None.'],
    0x56 : ['YIELD_VALUE', 0, 'Pops TOS and yields it from a generator.'],
    0x57 : ['POP_BLOCK', 0,
            'Removes one block from the block stack. Per frame, there is a ' \
            'stack of blocks, denoting nested loops, try statements, and ' \
            'such.'],
    0x58 : ['END_FINALLY', 0,
            'Terminates a finally clause. The interpreter ' \
            'recalls whether the exception has to be re-raised, or whether ' \
            'the function returns, and continues with the outer-next block.'],
    0x59 : ['BUILD_CLASS', 0,
            'Creates a new class object. TOS is the methods dictionary, ' \
            'TOS1 the tuple of the names of the base classes, and TOS2 the ' \
            'class name.'],

             # with argument
    0x5A : ['STORE_NAME', 2,
            'Implements name = TOS. /namei/ is the index of name in the ' \
            'attribute co_names of the code object. The compiler tries to ' \
            'use STORE_LOCAL or STORE_GLOBAL if possible.'],
    0x5B : ['DELETE_NAME', 2,
            'Implements del name, where /namei/ is the index into co_names ' \
            'attribute of the code object.'],
    0x5C : ['UNPACK_SEQUENCE', 2,
            'Unpacks TOS into /count/ individual values, which are put ' \
            'onto the stack right-to-left.'],
    0x5D : ['FOR_ITER', 2,
            'TOS is an iterator. Call its next() method. If this yields a ' \
            'new value, push it on the stack (leaving the iterator below ' \
            'it). If the iterator indicates it is exhausted TOS is popped, ' \
            'and the byte code counter is incremented by /delta/.'],
    0x5F : ['STORE_ATTR', 2,
            'Implements TOS.name = TOS1, where /namei/ is the index of ' \
            'name in co_names.'],
    0x60 : ['DELETE_ATTR', 2,
            'Implements del TOS.name, using /namei/ as index into co_names.'],
    0x61 : ['STORE_GLOBAL', 2,
            'Works as STORE_NAME(/namei/), but stores the name as a global.'],
    0x62 : ['DELETE_GLOBAL', 2,
            'Works as DELETE_NAME(/namei/), but deletes a global name.'],
    0x63 : ['DUP_TOPX', 2,
            'Duplicate /count/ items, keeping them in the same order. Due ' \
            'to implementation limits, count should be between 1 and 5 ' \
            'inclusive.'],
    0x64 : ['LOAD_CONST', 2, 'Pushes "co_consts[/consti/]" onto the stack.'],
    0x65 : ['LOAD_NAME', 2,
            'Pushes the value associated with "co_names[/namei/]" onto ' \
            'the stack.'],
    0x66 : ['BUILD_TUPLE', 2,
            'Creates a tuple consuming /count/ items from the stack, and ' \
            'pushes the resulting tuple onto the stack.'],
    0x67 : ['BUILD_LIST', 2,
            'Works as BUILD_TUPLE(/count/), but creates a list.'],
    0x68 : ['BUILD_MAP', 2,
            'Pushes a new empty dictionary object onto the stack. The ' \
            'argument is ignored and set to /zero/ by the compiler.'],
    0x69 : ['LOAD_ATTR', 2,
            'Replaces TOS with getattr(TOS, co_names[/namei/]).'],
    0x6A : ['COMPARE_OP', 2,
            'Performs a Boolean operation. The operation name can be found ' \
            'in cmp_op[/opname/].'],
    0x6B : ['IMPORT_NAME', 2,
            'Imports the module co_names[/namei/]. The module object is ' \
            'pushed onto the stack. The current namespace is not ' \
            'affected: for a proper import statement, a subsequent ' \
            'STORE_FAST instruction modifies the namespace.'],
    0x6C : ['IMPORT_FROM', 2,
            'Loads the attribute co_names[/namei/] from the module found ' \
            'in TOS. The resulting object is pushed onto the stack, to ' \
            'be subsequently stored by a STORE_FAST instruction. '],
    0x6E : ['JUMP_FORWARD', 2, 'Increments byte code counter by /delta/.'],
    0x6F : ['JUMP_IF_FALSE', 2,
            'If TOS is false, increment the byte code counter by /delta/. ' \
            'TOS is not changed.'],
    0x70 : ['JUMP_IF_TRUE', 2,
            'If TOS is true, increment the byte code counter by /delta/. ' \
            'TOS is left on the stack.'],
    0x71 : ['JUMP_ABSOLUTE', 2, 'Set byte code counter to /target/.'],
    0x74 : ['LOAD_GLOBAL', 2,
            'Loads the global named co_names[/namei/] onto the stack.'],
    0x77 : ['CONTINUE_LOOP', 2,
            'Continues a loop due to a continue statement. /target/ is the ' \
            'address to jump to (which should be a FOR_ITER instruction).'],
    0x78 : ['SETUP_LOOP', 2,
            'Pushes a block for a loop onto the block stack. The block ' \
            'spans from the current instruction with a size of /delta/ ' \
            'bytes.'],
    0x79 : ['SETUP_EXCEPT', 2,
            'Pushes a try block from a try-except clause onto the block ' \
            'stack. /delta/ points to the first except block.'],
    0x7A : ['SETUP_FINALLY', 2,
            'Pushes a try block from a try-except clause onto the block ' \
            'stack. /delta/ points to the finally block.'],
    0x7C : ['LOAD_FAST', 2,
            'Pushes a reference to the local co_varnames[/var_num/] onto ' \
            'the stack.'],
    0x7D : ['STORE_FAST', 2,
            'Stores TOS into the local co_varnames[/var_num/].'],
    0x7E : ['DELETE_FAST', 2, 'Deletes local co_varnames[/var_num/].'],
    0x82 : ['RAISE_VARARGS', 2,
            'Raises an exception. /argc/ indicates the number of ' \
            'parameters to the raise statement, ranging from 0 to 3. ' \
            'The handler will find the traceback as TOS2, the parameter as ' \
            'TOS1, and the exception as TOS.'],
    0x83 : ['CALL_FUNCTION', 2,
            'Calls a function. The low byte of /argc/ indicates the number ' \
            'of positional parameters, the high byte the number of keyword ' \
            'parameters. On the stack, the opcode finds the keyword ' \
            'parameters first. For each keyword argument, the value is on ' \
            'top of the key. Below the keyword parameters, the positional ' \
            'parameters are on the stack, with the right-most parameter on ' \
            'top. Below the parameters, the function object to call is on ' \
            'the stack.'],
    0x84 : ['MAKE_FUNCTION', 2,
            'Pushes a new function object on the stack. TOS is the code ' \
            'associated with the function. The function object is defined ' \
            'to have /argc/ default parameters, which are found below TOS.'],
    0x85 : ['BUILD_SLICE', 2,
            'Pushes a slice object on the stack. /argc/ must be 2 or 3. If ' \
            'it is 2, slice(TOS1, TOS) is pushed; if it is 3, ' \
            'slice(TOS2, TOS1, TOS) is pushed. See the slice() built-in ' \
            'function for more information.'],
    0x86 : ['MAKE_CLOSURE', 2,
            'Creates a new function object, sets its func_closure slot, ' \
            'and pushes it on the stack. TOS is the code associated with ' \
            'the function. If the code object has N free variables, the ' \
            'next N items on the stack are the cells for these variables. ' \
            'The function also has /argc/ default parameters, where are ' \
            'found before the cells.'],
    0x87 : ['LOAD_CLOSURE', 2,
            'Pushes a reference to the cell contained in slot /i/ of the ' \
            'cell and free variable storage. The name of the variable is ' \
            'co_cellvars[i] if i is less than the length of co_cellvars. ' \
            'Otherwise it is co_freevars[i - len(co_cellvars)].'],
    0x88 : ['LOAD_DEREF', 2,
            'Loads the cell contained in slot /i/ of the cell and free ' \
            'variable storage. Pushes a reference to the object the cell ' \
            'contains on the stack.'],
    0x89 : ['STORE_DEREF', 2,
            'Stores TOS into the cell contained in slot /i/ of the cell ' \
            'and free variable storage.'],
    0x8C : ['CALL_FUNCTION_VAR', 2,
            'Calls a function. /argc/ is interpreted as in CALL_FUNCTION. ' \
            'The top element on the stack contains the variable argument ' \
            'list, followed by keyword and positional arguments.'],
    0x8D : ['CALL_FUNCTION_KW', 2,
            'Calls a function. /argc/ is interpreted as in CALL_FUNCTION. ' \
            'The top element on the stack contains the keyword arguments ' \
            'dictionary, followed by explicit keyword and positional ' \
            'arguments.'],
    0x8E : ['CALL_FUNCTION_VAR_KW', 2,
            'Calls a function. /argc/ is interpreted as in CALL_FUNCTION. ' \
            'The top element on the stack contains the keyword arguments ' \
            'dictionary, followed by the variable-arguments tuple, ' \
            'followed by explicit keyword and positional arguments.'],
    0x8F : ['EXTENDED_ARG', 2, 'Support for opargs more than 16 bits long.']
}

cmp_op = {
    0x00 : '<',
    0x01 : '<=',
    0x02 : '==',
    0x03 : '!=',
    0x04 : '>',
    0x05 : '>=',
    0x06 : 'in',
    0x07 : 'not in',
    0x08 : 'is',
    0x09 : 'is not',
    0x0a : 'EXC_MATCH',
    0x0b : 'BAD'
}

marshal_types = {
    0x28 : ['TUPLE'],            # (
    0x2E : ['ELLIPSIS'],         # .
    0x30 : ['NULL'],             # 0
    0x3C : ['SET'],              # <
    0x3E : ['FROZENSET'],        # >
    0x3F : ['UNKNOWN'],          # ?
    0x46 : ['FALSE'],            # F
    0x49 : ['INT64'],            # I
    0x4E : ['NONE'],             # N
    0x52 : ['STRINGREF'],        # R
    0x53 : ['STOPITER'],         # S
    0x54 : ['TRUE'],             # T
    0x5B : ['LIST'],             # [
    0x63 : ['CODE'],             # c
    0x66 : ['FLOAT'],            # f
    0x67 : ['BINARY_FLOAT'],     # g
    0x69 : ['INT'],              # i
    0x6C : ['LONG'],             # l
    0x73 : ['STRING'],           # s
    0x74 : ['INTERNED'],         # t
    0x78 : ['COMPLEX'],          # x
    0x79 : ['BINARY_COMPLEX'],   # y
    0x7B : ['DICT'],             # {
    0x75 : ['UNICODE']           # u
}

flags = {
    0x0001 : 'OPTIMIZED',
    0x0002 : 'NEWLOCALS',
    0x0004 : 'VARARGS',
    0x0008 : 'VARKEYWORDS',
    0x0010 : 'NESTED',
    0x0020 : 'GENERATOR',
    0x0040 : 'NOFREE',
    0x1000 : 'GENERATOR_ALLOWED',
    0x2000 : 'FUTURE_DIVISION',
    0x4000 : 'FUTURE_ABSOLUTE_IMPORT',
    0x8000 : 'FUTURE_WITH_STATEMENT'
}

rflags = dict((flags[x], x) for x in flags.keys())
ropcodes = dict((opcodes[x][0], x) for x in opcodes.keys())

def __printOpcodes__():
    '''Prints html pages with table of opcodes.'''

    import os
    import re
    path = '../../../tests/all_opcodes/'
    cdir = os.path.abspath(os.curdir)
    os.chdir(path)
    k = opcodes.keys()
    k.sort()
    print '<html><head><style>table,td {border-width:1px;' \
          'border-collapse:collapse;border-style:solid;border-color:black;' \
          'padding:5px}</style></head>'
    print '<body><table><tr><td>Opcode</td><td>Mnemonics</td>' \
          '<td>Operand length</td><td>Description</td><td>Source code</td>' \
          '<td>Assembly</td></tr>'
    for e in k:
        print '<tr>'
        if os.system('./test.pl %.2X.py \&> /dev/null' % e) == 0:
            print "<td style='background:lightgreen'>%.2Xh</td>" % e
        else:
            print "<td style='background:pink'>%.2Xh</td>" % e
        print '<td>%s</td><td>%s</td><td>%s</td>' % (opcodes[e][0],
                                                     str(opcodes[e][1]),
                                                     opcodes[e][2])
        print '<td><pre>'
        # >> source
        try:
            f = open('%.2X.py' % e)
            print f.read()
            f.close()
            print '</pre></td>'
            print "<td onclick='o=document.getElementById(\"a%d\");" \
                  "o.style.display=o.style.display==\"block\"?" \
                  "\"none\":\"block\"'>" \
                  "<pre style='display:none' id='a%d'>\n" % (e, e)
            # >> disasm
            f = os.popen('UnPyc -dq %.2X.pyc' % e)
            print re.sub(opcodes[e][0],
                         '<b>' + opcodes[e][0] + '</b>', f.read())
            f.close()
        except:
            print '???'
            print '</pre></td>'
            print '<td><pre>'
            print '???'
        print '</pre></td>'
        print '</tr>'
    print '</table></body></html>'
    os.chdir(cdir)

def __printFlags__():
    '''Prints html pages with table of flags.'''

    k = flags.keys()
    k.sort()
    print '<html><head><style>table,td {border-width:1px;' \
          'border-collapse:collapse;border-style:solid;border-color:black;' \
          'padding:5px}</style></head>'
    print '<body><table><tr><td>Flag</td><td>Mnemonics</td>' \
          '<td>Description</td><td>Source code</td><td>Flags</td></tr>'
    for e in k:
        print '<tr>'
        print '<td>%.4Xh</td><td>%s</td><td>?</td>' % (e, flags[e])
        print '<td><pre>\n?\n</pre></td>'
        print '<td><pre>\n?\n</pre></td>'
        print '</tr>\n'
    print '</table></body></html>'

def __printTypes__():
    '''Prints marshal types.'''

    k = marshal_types.keys()
    k.sort()
    for x in k:
        print marshal_types[x][0]

if __name__ == '__main__':
    __printOpcodes__()
