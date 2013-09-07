#!/usr/bin/env python
##WingHeader v1 
###############################################################################
## File       :  liveUnPYC.py
## Description:  Superclass of UnPyc functionality to allow the decompilation
##            :  of raw code objects in memory rather than pyc's on disk
## Created_On :  Tue Aug  3 20:28:36 2010
## Created_By :  Rich Smith
## Modified_On:  Wed Dec  8 18:33:20 2010
## Modified_By:  Rich Smith
## License    :  GPLv3 (Docs/LICENSE.txt)
##
## (c) Copyright 2010, Rich Smith all rights reserved.
###############################################################################

##This is wrapper functionality around the core decompiler UnPyc which is written
## by Dmitri Kornev and available from http://unpyc.sourceforge.net
## At the time of writing the latest version was 0.81

#Refs
#http://docs.python.org/reference/datamodel.html
try:
    ##Current runtime's modules
    import sys      ##builtin
    import marshal  ##c module
    
    ##Module from the projects lib - corresponding to the projects version number
    import inspect
    import traceback
    import types
    
except ImportError, err:
    print "[-] Problem importing required module: %s"
    

##From UnPyc 
from Decompilers.unpyc import parse
from Decompilers.unpyc import disasm
from Decompilers.unpyc import decompile

class CoParser:
    """
    An equivilent to the Parser class in the parse module where rather than
    parsing marshalled code objects we parse a raw code object.
    The result being the creation of a PyCode object that UnPYC can
    then do it's magic on
    """
    
    def r_tuple(self, obj):
        """
        Construct a PyTuple object from an existing tuple with each member
        being set as a valid Py* type as well, so e.g. a PyTuple of
        PyStrings
        """
        py_tuple = []
        for item in obj:
            ##For each item in the tuple find it's type and create the
            ## corresponding Py* type
            py_tuple.append( self.r_object(item) )
            
        return parse.pyTuple( 0, tuple(py_tuple) )
    
    def r_code(self, obj):
        
        #print "[*] argcount"
        argcount  = parse.pyLong(0, long(obj.co_argcount),  "NA")
        #print "[*] nlocals"
        nlocals   = parse.pyLong(0, long(obj.co_nlocals),   "NA")
        #print "[*] stacksize"
        stacksize = parse.pyLong(0, long(obj.co_stacksize), "NA")
        #print "[*] flags"
        flags     = parse.pyLong(0, long(obj.co_flags),     "NA")
        #print "[*] code"
        code = parse.pyString(0, obj.co_code, "NA")
        #print "[*] consts"
        consts = self.r_object(obj.co_consts)
        #print "[*] names"
        names = self.r_object(obj.co_names)
        #print "[*] varnames"
        varnames = self.r_object(obj.co_varnames)
        #print "[*] freevars"
        freevars = self.r_object(obj.co_freevars)
        #print "[*] cellvars"
        cellvars = self.r_object(obj.co_cellvars)
        #print "[*] filename"
        filename = parse.pyString(0, obj.co_filename, "NA")
        #print "[*] name"
        name = parse.pyString(0, obj.co_name, "NA")
        #print "[*] firstlineno"
        firstlineno = parse.pyLong(0, long(obj.co_firstlineno), "NA")
        #print "[*] lnotab"
        lnotab = parse.pyString(0, obj.co_lnotab, "NA")
        
        return parse.pyCode(0, argcount, nlocals,
                              stacksize, flags, code,
                              consts, names,
                              varnames, freevars,
                              cellvars, filename,
                              name, firstlineno,
                              lnotab, self.verboseDisasm,
                              False)
    
    def r_object(self, obj):
        
        
        if type(obj) == types.StringType:
            return parse.pyString(0, obj, "NA")
        
        elif type(obj) == types.UnicodeType:
            return parse.pyUnicode(0, obj, "NA")
            
        elif type(obj) == types.NoneType:
            return parse.pyNone(0)
            
        elif type(obj) == types.IntType:
            return parse.pyLong(0, long(obj), "NA")
            
        elif type(obj) == types.FloatType:
            return parse.pyFloat(0, float(obj), "NA")
            
        elif type(obj) == types.TupleType:
            return self.r_tuple(obj)
        
        elif type(obj) == types.CodeType:
            return self.r_code(obj)
            #return parse.pyString(0, obj.co_code, "NA")
            
        else:
            print "UNKNOWN DATA TYPE: %s"%(type(obj))  
            
    
    def __init__(self, code_obj, verboseDisasm=False):
        """
        Pass in an unmarshalled code object for decompilation
        """
        
        self.verboseDisasm = verboseDisasm
        #TODO - generalise, make the functions below find the code obect
        #self.co = self.r_code(obj.func_code)
        self.co = self.r_code(code_obj)
        self.verbose = False
        


#TODO - generators, decorators
class liveUnPYC(object):
    """
    Traverse an object either in memory or from filesystem
    and decompile back to source through accessing code objects
    rather than .pyc files
    
    Relies on the UnPyc decompiler: http://unpyc.sourceforge.net/
    
    top_level_object - the object that will be treated as parent, anything
                           not parented by this module will not be traversed
                           stops you diving down rabbit holes with 
                           'from foo import *'
                           
                        Leave as None is you want to recurse
    """

    
    def __init__(self, pyretic, top_level_module = None, verbose = True, debug = True):
        
        ##The pyREtic instance
        self.pyretic = pyretic
        
        ##The name of the module we are decompiling - stops us going into
        ## objects imported to our top level name space e.g. from foo import *
        #TODO #__package__ ?
        self.top_level_module = top_level_module
        
        #TODO
        ##Source code derived from our objects
        self.source_code      = ""
        
        #TODO - do proper deindent
        ##Current indentation level - increased / decreased by code below
        self.indent = 0
           
        self.verbose = verbose
        self.debug   = debug

                
    def set_top_level_module(self, mod_name):
        
        self.top_level_module = mod_name
                
        
    def fs_decompile(self, mod_name):
        """
        Take an obfuscated .pyc file and decompile by grabbing the bytecode
        and unmarshaling with the obfuscating Python runtimes own marshalling code
        
        The opcode remapping must already have taken place
        
        If you have access to to files/filesystem and the runtime allows you
        access to it's marshaller module use this, you will get the best output
        """
        ##Open obfusated file read in binary data
        try:
            mod_f  = open(mod_name,"rb")
        except Exception, err:
            print "[-] Problem opening module '%s' : %s"%(mod_name, err)
            return ""
        try:
            obf_bc = mod_f.read()
        except Exception, err:
            mod_f.close()
            print "[-] Problem reading module '%s' : %s"%(mod_name, err)
            return ""
        
        ##Skip magic & time stampe (first 8 bytes) & unmarshel the series of 
        ## code objects
        ##IF THE MARSHALLER HAS CHANGED YOU MUST USE THAT MARSHALER 
        try:
            co=marshal.loads(obf_bc[8:])
        except Exception, err:
            mod_f.close()
            print "[-] Problem unmarshaling module '%s' : %s"%(mod_name, err)
            return ""
            
        
        #if self.debug:
        #    raw_input("Decompiling: %s, Any key to proceed.... "%mod_name)

        self.source_code = self._decompile(co, identity = "%s-%s"%(co.co_filename, co.co_name))

        return self.source_code

    
    def mem_decompile(self, obj):
        """
        Take an object & interogate it, do both decompilation of code objects
        and source code reconstruction from live interactive querying
        
        obj - Python object to interogate for decompilation back to source
        
        """        
        try:
            self.source_code = self.get_py(obj)
        except:
            ##Top level unexpected exception handler .... decompiler not perfect!
            import traceback
            
        return self.source_code
    

    #TODO - ordering of: Imports, constants, classes, functions, 
    def get_py(self, obj, indent = 0):
        """
        Determine the type of python object that has been passed and 
        as appropriate call a sub function to access the code object
        and decompile that back to source
        
        Called recursively
        """
        print "[+] Object: ",obj,type(obj)
        exclude_list = ["__builtins__","__class__", "__objclass__"] #__objclass__

        ##The source code generated from this depth
        source_str = ""
            
        ##if the object passed in is not from the module we have set as top 
        ## level then skip it - stops us recursing off into from x imports
        if hasattr(obj, "__module__") and self.top_level_module:
            if obj.__module__ != self.top_level_module:
                # TODO detect the from foo import bar 'as' blah
                # TODO from imports on functions ---- don't think this is possible
                print "[-] NOT recursing into %s module"%(obj.__module__)
                
                return ""
            
        ##Now find what type of objects we have & traverse to the code objects   
        
        ##First look at top level instances - not really decompilation, more
        ## reconstruction from artefacts and analysis at run time
        #TODO seperate import analsysis from this
        source_str += self.get_instances(obj, indent)
            
        ##Find and decompile all class objects (and their members)
        for name, class_obj in inspect.getmembers(obj, inspect.isclass):
            
            if name in exclude_list:
                continue
            print "[+] Class %s found...."%(name)
            print "from file %s"%(class_obj.__module__)
            
            ##Get documentation
            doc = self.get_doc(class_obj, indent+1)
            
            if self.top_level_module and class_obj.__module__ != self.top_level_module:
                
                print "[-] NOT recursing into %s module"%(class_obj.__module__)
                
                ##Must ? be a from foo import bar construct ?
                source_str += "from %s import %s\n"%(class_obj.__module__, 
                                                    class_obj.__name__)
      
                continue
            
            ##Get members of the class recursively
            content    = self.get_class(class_obj, indent + 1)
            if not content.strip():
                content = "\n%spass\n"%((indent+1)*"\t")
            superclasses = class_obj.__bases__
            if not superclasses:
                source_str += "class %s:\n"%(name)
            else:
                source_str += "class %s("%(name)
                for x in superclasses:
                    source_str += "%s, "%(x.__name__)
                ##remove final comma
                source_str = source_str[:-2]    
                source_str += "):\n"
    
            source_str += doc
            
            ##Get top class level attributes/instances
            source_str += self.get_instances(class_obj, indent+1)
            
            source_str += content + "\n\n"
        
        ##Find and decompile all method objects
        for name, method in inspect.getmembers(obj, inspect.ismethod):
            
            if name in exclude_list:
                continue
            print "[+] Method %s found...."%(name)
            
            ##Get the code from the method & its arguments
            content = self.get_method(method, indent + 1) 
            source_str += "%sdef %s(%s):\n"%("\t"*indent, name, self.get_args(method)) 
            
            ##Get documentation
            source_str += self.get_doc(method, indent+1)
            
            source_str += content + "\n\n"
            
        ##Find and decompile all function objects
        for name, function in inspect.getmembers(obj, inspect.isfunction):
    
            if name in exclude_list:
                continue
            print "[+] Function %s found...."%(name)
    
            ##Get the code from the function
            content = self.get_func(function, indent + 1) 
            source_str += "%sdef %s(%s):\n"%("\t"*indent, name, self.get_args(function))
            
            ##Get documentation
            source_str += self.get_doc(function, indent+1)
            
            source_str += content + "\n\n"

        return source_str
    
    
    
    def get_instances(self, obj, indent):
        """
        Get all top level instances into a usable string form, do not show builtins etc
        
        http://docs.python.org/reference/datamodel.html
        """
        exclude_list =  ["__builtins__", "__name__", "__file__", "__class__", 
                         "__package__",  "__doc__", "__module__"]

        
        #TODO - how to get invocation args ?
        #       instances from other modules ?
        #       import 'from' and 'as' - must move to top of file (return as sep)
        # 
        # decorators
        # nested functions ?
        # De-indent ?
        # Lambdas
        #globals ?
        
        instances = ""
        pad = "\t"*indent
        
        #TODO compensate for __slots__
        if not hasattr(obj, "__dict__"):
            print "[-] %s has no __dict__"%(obj)
            return ""
        
        #http://mypythonnotes.wordpress.com/2008/09/04/__slots__/
        
        for inst, val in obj.__dict__.items():
            
            ##Exclude types that we decompile elsewhere or that are things
            ## that don't show up in the source & reflect the underlying objects
            if inst in exclude_list or\
               inspect.isfunction(val) or\
               inspect.ismethod(val) or\
               inspect.isclass(val) or\
               inspect.isbuiltin(val) or\
               inspect.ismethoddescriptor(val) or\
               inspect.isgetsetdescriptor(val) or\
               inspect.isdatadescriptor(val) or\
               inspect.ismemberdescriptor(val):
                continue
            
            ##If it's a generator find out which one - only available in > 2.6
            elif sys.version_info[0] == 2 and sys.version_info[1] >5 and inspect.isgenerator(val):
                instances += "%s%s = %s()\n"%(pad, inst, val.__name__)
                
            
            elif inspect.ismodule(val):
                #MUST be a better way than this ?
                module_name = str(val).split(" ")[1].replace("'","")
                #
                instances += "import %s\n"%(module_name)
                                            
            ##Things that eval true as new/old class here but false for isclass
            ## above are class invocations
            elif self._is_new_style_class(val) :
                #MUST be a better way than this ?
                instance_of_name = str( type(val) ).split(" ")[1].replace(">","").replace("'","").replace("<","")
                parent_names = instance_of_name.split(".")
                if obj.__name__ == parent_names[0]:
                    instance_of_name = '.'.join(parent_names[1:])
                
                instances += "%s%s = %s()\n"%(pad, inst, instance_of_name)
                print inst,val,type(val), dir(val)
                print "new",self._is_new_style_class(val)
                #TODO - put the repr i.e. str(val) in the comments after ?
                #raw_input("+=+=+=+= %s%s = %s() #!ARGS UNKNOWN!\n"%(pad, inst, instance_of_name))
                
            elif self._is_old_style_class(val) or type(val) == types.InstanceType:
                instance_of_name = str( str(val) ).split(" ")[0].replace(">","").replace("<","")
                parent_names = instance_of_name.split(".")
                if obj.__name__ == parent_names[0]:
                    instance_of_name = '.'.join(parent_names[1:])
                
                instances += "%s%s = %s()\n"%(pad, inst, instance_of_name)
                print inst,val,type(val), dir(val)
                print "old",self._is_old_style_class(val)
                #TODO - put the repr i.e. str(val) in the comments after ?
                #raw_input("+=+=+=+= %s%s = %s() #!ARGS UNKNOWN!\n"%(pad, inst, instance_of_name))
                
            else:
                ##Variable a=1 or whatever
                print "++++++",val,type(val)
                if type(val) == types.StringType:
                    if "\n" in val or "\r" in val:
                        val = '"""%s"""'%(val)
                    elif "'" in val:
                        val = '"%s"'%(val)
                    else :
                        val = "'%s'"%(val)
                
                instances += "%s%s = %s\n"%(pad, inst, val)
            
        return instances+"\n"
    
    def get_doc(self, obj, indent):
        """
        My get doc function - wraps the inspect modules getdoc
        but adds in indentation and triple quotes so we can drop into
        a code listing
        """
        docstring = inspect.getdoc(obj)
        if docstring:
            pad = '\n%s'%(indent*"\t")
            idoc = indent*"\t" + pad.join( docstring.strip().split("\n") )
            return '%s"""\n%s\n%s"""\n'%(indent*"\t", idoc, indent*"\t")
        else:
            return ""
        
    def get_args(self, obj):
        """
        get the argument spec for a function / method
        """
        print "GETTING ARGS FOR",obj,type(obj)
        arg_spec = inspect.getargspec(obj)
    
        if arg_spec[3]:
            args_with_defaults = arg_spec[0][-len(arg_spec[3]):]
            default_pairs = zip(args_with_defaults, arg_spec[3])
        else:
            default_pairs = []
                                
        arg_str = ""
        if len(default_pairs) > 0:
            arg_str += ', '.join(arg_spec[0][:len(default_pairs)-1])
                
            #TODO respec to a .join logic
            for def_pair in default_pairs:
                arg_str += ", %s=%s"%(def_pair[0], def_pair[1])
        else:
            arg_str += ', '.join(arg_spec[0])
            
            
        if arg_spec[1]:
            print "2",arg_spec[1]
            arg_str += ", *%s"%(arg_spec[1])
    
        if arg_spec[2]:
            print "3",arg_spec[2]
            arg_str += ", **%s"%(arg_spec[2])
            
        return arg_str           
        
    def get_class(self, obj, indent):
        """
        Breaks a class into it's consituents: variables, functions etc
        """
        #TODO get SUPERCLASSES, decorators ? 
        ##Call back into get_py to get the components of the class object, 
        ## classes in this sense are just a non top level container
        source = self.get_py(obj, indent)
        print "CLASS",obj.__name__
        #raw_input()
        return source
    
        
    def get_method(self, obj, indent):
        """
        Get access to the function object in a method
        """
        m_identity = "%s.%s"%(obj.im_class, obj.__name__)
        print "METHOD",m_identity
        source = self.get_func(obj.im_func, indent, m_identity)

        if self.verbose:
            print "[+]Method code:%s"%(source)
        
        return source
    
    
    def get_func(self, obj, indent, identity = ""):
        """
        Decompiles an instantiated Python function object from
        """
        if not identity:
            identity = obj.__name__
            
            print  "FUNCTION:",identity
        
        source_code = self._decompile(obj.func_code, identity)

        if source_code:
            source_code = source_code.strip()
            source_code = source_code.strip("\n")
            source_code = source_code.strip("\r")
            pad = '\n%s'%(indent*"\t")
            return indent*"\t" + pad.join( source_code.split("\n") )
        else:
            return ""
        
    def get_generator(self, obj, indent):
        """
        Decompiles a generator object
        """
        source_code = self._decompile(obj.gi_code)
        
        if source_code:
            source_code = source_code.strip()
            source_code = source_code.strip("\n")
            source_code = source_code.strip("\r")
            pad = '\n%s'%(indent*"\t")
            return indent*"\t" + pad.join( source_code.split("\n") )
        else:
            return ""
    
    
    def _decompile(self, code_obj, identity, verbose = False):
        """
        Do the in memory decompilation
        """
        print "[=] Decompiling %s"%(identity)
       
        try:
            #parser = parse.Parser(f_code, raw=True)
            print "[+] Parsing code object of %s"%(code_obj)
            parser = CoParser(code_obj, verboseDisasm=verbose)
            print "[+] Disassembling.... "
            optimizingDisassembler = disasm.Disassembler(parser.co,
                                                       optimizeJumps=True)
            print "[+] Decompiling.... "        
            decompiler = decompile.Decompiler(optimizingDisassembler)
            
        #TODO - try and get code that was decompiled before error
        except (parse.ParseErrorException,
                parse.IOErrorException,
                parse.BadFirstObjectException), err:
            print err
            return ""
        
        except:
            print '>>> Unexpected exception:'
            traceback.print_exc()
            return ""
    
        sc = decompiler.decompile()

        return sc
    
    
    def _is_new_style_class(self, cls):
        """
        Check to see if this is a new style class
        """
        return hasattr(cls, '__class__') \
               and ('__dict__' in dir(cls) \
               or hasattr(cls, '__slots__'))
    
    
    def _is_old_style_class(self, cls):
        """
        Check to see if this is a old style class
        """
        return hasattr(cls, '__class__') \
               and type(cls) == types.InstanceType
        
    
    
    







