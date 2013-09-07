#!/usr/bin/env python
##WingHeader v1 
###############################################################################
## File       :  disasm.py
## Description:  
##            :  
## Created_On :  Sat Oct 30 00:48:26 2010
## Created_By :  Rich Smith
## Modified_On:  
## Modified_By:  
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
This module provides core functions for disassembly.

That includes primitives of working with python bytecode, manipulating
basic blocks, some bytecode optimizations and disassembler itself.

'''

import struct
from copy import deepcopy

import opcodes
import parse

class Command:
    '''Single command in bytecode.'''

    def __init__(self, offset, opcode, mnemonics, argument=None):
        '''
        @param offset: offset of the command in the co_code.
        @param opcode: byte that defines command.
        @param mnemonics: mnemonics of the command.
        @param argument: word, that defines argument (None if command
            takes no arguments).

        '''
        self.offset = offset
        self.opcode = opcode
        self.argument = argument
        self.mnemonics = mnemonics
        if argument is not None:
            self.length = 3
        else:
            self.length = 1

    def __str__(self):
        if self.argument is not None:
            return '%.8X %.2X - %s(%.4X)' % (self.offset, self.opcode,
                                             self.mnemonics, self.argument)
        return '%.8X %.2X - %s()' % (self.offset, self.opcode, self.mnemonics)

class Reference:
    '''Stores block xref information.'''

    def __init__(self, xref, blockxref, name):
        '''
        @param xref: offset of the command that made reference.
        @param blockxref:
            offset of the basic block that contains the command
            that made reference.
        @param name: type of reference (JIT, JIF, ...).

        '''
        self.xref = xref
        self.blockxref = blockxref
        self.name = name

    def __str__(self):
        return 'xref = %d, blockxref = %d, name = %s' % \
               (self.xref, self.blockxref, self.name)

class CodeBlocks:
    '''
    Basic blocks of a given program.

    They form nodes of its control flow graph.

    '''
    def __init__(self, startOffset=0):
        '''
        @param startOffset:
            offset of the first command of the first basic block.

        '''
        self.blocks = {startOffset:[]}
        self.root = startOffset

    def add(self, where, xref=None, name=None, blockxref=None):
        '''
        Add a new CodeBlock to the collection.

        @param where: offset of the first command in added block.
        @param xref:
            offset of the command, that references the added block.
        @param name:
            type of reference (JF, JIF, NJIF, JIT, NJIT, JA, finally,
            except, ...).
        @param blockxref:
            offset of the basic block that contains the command
            that made reference.

        '''
        if xref is None and name is None:
            if where not in self.blocks: self.blocks[where] = []
        else:
            if where in self.blocks:
                self.blocks[where].append(Reference(xref, blockxref, name))
            else:
                self.blocks[where] = [Reference(xref, blockxref, name)]

    def getSortedRefs(self):
        '''@return: sorted by xref list of references.'''

        refs = []
        for where in self.blocks: refs.extend(self.blocks[where])
        return sorted(refs, lambda x, y: cmp(x.xref, y.xref))

    def calcBlockXrefs(self):
        '''Method recalculates blockxref fields of references.'''

        cbs = sorted(self.blocks.keys())
        refs = self.getSortedRefs()
        cbsIndex = 0
        refsIndex = 0
        while cbsIndex < len(cbs) - 1 and refsIndex < len(refs):
            while refsIndex < len(refs) and \
                  cbs[cbsIndex + 1] > refs[refsIndex].xref:
                refs[refsIndex].blockxref = cbs[cbsIndex]
                refsIndex += 1
            cbsIndex += 1
        while refsIndex < len(refs):
            refs[refsIndex].blockxref = cbs[cbsIndex]
            refsIndex += 1

    def strkey(self, k):
        '''
        @param k: offset of the block to stringify.
        @return: string representation of the given CodeBlock.

        '''
        return ', '.join(('%s(%.8X@%.8X)') % (x.name, x.xref, x.blockxref)
                         for x in self.blocks[k])

    def __str__(self):
        r = ''
        for k in sorted(self.blocks.keys()):
            r += '%.8X <- ' % k + self.strkey(k) + '\n'
        return r

class Commands:
    '''Container for L{Command}s collection.'''

    def __init__(self, cmdList, offsets, cmdHash):
        '''
        @param cmdList: list     of commands.
        @param offsets: offsets of given list of commands.
        @param cmdHash: hash of given commands (offset -> command).

        '''
        self.cmdList = cmdList
        self.offsets = offsets
        self.cmdHash = cmdHash

    def __str__(self):
        return '\n'.join(str(cmd) for cmd in self.cmdList)

class Disassembler:
    '''Disassembler itself.'''

    def __init__(self, co, optimizeJumps=False, raw = False):
        '''
        @param co: code object, that is going to be disassembled.
        @param optimizeJumps:
            if true, disassembler does some bytecode optimization,
            see L{optimizeJumps} and L{optimizeAbsoluteJumps} for more
            information.

        '''
        self.co = co
        if not raw:
            self.commands = self.disasmCommands(self.co.code.value)
        else:
            self.commands = self.disasmCommands(co)
        if optimizeJumps:
            self.optimizeJumps()
            self.optimizeAbsoluteJumps()

    def optimizeJumps(self):
        '''
        Optimizes conditional jumps.

        Replaces JUMP_IF_* -> JUMP_IF_* -> ... -> TARGET
        with JUMP_IF_* -> TARGET.

        '''
        def getOptimizationAddr(cmd, negate=False):
            '''
            @param cmd: L{Command} from which to start.
            @param negate:
                the way to process UNARY_NOT + JUMP_IF.
            @return: address of the next hop.

            '''
            if cmd.mnemonics is not None and cmd.argument is not None:
                if cmd.mnemonics == 'JUMP_IF_FALSE' and negate == False or \
                   cmd.mnemonics == 'JUMP_IF_TRUE' and negate == True:
                    targetAddr = cmd.offset + cmd.argument + cmd.length
                    target = self.commands.cmdHash[targetAddr]
                    afterTargetAddr = target.offset + target.length
                    ##XXX Rich
                    try:
                        afterTarget = self.commands.cmdHash[afterTargetAddr]
                    except:
                        #print "zzzzzzzzzz"
                        #print targetAddr
                        #print target, target.offset , target.length
                        #print afterTargetAddr
                        #print cmd.mnemonics
                        #print self.commands.cmdHash
                        #raw_input()
                        return (None, None)
                        
                    if target.mnemonics == 'JUMP_IF_FALSE':
                        rAddr = target.offset + target.argument + target.length
                        return (rAddr, False)
                    elif target.mnemonics == 'UNARY_NOT' and \
                         afterTarget.mnemonics == 'JUMP_IF_TRUE':
                        rAddr = afterTarget.offset + \
                                afterTarget.argument + \
                                afterTarget.length
                        return (rAddr, True)
                    elif target.mnemonics == 'JUMP_IF_TRUE':
                        return (target.offset + target.length, False)
                    elif target.mnemonics == 'UNARY_NOT' and \
                         afterTarget.mnemonics == 'JUMP_IF_FALSE':
                        return (afterTarget.offset + afterTarget.length, True)
                if cmd.mnemonics == 'JUMP_IF_TRUE' and negate == False or \
                   cmd.mnemonics == 'JUMP_IF_FALSE' and negate == True:
                    targetAddr = cmd.offset + cmd.argument + cmd.length
                    target = self.commands.cmdHash[targetAddr]
                    afterTargetAddr = target.offset + target.length
                    afterTarget = self.commands.cmdHash[afterTargetAddr]
                    if target.mnemonics == 'JUMP_IF_TRUE':
                        rAddr = target.offset + target.argument + target.length
                        return (rAddr, False)
                    elif target.mnemonics == 'UNARY_NOT' and \
                         afterTarget.mnemonics == 'JUMP_IF_FALSE':
                        rAddr = afterTarget.offset + \
                                afterTarget.argument + \
                                afterTarget.length
                        return (rAddr, True)
                    elif target.mnemonics == 'JUMP_IF_FALSE':
                        return (target.offset + target.length, False)
                    elif target.mnemonics == 'UNARY_NOT' and \
                         afterTarget.mnemonics == 'JUMP_IF_TRUE':
                        return (afterTarget.offset + afterTarget.length, True)
            return (None, None)

        for cmd in self.commands.cmdList:
            (addr, negate) = getOptimizationAddr(cmd)
            while addr is not None:
                cmd.argument = addr - cmd.offset - cmd.length
                (addr, negate) = getOptimizationAddr(cmd, negate)

    def optimizeAbsoluteJumps(self):
        '''
        Replaces JUMP_ABSOLUTE with CONTINUE_LOOP or NOP.

        If JUMP_ABSOLUTE is the last one in the byte code for the
        specified target, then replace it with NOP, otherwise replace
        with CONTINUE_LOOP.

        '''
        possible = {}
        for cmd in self.commands.cmdList:
            if cmd.mnemonics == 'FOR_ITER':
                possible[cmd.offset] = 0
            elif cmd.mnemonics == 'SETUP_LOOP':
                possible[cmd.offset + cmd.length] = 0
        index = len(self.commands.cmdList) - 1
        while index >= 0:
            cmd = self.commands.cmdList[index]
            if cmd.mnemonics == 'JUMP_ABSOLUTE':
                if cmd.argument in possible and cmd.offset > cmd.argument:
                    if possible[cmd.argument] == 0:
                        possible[cmd.argument] = 1
                        cmd.mnemonics = 'NOP'
                        cmd.argument = None
                    else:
                        cmd.mnemonics = 'CONTINUE_LOOP'
                else:
                    # TODO: panic... strange jump
                    print 'STRANGE ABSOLUTE JUMP!!!'
            index -= 1

    @staticmethod
    def disasmCommands(co_code, startOffset=0):
        '''
        @param co_code: bytecode.
        @param startOffset: offset base.
        @return: L{Commands} for the specified co_code.

        '''
        commands = []
        offsets = []
        cmdHash = {}
        i = 0
        border = len(co_code)
        while i < border:
            offset = i + startOffset
            opcode = struct.unpack('=B', co_code[i])[0]
            i += 1
            name = None
            argument = None
            if opcode in opcodes.opcodes:
                name = opcodes.opcodes[opcode][0]
                size = opcodes.opcodes[opcode][1]
                if size != 0:
                    argument = parse.getInt(co_code[i:i + size])
                    i += size
            cmd = Command(offset, opcode, name, argument)
            commands.append(cmd)
            offsets.append(offset)
            cmdHash[offset] = cmd
        return Commands(commands, offsets, cmdHash)

    def getCommands(self, offset=0, length=0):
        '''
        @param offset: start offset in co_code.
        @param length: length of the substring in co_code.
        @return:
            Commands object, which represents the given slice of
            co_code.

        '''
        commands = deepcopy(self.commands)
        data = self.co.code.value
        if offset == 0 and length == 0: return commands
        if length == 0: length = len(data) - offset
        if length + offset > len(data): length = len(data) - offset
        if offset not in commands.cmdHash: return None
        start = None
        end = None
        for i in xrange(len(commands.offsets)):
            x = commands.offsets[i]
            if x < offset:
                del commands.cmdHash[x]
            elif x >= length + offset:
                del commands.cmdHash[x]
                if end is None: end = i
            else:
                if start is None: start = i
        if start is not None:
            commands.cmdList = commands.cmdList[start:end]
            commands.offsets = commands.offsets[start:end]
        else:
            commands.cmdList = []
            commands.offset = []
        return commands

    def getAllCodeBlocks(self, offset=0, length=0):
        '''
        Builds basic blocks of current co_code.

        @param offset: start offset in co_code.
        @param length: length of the substring in co_code.
        @return: L{CodeBlocks} of the current code object.

        '''
        commands = self.getCommands(offset, length).cmdList
        cb = CodeBlocks(offset)
        for cmd in commands:
            if cmd.mnemonics is not None:
                if cmd.argument is not None or cmd.mnemonics == 'END_FINALLY':
                    if cmd.mnemonics == 'JUMP_FORWARD':
                        cb.add(cmd.offset + cmd.length)
                        cb.add(cmd.offset + cmd.argument + cmd.length,
                               cmd.offset, 'JF')
                    elif cmd.mnemonics == 'JUMP_IF_FALSE':
                        cb.add(cmd.offset + cmd.length, cmd.offset, 'NJIF')
                        cb.add(cmd.offset + cmd.argument + cmd.length,
                               cmd.offset, 'JIF')
                    elif cmd.mnemonics == 'JUMP_IF_TRUE':
                        cb.add(cmd.offset + cmd.length, cmd.offset, 'NJIT')
                        cb.add(cmd.offset + cmd.argument + cmd.length,
                               cmd.offset, 'JIT')
                    elif cmd.mnemonics == 'JUMP_ABSOLUTE':
                        cb.add(cmd.offset + cmd.length)
                        cb.add(cmd.argument, cmd.offset, 'JA')
                    elif cmd.mnemonics == 'SETUP_FINALLY':
                        cb.add(cmd.offset + cmd.length, cmd.offset, 'ASF')
                        cb.add(cmd.offset + cmd.argument + cmd.length,
                               cmd.offset, 'finally')
                    elif cmd.mnemonics == 'END_FINALLY':
                        cb.add(cmd.offset + cmd.length, cmd.offset, 'AE')
                    elif cmd.mnemonics == 'SETUP_EXCEPT':
                        cb.add(cmd.offset + cmd.length, cmd.offset, 'try')
                        cb.add(cmd.offset + cmd.argument + cmd.length,
                               cmd.offset, 'except')
                    elif cmd.mnemonics == 'SETUP_LOOP':
                        cb.add(cmd.offset + cmd.length, cmd.offset, 'loop')
                        cb.add(cmd.offset + cmd.argument + cmd.length,
                               cmd.offset, 'AL')
                    elif cmd.mnemonics == 'FOR_ITER':
                        cb.add(cmd.offset + cmd.length, cmd.offset, 'for')
                        cb.add(cmd.offset + cmd.argument + cmd.length,
                               cmd.offset, 'AF')
        cb.calcBlockXrefs()
        return cb

    def getLoopCodeBlocks(self, offset=0, length=0):
        '''
        Builds loop blocks of current co_code.

        @param offset: start offset in co_code.
        @param length: length of the substring in co_code.
        @return: L{CodeBlocks} of current code object.

        '''
        commands = self.getCommands(offset, length).cmdList
        cb = CodeBlocks(offset)
        currentBlock = offset
        for cmd in commands:
            currentOffset = cmd.offset
            if currentOffset in cb.blocks: currentBlock = currentOffset
            if cmd.mnemonics is not None and cmd.argument is not None:
                if cmd.mnemonics == 'JUMP_ABSOLUTE':
                    cb.add(cmd.offset + cmd.length)
                    cb.add(cmd.argument, currentOffset, currentBlock, 'JA')
                elif cmd.mnemonics == 'SETUP_LOOP':
                    cb.add(cmd.offset + cmd.length, currentOffset,
                           currentBlock, 'loop')
                    cb.add(cmd.offset + cmd.argument + cmd.length,
                           currentOffset, currentBlock, 'AL')
                elif cmd.mnemonics == 'FOR_ITER':
                    cb.add(cmd.offset + cmd.length, currentOffset,
                           currentBlock, 'for')
                    cb.add(cmd.offset + cmd.argument + cmd.length,
                           currentOffset, currentBlock, 'AF')
        return cb

    def getMoreInfo(self, cmd, verbose):
        '''
        @param cmd: L{Command} on which to operate.
        @param verbose: verbosity level.
        @return: more disasm information for the given command.

        '''
        r = ''
        if cmd.mnemonics in ('LOAD_CONST', 'COMPARE_OP',
                             'LOAD_FAST', 'STORE_FAST',
                             'DELETE_FAST', 'IMPORT_NAME',
                             'IMPORT_FROM', 'STORE_GLOBAL',
                             'DELETE_GLOBAL', 'LOAD_GLOBAL',
                             'STORE_ATTR', 'DELETE_ATTR',
                             'LOAD_ATTR', 'STORE_NAME',
                             'DELETE_NAME', 'LOAD_NAME',
                             'LOAD_CLOSURE', 'LOAD_DEREF',
                             'STORE_DEREF', 'JUMP_FORWARD',
                             'JUMP_IF_TRUE', 'JUMP_IF_FALSE',
                             'SETUP_FINALLY', 'SETUP_EXCEPT',
                             'SETUP_LOOP', 'FOR_ITER',
                             'JUMP_ABSOLUTE'):
                if verbose >= 1: r += ' = '
                if cmd.mnemonics == 'LOAD_CONST':
                    const = self.co.consts.value[cmd.argument]
                    if isinstance(const, parse.pyCode):
                        r += const.info(verbose)
                    else:
                        #r += parse.shorten(
                        #         parse.dropNewLines(
                        #             const.info(verbose)))
                        r += const.info(verbose)
                elif cmd.mnemonics == 'COMPARE_OP':
                    r += '"' + opcodes.cmp_op[cmd.argument] + '"'
                elif cmd.mnemonics in ('LOAD_FAST', 'STORE_FAST',
                                       'DELETE_FAST'):
                    r += self.co.varnames.value[cmd.argument].info(verbose)
                elif cmd.mnemonics in ('IMPORT_NAME', 'IMPORT_FROM',
                                       'STORE_GLOBAL', 'DELETE_GLOBAL',
                                       'LOAD_GLOBAL', 'STORE_ATTR',
                                       'DELETE_ATTR', 'LOAD_ATTR',
                                       'STORE_NAME', 'DELETE_NAME',
                                       'LOAD_NAME'):
                        r += self.co.names.value[cmd.argument].info(verbose)
                elif cmd.mnemonics in ('LOAD_CLOSURE', 'LOAD_DEREF',
                                       'STORE_DEREF'):
                    if cmd.argument < len(self.co.cellvars.value):
                        r += self.co.cellvars.value[cmd.argument].info(verbose)
                    else:
                        index = cmd.argument - len(self.co.cellvars.value)
                        r += self.co.freevars.value[index].info(verbose)
                elif cmd.mnemonics in ('JUMP_FORWARD', 'JUMP_IF_TRUE',
                                       'JUMP_IF_FALSE', 'SETUP_FINALLY',
                                       'SETUP_EXCEPT', 'SETUP_LOOP',
                                       'FOR_ITER'):
                        rAddr = cmd.offset + cmd.argument + cmd.length
                        r += '-> %.8X' % rAddr
                elif cmd.mnemonics == 'JUMP_ABSOLUTE':
                    r += '-> %.8X' % cmd.argument
                else:
                    if verbose == 0: r += 'r%.4X' % cmd.argument
        return r

    def codeDisasm(self, offset=0, length=0, verbose=1, xref=False):
        '''
        Makes the disassembler output.

        @param offset: start offset in co_code.
        @param length: length of the substring in co_code.
        @param verbose: verbosity of the output (0, 1, 2)
        @param xref: show back references from jumps and such.
        @return: the disassembler output.

        '''
        cb = self.getAllCodeBlocks(offset, length)
        commands = self.getCommands(offset, length).cmdList
        r = ''
        for cmd in commands:
            if xref and cmd.offset in cb.blocks:
                xstring = cb.strkey(cmd.offset)
                if xstring != '':
                    r += '\n> xref ' + cb.strkey(cmd.offset) + '\n'
            r += '%.8X     ' % cmd.offset
            r += '%.2X ' % cmd.opcode
            if cmd.mnemonics is not None:
                r += '- ' + cmd.mnemonics + ' ' * (20 - len(cmd.mnemonics))
                if cmd.argument is not None:
                    if verbose >= 1: r += '%.4X' % cmd.argument
                    r += self.getMoreInfo(cmd, verbose)

                if verbose >= 2 and len(opcodes.opcodes[cmd.opcode]) > 2:
                    nT = parse.narrowText(opcodes.opcodes[cmd.opcode][2])
                    r += '\n' + parse.indentText(nT, 1)
            r += '\n'
        return r

    def disassemble(self):
        '''Wrapper that inits disassembly process.'''

        return self.co.str()