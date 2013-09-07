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
UnPyc - program for disassembling and decompiling *.pyc files.

`./UnPyc -cVh`::

 --== Copyright ==--
 [The "BSD licence"]
 Copyright (c) 2008-2009 Dmitri Kornev
 All rights reserved.

 e-mail:  tswr@tswr.ru
 webpage: http://d.tswr.ru/

 --== Version ==--
 UnPyc v0.8.1 (testing)

 --== Help ==--
 Usage: UnPyc -D [ --debugDraw ] [ -q ] <filename>
        UnPyc -d [ -x ] [ -v ] [ -v ] [ -q ] <filename>
        UnPyc -g <filename>
        UnPyc [ -h ] [ -V ] [ -c ] [ -l ]

 Options:
   Decompilation:
     -D, --decompile    decompile
     --debugDraw        draw intermediate CFGs

   Disassembly:
     -d, --disassemble  disassemble
     -x, --xref         show basic blocks and xrefs
     -v                 verbose, use twice for more verbosity

   Common:
     -q, --quiet        don't print --== Disasm ==--, #--== Decompile ==--

   Gui:
     -g, --gui          gui (control flow graph)

   Info:
     -c, --copyright    copyright
     -l, --license      license
     -V, --version      version
     -h, --help         show this help message

'''

__version__ = '0.8.1'

import sys
import traceback
import optparse

import parse
import disasm
import decompile


__usage = 'Usage: %prog -D [ --debugDraw ] [ -q ] <filename>\n' \
      '       %prog -d [ -x ] [ -v ] [ -v ] [ -q ] <filename>\n' \
      '       %prog -g <filename>\n' \
      '       %prog [ -h ] [ -V ] [ -c ] [ -l ]'

__copyright = '--== Copyright ==--\n' \
              '[The "BSD licence"]\n' \
              'Copyright (c) 2008-2009 Dmitri Kornev\n' \
              'All rights reserved.\n\n' \
              'e-mail:  tswr@tswr.ru\nwebpage: http://d.tswr.ru/\n'

__license = '''--== LICENSE ==--
[The "BSD licence"]
Copyright (c) 2008-2009 Dmitri Kornev
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
    * Redistributions of source code must retain the above copyright
      notice, this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright
      notice, this list of conditions and the following disclaimer in the
      documentation and/or other materials provided with the distribution.
    * The name of the author may not be used to endorse or promote products
      derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE AUTHOR ''AS IS'' AND ANY
EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL Dmitri Kornev BE LIABLE FOR ANY
DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
'''

__version = '--== Version ==--\n' \
            'UnPyc v%s (testing)\n' % __version__

def start():
    '''Starts the unpyc application.'''

    def copyright(option, opt_str, value, parser, *args, **kwargs):
        print __copyright

    def license(option, opt_str, value, parser, *args, **kwargs):
        print __license

    def version(option, opt_str, value, parser, *args, **kwargs):
        print __version

    def help(option, opt_str, value, parser, *args, **kwargs):
        print '--== Help ==--'
        parser.print_help()
        print

    parser = optparse.OptionParser(usage=__usage, add_help_option=False)

    decompileGroup = optparse.OptionGroup(parser, 'Decompilation')
    decompileGroup.add_option('-D', '--decompile',
              action='store_true', dest='decompile', default=False,
              help='decompile')
    decompileGroup.add_option('--debugDraw',
              action='store_true', dest='debugDraw', default=False,
              help='draw intermediate CFGs')

    disasmGroup = optparse.OptionGroup(parser, 'Disassembly')
    disasmGroup.add_option('-d', '--disassemble',
              action='store_true', dest='disassemble', default=False,
              help='disassemble')
    disasmGroup.add_option('-x', '--xref',
              action='store_true', dest='xref', default=False,
              help='show basic blocks and xrefs')
    disasmGroup.add_option('-v',
              action='count', dest='verbose', default=0,
              help='verbose, use twice for more verbosity')

    commonGroup = optparse.OptionGroup(parser, 'Common')
    commonGroup.add_option('-q', '--quiet',
              action='store_true', dest='quiet', default=False,
              help='don\'t print --== Disasm ==--, #--== Decompile ==--')

    guiGroup = optparse.OptionGroup(parser, 'Gui')
    guiGroup.add_option('-g', '--gui',
              action='store_true', dest='gui', default=False,
              help='gui (control flow graph)')

    infoGroup = optparse.OptionGroup(parser, 'Info')
    infoGroup.add_option('-c', '--copyright',
              action='callback', callback=copyright,
              help='copyright')
    infoGroup.add_option('-l', '--license',
              action='callback', callback=license,
              help='license')
    infoGroup.add_option('-V', '--version',
              action='callback', callback=version,
              help='version')
    infoGroup.add_option('-h', '--help',
              action='callback', callback=help,
              help='show this help message')

    parser.add_option_group(decompileGroup)
    parser.add_option_group(disasmGroup)
    parser.add_option_group(commonGroup)
    parser.add_option_group(guiGroup)
    parser.add_option_group(infoGroup)

    (options, args) = parser.parse_args()

    if options.disassemble or options.decompile or options.gui:
        if len(args) != 1:
            parser.error('incorrect number of arguments')
        else:
            filename = args[0]
            try:
                parser = parse.Parser(filename, verboseDisasm=options.verbose,
                                      xrefDisasm=options.xref)
                disassembler = disasm.Disassembler(parser.co)
                optimizingDisassembler = disasm.Disassembler(parser.co,
                                                           optimizeJumps=True)
                decompiler = decompile.Decompiler(optimizingDisassembler,
                                                  options.debugDraw)
            except (parse.ParseErrorException,
                    parse.IOErrorException,
                    parse.BadFirstObjectException), p:
                print p
                sys.exit(-1)
            except:
                print '>>> Unexpected exception:'
                traceback.print_exc()
                sys.exit(-3)

            if options.disassemble:
                if not options.quiet: print '--== Disasm ==--'
                print disassembler.disassemble(),

            if options.decompile:
                if not options.quiet: print '# --== Decompile ==--'
                print decompiler.decompile(),

            if options.gui:
                try:
                    import gui
                    gui.App(disassembler).start()
                except ImportError:
                    print '>>> Cannot load gui. Please make sure that you ' \
                          'have python-tk installed on your system.'
                    sys.exit(-2)
    else:
        if args:
            parser.error('incorrect number of arguments')
        if len(sys.argv) == 1:
            help(None, None, None, parser)

if __name__ == '__main__':
    start()
