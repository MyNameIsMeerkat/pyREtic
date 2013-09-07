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
Module for text processing.

'''

import re

INDENT = '\t'
ASM_INDENT = '    '
ASM_INDENT2 = '         '

# from decompile
def d_indentText(text, depth):
    r = re.compile('^(?=.)', re.M)
    return r.sub(INDENT * depth, text)

def d_ind(curIndent):
    return INDENT * curIndent

# from parse
def showoffset(offset):
    '''
    @return: '%.8X' % offset.
    @param offset: integer.

    '''
    return '%.8X' % offset

def p_indent(depth, offset=-1):
    '''
    @param depth: number of whitespaces.
    @param offset: integer.
    @return: string of whitespaces with or without offset.

    '''
    r = ''
    if offset != -1:
        r += showoffset(offset) + ' '
    else:
        r = ASM_INDENT2
    r += ASM_INDENT * depth
    return r

def p_indentText(text, depth):
    '''Add indentation to text block.'''

    r = re.compile('^(?=.)', re.M)
    return r.sub(p_indent(depth), text)

def narrowText(text):
    '''Narrows the Text to width=50.'''

    i = 0
    r = ''
    while i < len(text):
        r += text[i:i+50] + '\n'
        i += 50
    return r

def shorten(s):
    '''Trancation to 35 chars.'''

    # better to use multiple of 3 minus 1
    sh = 12
    shortento = sh * 3 - 1;
    if (isinstance(s, str) or isinstance(s, unicode)) and len(s) > shortento:
        return s[0:shortento] + '...'
    return s

def dropNewLines(text):
    '''Removes '\n' from the text.'''

    r = re.compile('\n')
    return r.sub('', text)

# from structure
def s_indentExText(text):
    depth = 1
    skip = 1
    if text == '': text = 'pass\n'
    list = text.split('\n')

    if len(list) >= 1:
        if list[0][0] == '#': list[0] = list[0][1:] + ':'
        else: list = [':'] + list
    index = skip
    while index < len(list):
        # TODO: use common indent variable
        if list[index] != '': list[index] = INDENT * depth + list[index]
        index += 1
    return '\n'.join(list)

def s_indentText(text, depth, skip=0):
    list = text.split('\n')
    index = skip
    while index < len(list):
        # TODO: use common indent variable
        if list[index] != '': list[index] = INDENT * depth + list[index]
        index += 1
    return '\n'.join(list)

def s_indentForText(text):
    skip = 1
    depth = 1
    list = text.split('\n')
    if len(list) == 2 and list[1] == '':
        list[1] = 'pass'
    index = skip
    while index < len(list):
        # TODO: use common indent variable
        if list[index] != '': list[index] = INDENT * depth + list[index]
        index += 1
    return '\n'.join(list)