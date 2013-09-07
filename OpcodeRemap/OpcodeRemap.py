#!/usr/bin/env python
##WingHeader v1 
###############################################################################
## File       :  OpcodeRemap.py
## Description:  Determine the new opcode table for a remapped Python runtime
##            :  
## Created_On :  Tue Aug  3 20:27:49 2010
## Created_By :  Rich Smith
## Modified_On:  Wed Dec 22 05:35:26 2010
## Modified_By:  Rich Smith
## License    :  GPLv3 (Docs/LICENSE.txt)
##
## (c) Copyright 2010, Rich Smith all rights reserved.
###############################################################################
__author__ = "Rich Smith"
__version__= "0.5.1"

##Imports from the injected runtime
import os
import sys
import time
import os.path

try:
    import marshal
except: 
    print "[-] marshal module unavailable"

#TODO - decouple the dependence on unpyc / opcodes.py - must be decompiler independent
    
##All Exceptions are raised via this class
class OpcodeRemapError(Exception):
    def __init__(self, value):
        self.value = value
        
    def __str__(self):
        return repr("[-] %s"%self.value)
    

class OpcodeRemap:
    """
    Take two equivilent streams of python bytecode with different opcode
    maps and produce the new opcode map. sex.
    """      
    def __init__(self, ref_path, obf_path, output_dir ):
        """
        Give two func_code.co_code blobs and as much as the
        dict as is known so far and remap
        """
        ##Path to the pyb bytecode that has already been generated
        self.ref_path = ref_path
        self.obf_path = obf_path
        
        ##Base path to write the newly remapped opcde.py (stdlib) and opcodes.py (unPYC_)
        self.output_dir = output_dir
        
        ##Key - new opcode, value - orig opcode
        self.opcode_dict = {}    
        self.args_start_at = 255
        self.done_extended_arg = False
        ##stdlib opcode.py
        self.opcode_py   = """
# opcode module - potentially shared between dis and other modules which
# operate on bytecodes (e.g. peephole optimizers).


__all__ = ["cmp_op", "hasconst", "hasname", "hasjrel", "hasjabs",
           "haslocal", "hascompare", "hasfree", "opname", "opmap",
           "HAVE_ARGUMENT", "EXTENDED_ARG"]

cmp_op = ('<', '<=', '==', '!=', '>', '>=', 'in', 'not in', 'is',
        'is not', 'exception match', 'BAD')

hasconst = []
hasname = []
hasjrel = []
hasjabs = []
haslocal = []
hascompare = []
hasfree = []

opmap = {}
opname = [''] * 256
for op in range(256): opname[op] = '<%r>' % (op,)
del op

def def_op(name, op):
    opname[op] = name
    opmap[name] = op

def name_op(name, op):
    def_op(name, op)
    hasname.append(op)

def jrel_op(name, op):
    def_op(name, op)
    hasjrel.append(op)

def jabs_op(name, op):
    def_op(name, op)
    hasjabs.append(op)

# Instruction opcodes for compiled code
# Blank lines correspond to available opcodes

#ALERT THESE CODE ARE REMAPPED! Not for standard Python\n\n
"""
        self.opcode_py   = "# REMAPPED by pyREtic on %s "%(time.ctime()) + self.opcode_py
        ##UnPYC opcodes.py file
        self.opcodes_py  = "#!/usr/bin/python\n# REMAPPED by pyREtic on %s "%(time.ctime())
        self.opcodes_py  += """
        
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
"""
        self.opcodes_py_tail = r"""
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
"""

        
        
    
    def __call__(self):
        """
        Given two sets of bytecode produced from identical sourcecode but
        with different opcode maps determine which opcodes the shifted values
        relate to
        """
        ##Has remapping already occured ?
        try:
            os.stat(os.path.join(self.output_dir, "opcode_remap.py"))
            os.stat(os.path.join(self.output_dir, "opcodes_remap.py"))
            print "[-] Opcode remap files already exist for this project, delete them or start a new project"
            return False
        except:
            ##No remaps files found - all good
            pass
        
        try:
            ref_bytecodes = os.listdir(self.ref_path)
        except Exception, err:
            raise OpcodeRemapError("Problem getting bytecode for path '%s' - %s"%(self.ref_path, err))
            
        try:
            obf_bytecodes = os.listdir(self.obf_path)
        except Exception, err:
            raise OpcodeRemapError("Problem getting bytecode for path '%s' - %s"%(self.obf_path, err))
    
        ##Intersect common pyb files between the reference and obfuscated pythons
        common_bytecodes = list(set(ref_bytecodes).intersection(set(obf_bytecodes)))    
        
        print "[+] Remapping opcodes using %s:\n"%(common_bytecodes)
        for bc in common_bytecodes:
            
            f = open(os.path.join(self.ref_path, ref_bytecodes[ref_bytecodes.index(bc)]), "rb")
            data_ref = f.read()
            f.close()
            
            f = open(os.path.join(self.obf_path, obf_bytecodes[obf_bytecodes.index(bc)]), "rb")
            data_obf = f.read()
            f.close()
            
            print "[=] %s -> %s :"%(ref_bytecodes[ref_bytecodes.index(bc)], 
                              obf_bytecodes[obf_bytecodes.index(bc)]  )
            
            ##Quick Sanity check
            if len(data_ref) != len(data_obf):
                print "[-] Mismatch in byte stream lengths [ref: %x obf:%x]- skipping."%(len(data_ref), len(data_obf))
                continue
            
            self.compare_stream(data_ref, data_obf)
            
            print "[=] %d opcodes remapped out of a possible %s"%(len(self.opcode_dict),
                                                              len(opcode.opmap))
            
            
            
            if len(self.opcode_dict) >= len(opcode.opmap):
                print "[+] All opcodes remapped. Complete"
                break
       
        self.fill_unknowns()            
            
        print "[+] Generating opcode.py & opocdes.py based on remapped opcodes...."
        self.generate_files()
        
        return True

    
    def compare_stream(self, data_orig, data_new ):
        """
        Compare the byte streams and remap the bytes
        Python opcodes can be singular or take arguments, if they take arguments 
        then they will be followed by two bytes, the 2nd byte being the most sig
        
        The opcodes which take arguments are specified in the opcode module by the
        HAVE_ARGUMENT property
        """
        self.data_orig = data_orig
        self.data_new = data_new
        
        i = 0
        while i < len(self.data_orig):
            
            ##Does this opcode have an argument ? if so we skip the next two bytes
            if ord(self.data_orig[i]) >= opcode.HAVE_ARGUMENT:
                incrementor = 3
            else:
                incrementor = 1
            
            ##If they differ note the mapping if we haven't already
            if ord(self.data_orig[i]) not in self.opcode_dict.values():
                print "[%s]\t%s -> %s"%(opcode.opname[ord(self.data_orig[i])],
                                        ord(self.data_orig[i]), 
                                        ord(self.data_new[i]) )
 
                self.opcode_dict[ ord(self.data_new[i]) ] = ord(self.data_orig[i])
                
            else:
                ##Double check - has this opcode already been remapped but
                ## at a different value?
                if self.opcode_dict[ord(self.data_new[i])] != ord(self.data_orig[i]):
                    print "[-] OPCODE REMAP MISMATCH!! %s -> %s"\
                          %(ord(self.data_orig[i]), ord(self.data_new[i]))
                    print "[-] Abandoning this file as we cannot be sure if we are in sync"
                    return
                
            i += incrementor
            
    def fill_unknowns(self):
        """
        For opcode remappings produced by compare stream and values which have
        not had new values found for are mapped at the same value as the refernce
        
        This is basically a vast assumption, but if we haven't seen an opcode then
        we have no idea so steady state is as good a guess as any :)
        """
        steady_opcodes = []
        
        for oc in opcode.opmap.values():
            
            if not self.opcode_dict.has_key(oc) and oc not in self.opcode_dict.values():
                ##No existing key - 'remap' to the reference value
                self.opcode_dict[oc] = oc
                
                steady_opcodes.append(oc)
                
        print "[+] Number of opcodes maintained at original mapping: %s"%(len(steady_opcodes))
        print "\t %s"%(steady_opcodes)
        
        print "[+] Number of opcodes we have no idea about!: %s"%(len(opcode.opmap) - len(self.opcode_dict))
                    


    def generate_files(self):
        """"
        Generate out the opcode.py & opcodes.py files with the new opcode
        mappings in
        """        
        ##Order the new opcodes we are writing in ascending order
        new_opcode_list = self.opcode_dict.keys()
        new_opcode_list.sort()
        
        for oc in new_opcode_list:
            

            old_opcode_val = self.opcode_dict[oc]
            new_opcode_val = oc
            opcode_name    = opcode.opname[old_opcode_val]
       
            ##Write the new opcode.py as we go :)
            if old_opcode_val in opcode.hasname :
                self.opcode_py += "name_op('%s', %d)\n"%(opcode_name, new_opcode_val)
                
            elif old_opcode_val in opcode.hasjrel :
                self.opcode_py += "jrel_op('%s', %d)\n"%(opcode_name, new_opcode_val)
                
            elif old_opcode_val in opcode.hasjabs :
                self.opcode_py += "jabs_op('%s', %d)\n"%(opcode_name, new_opcode_val)
                
            else:
                self.opcode_py += "def_op('%s', %d)\n"%(opcode_name, new_opcode_val)
                
            if old_opcode_val in opcode.haslocal:
                self.opcode_py += "haslocal.append(%d)\n"%(new_opcode_val)
                
            elif old_opcode_val in opcode.hasconst:
                self.opcode_py += "hasconst.append(%d)\n"%(new_opcode_val)
            
            elif old_opcode_val in opcode.hascompare:
                self.opcode_py += "hascompare.append(%d)\n"%(new_opcode_val)
                
            elif old_opcode_val in opcode.hasfree:
                self.opcode_py += "hasfree.append(%d)\n"%(new_opcode_val)
                
            if opcode_name == "EXTENDED_ARG":
                self.opcode_py += "EXTENDED_ARG = %d"%(new_opcode_val)
                self.done_extended_arg = True
                
            if old_opcode_val >= opcode.HAVE_ARGUMENT:
                if (new_opcode_val) < self.args_start_at:
                    self.args_start_at = (new_opcode_val)
            
            ##And write the opcodes.py for UnPYC
            self.opcodes_py += "%s : ['%s', %d, '%s'],\n"%(new_opcode_val,
                                         opcode.opname[old_opcode_val],
                                         opcodes.opcodes[old_opcode_val][1],
                                         opcodes.opcodes[old_opcode_val][2].replace("'",'') )
            

        if not self.done_extended_arg:
            ##Add a default value
            #TODO 143 should not be static
            self.opcode_py += "EXTENDED_ARG = 143"
            
        self.opcode_py += "\nHAVE_ARGUMENT = %d"%(self.args_start_at)
                    
        self.opcode_py += "\ndel def_op, name_op, jrel_op, jabs_op\n"
        
        print "\n[+] %d opcodes remapped"%(len(self.opcode_dict))
        
        #print "\n[+] New opcode.py:\n<file>%s</file>"%(self.opcode_py)
        
        #print "\n[+] New opcodes.py:\n<file>%s</file>"%(self.opcodes_py+self.opcodes_py_tail)
        
        ##Does directory exist ? if not create it
        try:
            os.stat(self.output_dir)
        except:
            try:
                os.makedirs(self.output_dir)
            except Exception, err:
                print "[-] Error trying to access the specified output dir '%s' : %s"%(self.output_dir, err)
                return
        
        f1 = None
        try:
            f1 = open(os.path.join(self.output_dir, "opcode_remap.py"),"wb")
        except:
            print "[-] Could not open %s, aborting."%(os.path.join(self.output_dir, "opcode.py"))
            return False
        try:
            f2 = open(os.path.join(self.output_dir, "opcodes_remap.py"),"wb")
        except:
            print "[-] Could not open %s, aborting."%(os.path.join(self.output_dir, "opcode.py"))
            if f1:
                f1.close()
            return False
        
        f1.write(self.opcode_py)
        f2.write(self.opcodes_py+self.opcodes_py_tail)
        f1.close()
        f2.close()
        
        print "[+] opcode.py and opcodes.py written to %s"%(self.output_dir)

        return True
    

class GenerateBytecode:
    """
    Take the .py sourcecode from a standard Python distribution
    and compile it to bytecode, but NOT marshal it into a full .pyc.
    
    These raw byte code files are then dropped to disk to be used
    as an oracle to diff obfuscated bytecode against when you have
    some.
    
    For each version of Python (2.4, 2.5 ..) you only need to do this once
    """
    def __init__(self, py_version, pyb_dir, module_dir = None):
        """
        Set ourselves up
        """
        self.py_version = py_version
        
        ##Where are we outputting generated bytecode to
        self.ref_dir = os.path.join(pyb_dir, "ref_pyb")
        self.obf_dir = os.path.join(pyb_dir, "obf_pyb")
        
        ##Set of python modules to use as a source to generate pyb's
        self.module_dir = module_dir
        
            
    def __call__(self, reference = True):
        """
        Generate the pyb bytecode files
        
        We can run in two modes: Reference and Obfuscated
        
        Reference mode:
         This takes a standard Python module set and generates raw bytecode .pyb files
         from them and saves them to disk. 
         NOTE: Must be run in the context of a standard Python.
         
        Obfuscated mode:
         This takes the set of already generated reference Python .pyb files and tries to
         generate an equivilent set for the obfuscated Python
         NOTE: Must be run in the context of the obfuscated Python you want to crack.
         
        """
        if reference:
            print "[+] Generating reference .pyb's"
            self.gen_ref_pyb()
            
        else:
            print "[+] Generating obfuscated .pyb's"
            self.gen_obf_pyb()
            
    def get_pys(self):
        """
        Get all the .py's in the specified directory to build up an import set for
        testing normally point it at like: /usr/lib64/python2.5/
        
        Return a list of module names with the .py extension
        """
        #py_list = []
        py_dict = {}
        
        root_split = self.module_dir.split(os.path.sep)

        try:
            #TODO - proper recursive walk 
            #for f in os.listdir(self.module_dir):
            for path, dirs, files in os.walk(self.module_dir):
                
                if path != self.module_dir:
                    ##In a sub dir below the module root, split of the subdirs
                    ## so as we can qualify the 'import path' in the dict
                    sub_dir = "%s"%(os.path.sep).join( path.split(os.path.sep)[len(root_split):] )
                else:
                    ##For the root
                    sub_dir = ""

                py_dict[sub_dir] = []
                
                for f in files:

                    comp = os.path.splitext(f)
                    if comp[1] == ".pyc" or comp[1] == ".pyo":
                        #py_list.append(comp[0])
                        print "\t adding:",f 
                        #py_list.append(f)
                        py_dict[sub_dir].append(f)
                    
        except OSError, err:
            raise OpcodeRemapError("[-] Problem accessing python module directory: %s"%(err))
        
        return py_dict
     
    def compile_pys(self, dir_to_compile):
        """
        Make sure everything is compiled to bytecode
        """
        print "[+] Compiling all modules"
        compileall.compile_dir(dir_to_compile, force=1)
        
        
    def gen_ref_pyb(self):
        """
        NEEDS to be run from the standard Pythons context
        
        Generate a set of raw Python bytecode (.pyb) that will be used as a reference
        set against which to determine the obfuscated Pythons bytecode mapping.
        
        For all the modules in a specified path to a standard Python, compile them and
        save off the unmarshalled raw bytecode into a .pyb file.
        """ 
        ##recompile all modules in the specifed dir
        self.compile_pys(self.module_dir)        
            
        ##Get dictionary of modules available for reference
        self.mod_dict = self.get_pys()
        
        try:
            os.stat(self.ref_dir)
            print "[=] Overwriting existing .pyb directory"
        except OSError:
            try:
                print "[=] Making new .pyb directory"
                os.makedirs(self.ref_dir)
            except Exception, err:
                raise OpcodeRemapError("[-] Problem creating reference .pyb output directory '%s' : %s"%(self.ref_dir, err))
            
        ##Go through each module in the directory
        ref_list = []

        for mod_root in self.mod_dict.keys():
            
            for mod in self.mod_dict[mod_root]:
            
                try:
                    if mod_root == "":
                        dotted_root = ""
                        print "[=] importing %s"%(mod)
                        
                        m = __import__(mod.replace(".pyc",""))
                        print "[=] reading raw bytecode of %s"%(os.path.join(self.module_dir, mod_root, mod))
                    
                    else:
                        dotted_root = mod_root.replace(os.path.sep, ".")+"."
                        print "[=] importing %s.%s"%(dotted_root, mod)

                        m = __import__(dotted_root[:-1], globals(), 
                                       locals(), [mod.replace(".pyc","")], -1)
                        print "[=] reading raw bytecode of %s"%(os.path.join(self.module_dir, mod_root, mod))
                        
                    f = open(os.path.join(self.module_dir, mod_root, mod),"rb")
                    bc=f.read()
                    f.close()
                    co=marshal.loads(bc[8:])
    
                    if not co:
                        print "[-] code object empty"
                        continue
                    
                except Exception, err:
                    ##Not fatal
                    print "[-] Error importing/reading file: %s"%(err)
                    continue 
                
                ref_list += dotted_root+mod
                try:
                    bc_file = open(os.path.join(self.ref_dir, dotted_root+mod.replace("pyc","pyb")), "wb" )
                except:
                    ##Bad perms on file ?
                    raise OpcodeRemapError( "[-] Cannot open file to write .pyb to?" )
    
                ##For each module list it's functions, get their bytecode and concat
                ## into a file in order so it contains all the bytecode from the 
                ## functions in that module
                bc_file.write(co.co_code)
    
                for func in dir(m):
            
                    f_obj = eval("m.%s"%(func))
                    
                    if inspect.isfunction(f_obj):
                        bc_file.write(f_obj.func_code.co_code)
                    
                    elif inspect.ismethod(f_obj):
                        bc_file.write(f_obj.im_func.func_code.co_code) 
                
                bc_file.close()
            
                  
        print "[+] %d reference .pyb's generated."%(len(ref_list))
        print "[+] .pyb's written to %s"%(self.ref_dir)
        
        return ref_list
            
            
    def gen_obf_pyb(self):
        """    
        NEEDS to be run from the obfuscated Pythons context
        
        For every module in the set of reference Python modules that we were able to
        compile to bytecode for, we attempt to import the equivilent module from the 
        obfuscated Python.
        
        Once they are imported we can access the bytecode objects of each function in
        the module and create a .pyb file from them, as we did for the ref Python modules.
        
        The upshot being we have two sets of bytecode in .pyb format over the same set
        of Python source modules. We can then diff them to determine the new opcode map.
        """
        try:
            os.stat(self.obf_dir)
            print "[=] Overwriting existing .pyb directory"
        except:
            try:
                os.makedirs(self.obf_dir)
            except Exception, err:
                raise OpcodeRemapError("[-] Problem creating obfuscated .pyb output directory '%s' : %s"%(self.ref_dir, err))
    
        ##Build list of modules for which we have generated reference bytecode pyb's
        obf_list = []
        try:
            for f in os.listdir(self.ref_dir):
                obf_list.append( f )
                
        except OSError, err:
            raise OpcodeRemapError("Error accessing the reference bytecode file set - have reference pyb's been generated yet?")
           
        ##For each reference module we have previously constructed bytecode for lets get
        ## the equivilent module in the running obfuscated pythons context
        phail_list = []
        
        ##Need to adjust the python path so modules in the specified obfucation dir
        ## load in preference to all else
        save_path = sys.path
        sys.path  = [self.obf_dir]
        
        for f_name in obf_list:
            
            mod_name = f_name.replace(".pyb","")
            try:
                ##Import module for object interogation
                if "." in mod_name:
                    ##Do a 'from foo.bar import baz' construct
                    dotted_root = mod_name[:mod_name.rfind(".")]
                    m = __import__(dotted_root, globals(), locals(), [mod_name[mod_name.rfind(".")+1:]], -1)
                else:
                    ##Do a 'import foo' construct
                    m = __import__(mod_name)
                    dotted_root = ""
                              
                
            except Exception, err:
                ##Not fatal, we expect a few of these
                phail_list.append(f_name)
                continue
            
            ##For each module we can import we access each of the constituent
            ## functions bytecode and concat that into a new .pyb file.
            try:
                bc_file = open(os.path.join(self.obf_dir, f_name), "wb" )
            except:
                ##Bad perms on file ?
                raise OpcodeRemapError( "[-] Cannot open file to write .pyb to?" )
            
            try:
                ##Read module level code object
                f = open(os.path.join(self.module_dir, mod_name.replace(".", os.sep)+".pyc"),"rb")
                bc=f.read()
                f.close()
                co=marshal.loads(bc[8:])
                if not co:
                    print "[-] code object empty"
                    continue
                
                ##module bytecode 
                bc_file.write(co.co_code)
                
            except Exception, err:
                ##Not fatal, we expect a few of these
                phail_list.append(f_name)
                continue
                
            
            #TODO call into the liveunpyc object walker to get code objects but no decompile
            for func in dir(m):
                f_obj = eval("m.%s"%(func))
                
                if inspect.isfunction(f_obj):
                    bc_file.write(f_obj.func_code.co_code)
                    
                elif inspect.ismethod(f_obj):
                    bc_file.write(f_obj.im_func.func_code.co_code) 
            
            bc_file.close()
            
        ##Restore sys path
        sys.path = save_path
            
        ##Now lets remove the ref modules from the list that we couldn't import for
        ## whatever reason so we have a list of bytecodes that are common to both
        obf_list = list(set(obf_list).difference(set(phail_list)))
        
        print "[+] %d equivilent .pyb's generated/."%(len(obf_list))
        print "[+] .pyb's written to %s"%(self.obf_dir)
        return obf_list

                
        


##Convenience functions to call from interactive sessions / pdb
def gen_ref(pyb_dir, ref_dir, version):
    """
    RUN FROM STANDARD RUNTIME
    Generate reference bytecode into a .pyb form, this will be used to generate
    and diff against the obfuscated .pyb's
    
    pyb_dir - where to dump pyb's to
    ref_dir - where referecnce modules are located to generate pyb's from
    version - major/minor version of python (2.5, 2.6 etc)
    """
    try:
        gb = GenerateBytecode(py_version = version, pyb_dir = pyb_dir, module_dir = ref_dir)
        gb(reference = True)
    except OpcodeRemapError, err:
        print err
    except Exception, err:
        print "[-] UNHANDLED exception:"
        print "\t%s"%(err)
        

def gen_obf(pyb_dir, obf_dir, version):
    """
    RUN FROM OBFUSCATED RUNTIME
    Generate pyb's for an obfuscated runtime against previously generated reference bytecode
    
    pyb_dir - where to dump pyb's to
    obf_dir - directory from which to read the obfuscated .pyc's from
    version - major/minor version of python (2.5, 2.6 etc)     
    """
    try:
        gb = GenerateBytecode(py_version = version, pyb_dir = pyb_dir, module_dir = obf_dir)
        gb(reference = False)
    except OpcodeRemapError, err:
        print err
    except Exception, err:
        print "[-] UNHANDLED exception:"
        print "\t%s"%(err)

        
def remap(ref_dir, obf_dir, output_dir = "/tmp"):
    """
    Diff the pyb format bytecode and create new opcode map files
    """
    oc = OpcodeRemap(ref_dir, obf_dir, output_dir)
    oc()
    
    
if __name__ == "__main__":
    
    ##As the remapping operations often happen in their own process so as a specific python
    ## version can be used to generate reference bytecode - see REpdb.ref_gen
    
    if len(sys.argv) < 3:
        print "[-] Non enough argumentsd supplied for reference remapping"
        print "   OpcodeRemap.py <python version> <pyb dum dir> <modules to reference>"
        sys.exit(-1)
        
    print "[+] Reference generation mode"
    import compileall, inspect
    
    gen_ref(sys.argv[2], sys.argv[3], sys.argv[1])
        
        
else:
    ##Being called/imported from another module - likely REpdb

    import inspect
    import compileall
    import opcode
    import traceback
    
    from Decompilers.unpyc import opcodes_std as opcodes

    