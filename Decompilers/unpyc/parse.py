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

'''Parses pyc files and builds up DOM.'''

import struct

import opcodes
import disasm

from text import showoffset, shorten, \
                 p_indent as indent, \
                 p_indentText as indentText

def getInt(array):
    '''
    Interprets sequence of bytes as unsigned int.

    @param array: sequence of bytes.
    @return: integer.

    '''
    int = 0
    j = 0
    for x in array:
        int += struct.unpack('=B', x)[0] << j
        j += 8
    return int

def readRaw(raw):
    '''
    Does byte -> hex transformation of a given string.

    @param raw: string of bytes.
    @return: string of hexes.

    '''
    res = ''
    if isinstance(raw, str):
        return ' '.join(['%.2X' % struct.unpack('=B', c)[0] for c in raw])
    else:
        raise TypeError

class ParseErrorException():
    '''Thrown when parser breaks.'''

    def __init__(self, offset):
        '''@param offset: offset at which error occured.'''

        self.offset = offset

    def __str__(self):
        return '>>> Parsing error occured at offset %s.' % showoffset(self.offset)

class BadFirstObjectException():
    '''Thrown when first object in pyc file is not code object.'''

    def __str__(self):
        return '>>> First object in pyc file should be CODE object.'

class IOErrorException():
    '''Thrown when IO error occurs during work with files.'''

    def __init__(self, text):
        self.message = text

    def __str__(self):
        return '>>> ' + self.message

class AbstractMethodException():
    '''Only for development. A `TODO' for `abstract' methods.'''

    def __init__(self):
        print 'Please redefine this method!'

class pyObject:
    '''Basic `abstract' class for the pyc DOM.'''

    def __init__(self, offset, type, value, raw=''):
        '''
        @param offset: offset of the object.
        @param type: python type of the object (e.g. list, str, ...).
        @param value: value of the object.
        @param raw: raw bytes that represent the object.

        '''
        self.parent = None
        self.depth = 0
        self.type = type
        self.value = value
        self.offset = offset
        if isinstance(raw, str):
            self.raw = raw
        else:
            raise TypeError

    def str(self, depth=0):
        '''Used when sections such as constants are stringified.'''

        raise AbstractMethodException()

    def info(self, verbose=0):
        '''Used to output arguments of opcodes.'''

        raise AbstractMethodException()

    def repr(self):
        '''Used in decompiler.'''

        return repr(self.value)

##################
# simple objects #
##################

class pySimpleObject(pyObject):
    '''Basic class for simple objects in DOM (None, True, False, ...).'''

    def __init__(self, offset, type, value, raw):
        pyObject.__init__(self, offset, type, value, raw)

    def str(self, depth=0):
        return indent(depth, self.offset) + \
               shorten(str(self.value)) + \
               ' (%s)' % shorten(readRaw(self.raw))

    def info(self, verbose=0):
        if verbose >= 1:
            return showoffset(self.offset) + ' ' + \
                   shorten(str(self.value)) + \
                   ' (%s)' % shorten(readRaw(self.raw))
        else:
            return shorten(str(self.value))

class pyNull(pySimpleObject):
    def __init__(self, offset):
        pySimpleObject.__init__(self, offset, 'NullType', 'Null', '0')

class pyNone(pySimpleObject):
    def __init__(self, offset):
        pySimpleObject.__init__(self, offset, 'NoneType', None, 'N')

class pyStopIter(pySimpleObject):
    def __init__(self, offset):
        pySimpleObject.__init__(self, offset, 'StopIterType', 'StopIter', 'S')

class pyEllipsis(pySimpleObject):
    def __init__(self, offset):
        pySimpleObject.__init__(self, offset, '...', Ellipsis, '.')

class pyFalse(pySimpleObject):
    def __init__(self, offset):
        pySimpleObject.__init__(self, offset, 'bool', False, 'F')

class pyTrue(pySimpleObject):
    def __init__(self, offset):
        pySimpleObject.__init__(self, offset, 'bool', True, 'T')

class pyUnknown(pySimpleObject):
    def __init__(self, offset):
        pySimpleObject.__init__(self, offset, 'UnknownType', 'Unknown', '?')

###################
# complex objects #
###################

class pyComplexObject(pyObject):
    '''Basic class for complex objects in DOM (e.g. int, str, list, etc).'''

    def str(self, depth=0):
        return indent(depth, self.offset) + self.type.upper() + \
               ': %s (%s)' % (repr(shorten(self.value)),
                              shorten(readRaw(self.raw)))

    def info(self, verbose=0):
        if verbose >= 1:
            return showoffset(self.offset) + ' ' + self.type.upper() + \
                   ': %s (%s)' % (repr(shorten(self.value)),
                                  shorten(readRaw(self.raw)))
        else:
            #return repr(shorten(self.value))
            return repr(self.value)

class pyInt(pyComplexObject):
    def __init__(self, offset, integer, raw):
        if isinstance(integer, int) or isinstance(integer, long):
            pyComplexObject.__init__(self, offset, 'int', integer, raw)
        else:
            raise TypeError

class pyLong(pyComplexObject):
    def __init__(self, offset, l, raw):
        if isinstance(l, long):
            pyComplexObject.__init__(self, offset, 'long', l, raw)
        else:
            raise TypeError

class pyInt64(pyComplexObject):
    def __init__(self, offset, l, raw):
        if isinstance(l, long):
            pyComplexObject.__init__(self, offset, 'int64', l, raw)
        else:
            raise TypeError

class pyFloat(pyComplexObject):
    def __init__(self, offset, float_num, raw):
        if isinstance(float_num, float):
            pyComplexObject.__init__(self, offset, 'float', float_num, raw)
        else :
            raise TypeError

class pyComplex(pyComplexObject):
    def __init__(self, offset, complex_num, raw):
        if isinstance(complex_num, complex):
            pyComplexObject.__init__(self, offset, 'complex', complex_num,
                                     raw)
        else:
            raise TypeError

class pyInterned(pyComplexObject):
    def __init__(self, offset, string, raw):
        if isinstance(string, str):
            pyComplexObject.__init__(self, offset, 'str', string, raw)
            self.length = len(string)
        else:
            raise TypeError

class pyString(pyInterned):
    pass

class pyStringRef(pyInterned):
    pass

class pyUnicode(pyComplexObject):
    def __init__(self, offset, string, raw):
        if isinstance(string, unicode):
            pyComplexObject.__init__(self, offset, 'unicode', string, raw)
            self.length = len(string)
        else:
            raise TypeError

class pyTuple(pyComplexObject):
    def __init__(self, offset, tpl):
        if isinstance(tpl, tuple):
            pyComplexObject.__init__(self, offset, 'tuple', tpl)
            self.length = len(tpl)
        else:
            raise TypeError

    def showElements(self, depth=0):
        return ',\n'.join('%s' % e.str(depth+1).rstrip('\n')
                          for e in self.value) + '\n' + indent(depth)

    def str(self, depth=0):
        if self.length == 0:
            return indent(depth, self.offset) + 'TUPLE: ()'
        return indent(depth, self.offset) + 'TUPLE: (\n' + \
               self.showElements(depth) + ')'

    def showElementsInfo(self, verbose=0):
        return ', '.join('%s' % e.info(verbose) for e in self.value)

    def info(self, verbose=0):
        if verbose >= 1:
            if self.length == 0:
                return showoffset(self.offset) + ' TUPLE: ()'
            return showoffset(self.offset) + ' TUPLE: (' + \
                   self.showElementsInfo(verbose) + ')'
        else:
            if self.length == 0:
                return '()'
            return '(' + self.showElementsInfo(verbose) + ')'

class pyList(pyTuple):
    def __init__(self, offset, lst):
        if isinstance(lst, list):
            pyComplexObject.__init__(self, offset, 'list', lst)
            self.length = len(lst)
        else:
            raise TypeError

    def str(self, depth=0):
        if self.length == 0:
            return indent(depth, self.offset) + 'LIST: []'
        return indent(depth, self.offset) + 'LIST: [\n' + \
               self.showElements(depth) + ']'

    def info(self, verbose=0):
        if verbose >= 1:
            if self.length == 0:
                return showoffset(self.offset) + ' LIST: []'
            return showoffset(self.offset) + ' LIST: [' + \
                   self.showElementsInfo(verbose) + ']'
        else:
            if self.length == 0:
                return '[]'
            return '[' + self.showElementsInfo(verbose) + ']'

class pyDict(pyComplexObject):
    def __init__(self, offset, d):
        if isinstance(d, dict):
            pyComplexObject.__init__(self, offset, 'dict', d)
            self.length = len(d)
        else:
            raise TypeError

    # TODO: very old str`s were used, could break here
    def str(self, depth=0):
        if self.length == 0:
            return indent(depth, self.offset) + 'DICT: {}'
        return indent(depth, self.offset) + 'DICT: {\n' + \
               ',\n'.join('%s : %s' % (i.str(depth+1), self.value[i].str())
                            for i in self.value) + '\n' + indent(depth) + '}'

    # TODO: test this one
    def info(self, verbose=0):
        if verbose >= 1:
            if self.length == 0:
                return showoffset(self.offset) + ' DICT: {}'
            return showoffset(self.offset) + ' DICT: {' + \
                   ', '.join('%s : %s' % (i.info(verbose),
                                            self.value[i].info(verbose))
                               for i in self.value) + '}'
        else:
            if self.length == 0: return '{}'
            return '{' + (', ').join('%s : %s' % (i.info(verbose),
                                                  self.value[i].info(verbose))
                                     for i in self.value) + '}'

class pySet(pyTuple):
    def __init__(self, offset, s):
        if isinstance(s, set):
            pyComplexObject.__init__(self, offset, 'set', s)
            self.length = len(s)
        else:
            raise TypeError

    def str(self, depth=0):
        if self.length == 0:
            return indent(depth, self.offset) + 'SET: set([])'
        return indent(depth, self.offset) + 'SET: set([\n' + \
               self.showElements(depth) + '])'

    def info(self, verbose=0):
        if verbose >= 1:
            if self.length == 0:
                return showoffset(self.offset) + ' SET: set([])'
            return showoffset(self.offset) + ' SET: set([' + \
                   self.showElementsInfo(verbose) + '])'
        else:
            if self.length == 0:
                return 'set([])'
            return 'set([' + self.showElementsInfo(verbose) + '])'

class pyFrozenSet(pyTuple):
    def __init__(self, offset, s):
        if isinstance(s, frozenset):
            pyComplexObject.__init__(self, offset, 'frozenset', s)
            self.length = len(s)
        else:
            raise TypeError

    def str(self, depth=0):
        if self.length == 0:
            return indent(depth, self.offset) + 'FROZENSET: frozenset([])'
        return indent(depth, self.offset) + 'FROZENSET: frozenset([\n' + \
               self.showElements(depth) + '])'

    def info(self, verbose=0):
        if verbose >= 1:
            if self.length == 0:
                return showoffset(self.offset) + ' FROZENSET: frozenset([])'
            return showoffset(self.offset) + ' FROZENSET: frozenset([' + \
                   self.showElementsInfo(verbose) + '])'
        else:
            if self.length == 0:
                return 'frozenset([])'
            return 'frozenset([' + self.showElementsInfo(verbose) + '])'

class pyCode(pyComplexObject):
    def __init__(self, offset, argcount, nlocals, stacksize, flags, code,
                 consts, names, varnames, freevars, cellvars, filename, name,
                 firstlineno, lnotab, verboseDisasm=0, xrefDisasm=False):
               
        pyComplexObject.__init__(self, offset, 'code', code)
        self.verboseDisasm = verboseDisasm
        self.xrefDisasm = xrefDisasm
        self.argcount = argcount
        self.nlocals = nlocals
        self.stacksize = stacksize
        self.flags = flags
        self.code = code
        self.consts = consts
        self.names = names
        self.varnames = varnames
        self.freevars = freevars
        self.cellvars = cellvars
        self.filename = filename
        self.name = name
        self.firstlineno = firstlineno
        self.lnotab = lnotab
        
        #print "C %s"%(code.info())
        
    ##XXX Rich
    def __str__(self):
        return self.str()

    def str(self, depth=0):
        dis = disasm.Disassembler(self)
        ind = indent(depth + 1)
        
        r = indent(depth, self.offset) + 'CODE:\n' + \
            ind + 'argcount:\n%s\n' % self.argcount.str(depth + 2) + \
            ind + 'nlocals:\n%s\n' % self.nlocals.str(depth + 2) + \
            ind + 'stacksize:\n%s\n' % self.stacksize.str(depth + 2) + \
            ind + 'flags:\n%s\n' % self.flags.str(depth + 2) + \
            indent(depth + 2) + '(' + \
            ', '.join([opcodes.flags[f]
                       for f in opcodes.flags
                       if f & self.flags.value]) + ')\n' + \
            ind + 'code:\n%s\n' % self.code.str(depth + 2) + \
            indentText(dis.codeDisasm(verbose=self.verboseDisasm,
                                      xref=self.xrefDisasm), depth + 2) + \
            ind + 'consts:\n%s\n' % self.consts.str(depth + 2) + \
            ind + 'names:\n%s\n' % self.names.str(depth + 2) + \
            ind + 'varnames:\n%s\n' % self.varnames.str(depth + 2) + \
            ind + 'freevars:\n%s\n' % self.freevars.str(depth + 2) + \
            ind + 'cellvars:\n%s\n' % self.cellvars.str(depth + 2) + \
            ind + 'filename:\n%s\n' % self.filename.str(depth + 2) + \
            ind + 'name:\n%s\n' % self.name.str(depth + 2) + \
            ind + 'firslineno:\n%s\n' % self.firstlineno.str(depth + 2) + \
            ind + 'lnotab:\n%s\n' % self.lnotab.str(depth + 2)
        
        return r
    

    def info(self, verbose=0):
        if verbose >= 1:
            return '%.8X CODE(%s)' % (self.offset, self.name.repr())
        else:
            return 'CODE(%s)' % self.name.repr()


class Parser:
    '''
    Parser class itself.

    Refer to marshal.c for more information on r_* things.

    '''

    def nop(self):
        pass

    def r_byte(self):
        if self.p + 1 > len(self.data):
            raise ParseErrorException(self.p)
        offset = self.p
        self.p += 1
        value = int(struct.unpack('=b', self.data[self.p - 1 : self.p])[0])
        return pyInt(offset, value, self.data[self.p - 1 : self.p])

    def r_short(self):
        if self.p + 2 > len(self.data):
            raise ParseErrorException(self.p)
        offset = self.p
        self.p += 2
        value = int(struct.unpack('=h', self.data[self.p - 2 : self.p])[0])
        return pyInt(offset, value, self.data[self.p - 2 : self.p])

    def r_long(self):
        # read dword, don't confuse with r_type_long
        if self.p + 4 > len(self.data):
            raise ParseErrorException(self.p)
        offset = self.p
        self.p += 4
        value = long(struct.unpack('=l', self.data[self.p - 4 : self.p])[0])
        return pyLong(offset, value, self.data[self.p - 4 : self.p])

    def r_unsigned_long(self):
        if self.p + 4 > len(self.data):
            raise ParseErrorException(self.p)
        offset = self.p
        self.p += 4
        value = long(struct.unpack('=L', self.data[self.p - 4 : self.p])[0])
        return pyLong(offset, value, self.data[self.p - 4 : self.p])

    def r_type_long(self):
        offset = self.p
        n = self.r_long().value
        if n < 0: sign = -1; n = -n
        else: sign = 1
        if self.p + 2 * n > len(self.data):
            raise ParseErrorException(self.p)
        raw = ''
        l = 0L
        for i in range(n):
            d = self.r_short()
            if d.value < 0:
                raise ParseErrorException(self.p)
            l += d.value * 32768 ** i
            raw += d.raw
        return pyLong(offset, l * sign, raw)

    def r_float(self):
        if self.p + 8 > len(self.data):
            raise ParseErrorException(self.p)
        offset = self.p
        self.p += 8
        value = struct.unpack('=d', self.data[self.p - 8 : self.p])[0]
        return pyFloat(offset, value, self.data[self.p - 8 : self.p])

    def r_string(self):
        offset = self.p
        l = self.r_long().value
        if l < 0 or self.p + l > len(self.data):
            raise ParseErrorException(self.p)
        self.p += l
        value = self.data[self.p - l : self.p]
        return pyString(offset, value, self.data[self.p - l - 4 : self.p])

    def r_s_string(self):
        # short string - length is one byte
        offset = self.p
        l = self.r_byte().value
        if l < 0 or self.p + l > len(self.data):
            raise ParseErrorException(self.p)
        self.p += l
        value = self.data[self.p - l : self.p]
        return pyString(offset, value, self.data[self.p - l - 1 : self.p])

    def r_tuple(self):
        offset = self.p
        n = self.r_long().value
        if n < 0:
            raise ParseErrorException(self.p)
        a = []
        for i in range(n):
            a += [self.r_object()]
        return pyTuple(offset, tuple(a))

    def r_dict(self):
        offset = self.p
        d = {}
        k = self.r_object()
        while not isinstance(k, pyNull):
            d[k] = self.r_object()
            k = self.r_object()
        return pyDict(offset, d)

    def r_code(self):
        offset = self.p
        self.r_object()
        length = self.p - offset
        self.codeDisasm(offset + 5, length - 5)

    def r_object(self, force=False):
        if self.p + 1 > len(self.data):
            print "pop"
            raise ParseErrorException(self.p)
        offset = self.p
        print "byte: %d"%self.p 
        byte = struct.unpack('=B', self.data[self.p])[0]
        self.p += 1
        
        if byte in opcodes.marshal_types:
            print "G",opcodes.marshal_types[byte]
            type = opcodes.marshal_types[byte][0]
            # simple objects
            if type == 'NULL':
                return pyNull(offset)
            elif type == 'NONE':
                return pyNone(offset)
            elif type == 'STOPITER':
                return pyStopIter(offset)
            elif type == 'ELLIPSIS':
                return pyEllipsis(offset)
            elif type == 'FALSE':
                return pyFalse(offset)
            elif type == 'TRUE':
                return pyTrue(offset)
            elif type == 'UNKNOWN':
                return pyUnknown(offset)
            # complex objects
            elif type == 'INT':
                i = self.r_long()
                return pyInt(offset, int(i.value), i.raw)
            elif type == 'INT64':
                lo4 = self.r_unsigned_long()
                hi4 = self.r_long()
                value = long(lo4.value + hi4.value * 4294967296L)
                return pyInt64(offset, value, lo4.raw + hi4.raw)
            elif type == 'LONG':
                i = self.r_type_long()
                return pyLong(offset, i.value, i.raw)
            elif type == 'FLOAT':
                s = self.r_s_string()
                return pyFloat(offset, float(s.value), s.raw)
            elif type == 'BINARY_FLOAT':
                f = self.r_float()
                return pyFloat(offset, f.value, f.raw)
            elif type == 'COMPLEX':
                real = self.r_s_string()
                img = self.r_s_string()
                value = complex(float(real.value), float(img.value))
                return pyComplex(offset, value, real.raw + img.raw)
            elif type == 'BINARY_COMPLEX':
                real = self.r_float()
                img = self.r_float()
                value = complex(real.value, img.value)
                return pyComplex(offset, value, real.raw + img.raw)
            elif type == 'INTERNED':
                tmpstr = self.r_string()
                self.InternedStringList.append(tmpstr)
                return pyInterned(offset, tmpstr.value, tmpstr.raw)
            elif type == 'STRING':
                s = self.r_string()
                print "RAW",s.raw
                return pyString(offset, s.value, s.raw)
            elif type == 'STRINGREF':
                i = self.r_long()
                value = self.InternedStringList[i.value].value
                return pyStringRef(offset, value, i.raw)
            elif type == 'UNICODE':
                tmpstr = self.r_string()
                value = tmpstr.value.decode('utf')
                return pyUnicode(offset, value, tmpstr.raw)
            elif type == 'TUPLE':
                t = self.r_tuple()
                return pyTuple(offset, t.value)
            elif type == 'LIST':
                return pyList(offset, list(self.r_tuple().value))
            elif type == 'DICT':
                d = self.r_dict()
                return pyDict(offset, d.value)
            elif type == 'SET':
                return pySet(offset, set(self.r_tuple().value))
            elif type == 'FROZENSET':
                return pyFrozenSet(offset, frozenset(self.r_tuple().value))
            elif type == 'CODE':

                return pyCode(offset, self.r_long(), self.r_long(),
                              self.r_long(), self.r_long(), self.r_object(),
                              self.r_object(), self.r_object(),
                              self.r_object(), self.r_object(),
                              self.r_object(), self.r_object(),
                              self.r_object(), self.r_long(),
                              self.r_object(), self.verboseDisasm,
                              self.xrefDisasm)
        else:
            raise ParseErrorException(self.p)

    def __init__(self, filename, offset=8, verboseDisasm=0, xrefDisasm=False, ):
        '''
        @param filename: name of the file to parse.
        @param offset:
            offset at which code object starts. Default is 8 to skip
            magic and timestamp.
        @param verboseDisasm: verbosity of the disassembler.
        @param xrefDisasm:
            wheather or not the disassembler should output xref
            information.
        '''
        self.p = offset
        self.verboseDisasm = verboseDisasm
        self.xrefDisasm = xrefDisasm
        self.indent = 0
        self.currentObject = None;
        self.InternedStringList = []
        

        try:
            self.file = open(filename, 'rb')
        except:
            raise IOErrorException('Cannot open file "' + filename + '".')
    
        try:
            self.data = self.file.read()
        except:
            raise IOErrorException('Cannot read file "' + filename + '".')
        
            
        self.co = self.r_object()
        if not isinstance(self.co, pyCode):
            #raise BadFirstObjectException()
            print "First object is not a code object?"

    def __del__(self):
        try:
            self.file.close()
        except:
            pass