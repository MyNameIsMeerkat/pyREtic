#!/usr/bin/env python
##WingHeader v1 
###############################################################################
## File       :  REpdb.py
## Description:  pyREtic extensions to the standard Python debugger (pdb)
##            :  focussing on use for reverse engineering bytecode/vuln hunting
## Created_On :  Tue Aug  3 20:24:32 2010
## Created_By :  Rich Smith
## Modified_On:  Wed Dec 22 05:41:31 2010
## Modified_By:  Rich Smith
## License    :  GPLv3 (Docs/LICENSE.txt)
##
## (c) Copyright 2010, Rich Smith all rights reserved.
###############################################################################
__author__ = "Rich Smith"
__version__= "0.5.1"

##Use libs we control in preference to the packed runtime's
import sys
import os.path
##Allows easy relative writes to the location this dir later
MODULE_LOCATION = os.path.dirname(__file__)
sys.path = [os.path.join(MODULE_LOCATION, "Projects", "default", "libs")] + sys.path

##Imports
import os
import pdb
import time
import struct
import atexit
import shutil
import urllib
import tarfile
import subprocess


##Third party imports for extra functionality in the debugger context
try:
    from ThirdParty import pycallgraph
    CAN_CALLGRAPH = True
except:
    CAN_CALLGRAPH = False

#TODO - CONFIG FILE WITH ALL THIS STUFF IN & make OS specific
RUNTIME_LOCATION = {"2.4" : "/usr/bin/python2.4",
                    "2.5" : "/usr/bin/python2.5",
                    "2.6" : "/usr/bin/python2.6",
                    "2.7" : "/usr/bin/python2.7"
                    }

##pyREtic modules
import pyREtic

class REpdb(pdb.Pdb):
    """
    Extended pdb debugger with functionality useful when reverse engineering
    Python .pyc/.pyo files without the .py source 
    """
    def __init__(self, completekey='tab', stdin=None, stdout=None):

        ##initiate Pdb
        pdb.Pdb.__init__(self, completekey, stdin, stdout)

        global MODULE_LOCATION

        ##Locations of reference/obfuscated .pyb's
        self.ref_pyb = None
        self.obf_pyb = None
        
        self.runtime_version = "default"

        self.pyretic = pyREtic.pyREtic()

        ##Get default project name from pyREtic
        self.projectdir = self.pyretic.get_projectroot()

        self.ref_pyb_generated = False
        self.callgraph_started = False
        self.cg_exclude = ['pycallgraph.*']
        self.do_module_restore = False
        
        self.runtime_remapped = False
        self.remap_complete()

        self.prompt = '(REpdb:%s) '%(self.pyretic.get_project())
        
        print "\n%s\nREpdb is part of the pyREtic toolkit. %s 2010\n%s\n"%("="*53, __author__, "="*53)    
    
        
    def __reload_modules(self):
        """
        This function reloads all the modules in the libs dir of the project that
        has been switched to + some other modules that require it. 
        
        *Don't mess with this as it can introduce subtle bugs that are annoying to debug*
        """
        ##Ordered reload
        must_reload = ["opcode", "dis", "opcodes"]
     
        for mr in must_reload:

            try:
                exec("%s = reload(%s)"%(mr, mr))
                #print "[+] Reloaded '%s'"%(mr)
                
            except Exception, err:
                #print "[-] Problem reloading '%s' : %s"%(mr, err)
                pass
        
        ##Unordered reload
        lib_modules = os.listdir(self.pyretic.get_project_mod_dir())
        
        for m in lib_modules:
            
            if m not in must_reload and m != "__init__.py":
                
                mod_name, ext = os.path.splitext(m)
                
                if ext != ".py":
                    #print "[-] none .py '%s' in project directory, skipping"%(m)
                    continue
                try:
                    exec("%s = reload(%s)"%(mod_name, mod_name))
                    #395print "[+] Reloaded '%s'"%(mod_name)
                    
                except Exception, err:
                    #print "[-] Problem reloading '%s' : %s"%(mod_name, err)
                    pass
                
        
    def do_show(self, args):
        """
        Print out all the current settings for this REpdb project
        
        Usage: show
        """

        
        self.do_is_remapped()
        
        print """
        Current project name:        %s
        Current project directory:   %s
        Project runtime set as:      %s  
        
        Decompiler:                  %s
        
        Python paths:                %s
        
        Runtime opcode remapped:     %s
        
        Reference modules:           %s
        Obfuscated modules:          %s
        Remap done:                  %s
        
        Callgraph started:           %s
        
        Current runtime reported as: %s
          
        """%(self.pyretic.get_project(), self.pyretic.get_dump_dir(), self.runtime_version,
             self.pyretic.decompiler, RUNTIME_LOCATION, self.runtime_remapped,
             os.path.join(self.pyretic.get_projectdir(), "pybs", "ref_pyb"), 
             os.path.join(self.pyretic.get_projectdir(), "pybs", "obj_pyb"),
             self.ref_pyb_generated, self.callgraph_started, 
             sys.version.replace("\n", ""))
        
        
    def remap_complete(self):
        """
        For the current project has a re-mapped opcode table been generated, set var accordingly ?
        """
        try:
            os.stat(os.path.join(self.pyretic.get_project_mod_dir(), "opcodes_remap.py"))
            self.ref_pyb_generated = True
        except OSError:
            self.ref_pyb_generated = False
            
            
    
    def do_is_remapped(self, args = None):
        """
        Determine if the current runtime has remapped its opcode table
        
        Usage: is_remapped
        """
        ##Code to compile
        test_py = "print 'Am I remapped?'"
        ##The bytecode that should be produced if the runtime is NOT remapped
        expected_bc = "\x64\x00\x00\x47\x48\x64\x01\x00\x53"
        
        try:
            current_bc = compile(test_py, "<pyREtic test>", "exec")
        except Exception, err:
            print "[-] Problem compiling bytecode: %s"%(err)
            print "[?] Runtime may have been modified to mess with the compile() function ?"
            self.runtime_remapped = True
            
        if expected_bc != current_bc:
            print "[!] Runtime appears to be opcode remapped"
            self.runtime_remapped = True
        else:
            print "[=] Runtime prodcued expected bytecode it doesn't seem to be remapped"
            self.runtime_remapped = False
        
        
    def do_set_version(self, version):
        """
        Set the version number of the runtime we are running in to a specific value
        
        Usage: set_version 2.5.4
        """
        if not version:
            print "[-] No version given to set"
            
        self.runtime_version = version
        
        #TODO - set correct libs for project ?
        
        print "[+] Python version set as: %s"%(version)
        
        
    def _autodetect_version(self, always_prompt = False):
        """
        Interrogate the runtime 3 different ways to try and get an idea of what 
        the running python's version is

        Prompts user for their choice
        
        returns the version as a string
        """
        choices = []
        
        ##Get the version according to the builtin sys module
        ##Derived from PY_VERSION defined in patchlevel.h
        sys_mod_ver      = sys.version.split()[0]
        ##Derived from PY_MAJOR_VERSION, PY_MINOR_VERSION, PY_MICRO_VERSION defined in patchlevel.h
        sys_mod_ver_info = "%s.%s.%s"%(sys.version_info[0],sys.version_info[1],sys.version_info[2])
        
        print "[=] sys.version reports version: %s"%(sys_mod_ver)
        print "[=] sys.version_info reports version: %s"%(sys_mod_ver_info)
        
        choices.append(sys_mod_ver_info)        
        
        ##First compare - has to be an 'in' compare as sys_mod_ver may not have a .0 micro version
        if not sys_mod_ver in sys_mod_ver_info:
            print "[-] sys.version does not match sys.version_info"
            choices.append(sys_mod_ver)
        
        ##Get the magic number from a pyc
        magic_dict = self._get_magic()
        
        if magic_dict.has_key(None):
            ##A problem was encountered
            print "[-] Problem when getting pyc magic"
            print "[-] %s"%(magic_dict[None])
            
        else:
            print "[=] pyc magic number reports version: %s [magic: %s]"%(magic_dict.values()[0], magic_dict.keys()[0][0])
            ##Now compare sys.version to the magic byte version
            if not magic_dict.values()[0] in sys_mod_ver_info:
                print "[!] pyc magic does not match sys.version_info - *indication of obfuscation/opcode remapping*"
                closest_ver = self.closest(magic_dict.keys()[0][0], self.known_magic.keys())
                print "[=] pyc magic value: %s - closest value of a known runtime: %s [magic: %s]"%(magic_dict.keys()[0][0],self.known_magic[closest_ver],closest_ver)
                choices.append(self.known_magic[closest_ver])
                
        ##If there were not discrepencies and always_prompt not set return version
        if len(choices) == 1 and not always_prompt:
            print "[+] Python version detected as: %s. Setting..."%(choices[0])
            return choices[0]
        
        ##Else promptt user to choose
        print "[=] Please chose which runtime version to set:"
        for c in choices:
            print "\t [%s] %s"%(choices.index(c), c)
            
        print "\t [%s] Enter own version value to use"%(len(choices))
            
        user_choice = raw_input("Enter number of version to use: ")
        
        if user_choice == str(len(choices)):
            own_ver = raw_input("Please enter version to set (e.g. 2.5.4): ")
            return own_ver
            
        elif not user_choice.isdigit() or int(user_choice) > len(choices)-1 or int(user_choice) < 0:
            
            print "[-] Invalid choice entered: %s"%(user_choice)
            return None
        else:
            return choices[int(user_choice)]
                
        
    def do_detect_version(self, args):
        """
        Try to determine the version of the running Python (the runtime we are injected into)
        
        If there is a mismatch between the different ways we can do this you will be prompted 
        to choose for yourself
        
        Usage: detect_version
        """
        p_ver = self._autodetect_version()
        
        if not p_ver:
            return
        
        else:
            self.do_set_version(p_ver)
                
            
    def closest(self, target, collection):
        """
        For a list of integers and a given value find the list element it's closest to
        """
        return min((abs(target - i), i) for i in collection)[1] 
    
        
    def _get_magic(self):
        """
        Get the 'magic number' from the pyc file
        """
        ## Walk the sys.modules table until we get a file location of a loaded module
        path = None
        for m in sys.modules.values():
            if not m:
                continue
            
            try:
                path = m.__file__
                if os.path.splitext(path)[-1] in [".pyc", ".pyo"]:
                    break
            except:
                continue
            
        if not path:
            return {None : "No pyc module could be found"}
        
        ##Read the first 2 magic bytes
        try:
            fo = open(path, "rb")
            magic = struct.unpack( "<H", fo.read(2))
            fo.close()
            
        except Exception, err:
            return {None : "Error accessing '%s' : %s"%(path, err)}
        
        ##Compare to table of values derived from import.c
        self.known_magic = {20121:"1.5", #or 1.5.1 or 1.5.2
                       50428:"1.6",
                       50823:"2.0", #or 2.0.1
                       60202:"2.1", #or 2.1.1, 2.1.2
                       60717:"2.2",
                       62011:"2.3",
                       62021:"2.3",
                       62041:"2.4",
                       62051:"2.4",
                       62061:"2.4",
                       62071:"2.5",
                       62081:"2.5",
                       62091:"2.5", 
                       62092:"2.5", 
                       62101:"2.5", 
                       62111:"2.5", 
                       62121:"2.5",             
                       62131:"2.5", 
                       62151:"2.6", 
                       62161:"2.6", 
                       62171:"2.7", 
                       62181:"2.7", 
                       62191:"2.7", 
                       62201:"2.7", 
                       62211:"2.7"}
        
        try:
            pyc_ver = self.known_magic[magic]
        except KeyError:
            ##Unknown magic value - sign of obfuscation / remapping
            pyc_ver = "unknown"
            
        return {magic : pyc_ver}
            


    def do_download_runtime(self, version):
        """
        Download the specified Python runtime sourcecode from python.org and decompress it.
        It is saved to the 'Downloaded_Runtimes' subdir and shared between all projects
        
        Usage: download_runtime 2.5.4
        """
        if not version:
            print "[-] No Python version specified, cannot download"
            return
        elif self.py_ver_downloaded(version):
            print "[+] That version has already been downloaded, no need to redownload"
            return
        
        target = r"http://www.python.org/ftp/python/%s/Python-%s.tar.bz2"%(version, version)
        local  = os.path.join(MODULE_LOCATION, "Downloaded_Runtimes","Python-%s.tar.bz2"%(version))
        print "[=] Downloading from %s ....."%(target)
        try:
            fn, msg = urllib.urlretrieve(target, local)
            print "[+] Download complete - saved to %s"%(local)
        except Exception, err:
            print "[-] Problem downloading %s : %s"%(target, err)
            return
            
        print "[=] Decompressing...."
        try:
            tar = tarfile.open(local, "r:bz2")
            tar.extractall(path = os.path.join(MODULE_LOCATION, "Downloaded_Runtimes"))
            tar.close()
            print "[+] Complete"
        except:
            print "[-] Error decompressing - Check that the version given is a valid runtime at python.org"
            
            
    def py_ver_downloaded(self, ver):
        """
        Has the specifiedversion of Python already been downloaded ?
        """
        try:
            os.stat(os.path.join(MODULE_LOCATION, "Downloaded_Runtimes","Python-%s"%(ver)))
            return True
        except:
            return False
        
    

        
    def set_py(self, loc, ver):
        """
        Set the location of the python runtime for the specified version
        Called from the other do_set_py* functions
        """
        global RUNTIME_LOCATION
        RUNTIME_LOCATION[ver] = loc
        print "[=] Reference Python %s location set to: %s"%(ver, loc)
        
        
    def do_set_py24(self, loc):
        """
        Reset the location of the standard Python 2.4 runtime used to generate
        reference bytecode
        
        Usage: set_py24 /usr/local/bin/python2.4
        """
        self.set_py(loc, "2.4")        

        
    def do_set_py25(self, loc):
        """
        Reset the location of the standard Python 2.5 runtime used to generate
        reference bytecode
        
        Usage: set_py25 /usr/local/bin/python2.5
        """
        self.set_py(loc, "2.5")
        

    def do_set_py26(self, loc):
        """
        Reset the location of the standard Python 2.6 runtime used to generate
        reference bytecode
        
        Usage: set_py26 /usr/local/bin/python2.6
        """
        self.set_py(loc, "2.6")
        
        
    def do_set_py27(self, loc):
        """
        Reset the location of the standard Python 2.7 runtime used to generate
        reference bytecode
        
        Usage: set_py27 /usr/local/bin/python2.7
        """
        self.set_py(loc, "2.7")
        

    def do_set_project(self, name):
        """
        Create a new project or switch to an existing one
        
        Usage: set_project <project name>
        """
        #TODO - description field
        if not name:
            print "[-] No project name supplied"
            return        
     
        elif self.does_project_exist(name):
            ##Project already exists so just switch to it
            self.switch_project(name)
            return
        
        print "[=] Please select the Python runtime version to associate wth this project"
        print "[=] Automatic version detection "
        p_ver = self._autodetect_version()
        
        ##Has that version of the Python runtime already been downloaded?
        if not self.py_ver_downloaded(p_ver):
            print "[=] Python %s has not already been downloaded to the pyREtic cache,"%p_ver
            print "    if you choose not to download the the standard runtime there"
            print "    may be difficulties in performing some operations due to module"
            print "    version mismatches."
            choice = raw_input("Do you want to download Python %s now? "%p_ver )
            
            if choice.lower() in ["y", "yes"]:
                self.do_download_runtime(p_ver)
            else:
                print "[-] Not downloading Python"
                print "[!] Please copy the correct files for the Python runtime to the %s projects libs directory"
            
        print "[=] Creating new project: '%s'"%(name)
        ret = self.pyretic.new_project(name, p_ver)
        if ret == False:
            print "[-] Problem during project creation, source code output still going to: %s"%(self.pyretic.get_dump_dir())
        elif ret == True:
            print "[+] Project created. Source code output now going to : %s"%(self.pyretic.get_dump_dir())


        self.prompt = '(REpdb:%s) '%(self.pyretic.get_project())
        
        self.do_set_version(p_ver)
        
        self.__reload_modules()
        
        
    def switch_project(self, name):
        """
        Switch to another project descriptor
        """
        if not name:
            print "[-] No project name supplied"
            return
        
        elif not self.does_project_exist(name):
            print "[-] Project does not already exist, cannot switch to it"
            return

        print "[=] Switching to project '%s'"%(name)
        
        self.pyretic.switch_project(name)
        
        print "[+] Success, sourcecode output now going to %s"%(self.pyretic.get_dump_dir())
        
        self.prompt = '(REpdb:%s) '%(self.pyretic.get_project())
        
        ##Read project meta data - 
        #TODO break into own function as we hold more meta data
        try:
            f = open(os.path.join(self.pyretic.get_projectdir(), "meta"), "r")
            data = f.read()
            f.close()
            ver = data.split(":")
            self.do_set_version(ver[1]) 
        except Exception, err:
                print "[-] Problem reading project meta data : %s"%(err)
        
        self.remap_complete()
        
        self.__reload_modules()
        
        
    def does_project_exist(self, name):
        """
        Determine whether a project of the given name already exists
        
        Return boolean
        """
        name = self.pyretic.normalise_path(name)
        try:
            print os.path.join(self.pyretic.get_projectroot(), name)
            os.stat(os.path.join(self.pyretic.get_projectroot(), name))
            return True
        except:
            return False
        

    def do_setprojectroot(self, location):
        """
        Leave the project name the same but change the root directory location 
        on the filesystem. The currently set project is used as the project to relocate
        
        Usage: set_project_root /tmp/pyretic_dump
        """
        if not location:
            print "[-] No project root location supplied"      
            return  
        
        print "[=] Setting project root to '%s'"%(location)
        if not self.pyretic.set_projectroot(location):
            print "[-] Problem during project change, source code output still going to: %s"%(self.pyretic.get_dump_dir())
        else:
            print "[=] Source code output now going to : %s"%(self.pyretic.get_dump_dir())
            
        self.remap_complete()


    def do_fs_um_decompile(self, path = None):
        """
        Decompile obfuscated bytecode by traversing the filesystem from a given
        start point and using the current runtimes marshal module to unmarshal
        the bytecode of each .pyc found.
        
        Note: If the current obfuscated runtime does not have the marshal module
              available then this decompilation technique cannot be used.
              
        usage: fs_um_decompile <path to obfuscated pyc's>
        example: fs_um_decompile /tmp/foo.app/Contents/Resources/runtime/site_packages/
        """
        if not path:
            print "[-] No path to begin decompilation from specified"
            return

        self.pyretic.fs_unmarshal(path)


    def do_fs_mem_decompile(self, path = None):
        """
        Decompile obfuscated bytecode by traversing the filesystem from a given
        start point but do NOT rely on the presence of the marshal module to be
        able to get thebytecode from the pyc file found. Instead each pyc found
        is imported and each of its objects are interogated for their bytecode. 
        These bytecode objects are what is decompiled.
        
        Note: If the current obfuscated runtime does not have the marshal module
              available but you do have access to the filesystem where the obfuscated
              pyc's reside then this is the technique to use.
              
        usage: fs_mem_decompile <path to obfuscated pyc's>
        example: fs_mem_decompile /tmp/foo.app/Contents/Resources/runtime/site_packages/
        """
        if not path:
            print "[-] No path to begin decompilation from specified"
            return

        self.pyretic.fs_objwalk(path)


    def do_pure_mem_decompile(self, obj = None):
        """
        Decompile to source code purely from instantiated objects. This assumes
        no availability of the marshal module or even access to the filesystem
        where the pyc files reside, this decompiles directly from the currently
        executing runtimes namespace.
        The specified object is decompiled and the objects it contains are traversed
        and decompiled until no more remain.
        
        [ Currently available objects can be seen by typing dir() at the REpdb prompt]

        usage: pure_mem_decompile <name of object to decompile>
        example: pure_mem_decompile AnObjectsName
        """
        if not obj:
            print "[-] No object to begin decompilation from specified"
            return
        
        ##We need to access the context of the frame we started the trace from
        ##NOT our frame we are executing in here - self.curframe holds this from
        ##bdp
        #print "Current executing frame context: ",sys._getframe()
        #print "Frame from where the debugger was called: ",self.curframe
        locals = self.curframe.f_locals
        globals = self.curframe.f_globals
        try:
            ##We are passed a string, eval it to an object using the calling frames 
            ## globals and locals
            e_obj = eval(obj, globals, locals)

        except Exception, err:
            print dir()
            print "[-] Problem accessing specified object: %s"%(err)
            return

        self.pyretic.mem_objwalk( e_obj )



    def do_get_version(self, args):
        """
        Get the reported version of the currently executing Python runtime
        Note: This may not be accurate, a runtime can be made to report any version. 
              Use only as an indicator when choosing a reference runtime to use.
              
        usage: get_version
        """
        print "[=] Report version of current runtime:\n\t%s\n"%(sys.version)
    
    def do_auto_remap(self, remapped_pycs):
        """
        Make some best guesses on how to remap the opcodes from the currently
        running obfuscated runtime.
        
        NOTE: If there is an exiting auto_remap project it will be overwritten
        
        Usage: auto_remap <path to remapped pycs>
        """        
        if not remapped_pycs:
            print "[-] No target obfuscated byte code supplied to remap. Aborting"
            return
        
        self.do_is_remapped()
        if not self.runtime_remapped:
            resp = raw_input( "[!] It doesn't seem like the runtime we are in has remapped it's opcodes, do you want to continue to remap anyway ? (yes/no) ")
            if resp.lower() in ["n","no"]:
                print "[=] Aborting remap"
                return
            
        ##Remove an existing auto_remap project
        try:
            shutil.rmtree(os.path.join(self.pyretic.prev_project_root, "auto-remap"))
        except:
            ##Probably didn't exist
            pass

        ##New project called auto remap - this will prompt for py runtime version choice
        self.do_set_project("auto-remap")
            
        ##Generate reference bytecode
        self.do_gen_ref()
        
        ##Generate obfuscated bytecode with supplied pyc target
        self.do_gen_obf(remapped_pycs)
        
        ##Perform remap
        self.autowrite = True
        self.do_remap()
        
        ##Swap in the newly generated opcodes
        self.do_swap_opcodes()
        
        print "[+] Automatic remapping of opcodes complete. Please restart to use the new opcode tables in decompilation"
        
    

    def do_gen_ref(self,  reference_modules = None):
        """
        Generate reference bytecode from the .py's at the path specified
        using the Python runtime version already set. If not path is specified
        the relevant Python runtime will be used if it has already been downloaded
        with download_runtime.
        
        The generated bytecode will be used to diff against the obfuscated
        bytecode to deduce a modified opcode map.
        The more commonality between the reference and obfuscated bytecode there
        the higher the number of opcodes that will be able to be remapped.
  
        Usage:   gen_ref  [to use the downloaded runtime of the current project 
                           version as the reference source]
                 gen_ref <path to directory of reference python source code>
        Example: gen_ref /tmp/python2.5.4/Lib 
        """        
        try:
            downloaded_rt = os.path.join(MODULE_LOCATION, "Downloaded_Runtimes",
                                         "Python-%s"%(self.runtime_version), "Lib")
            os.stat(downloaded_rt)
            source_modules = downloaded_rt
        except:
            source_modules = None
            
        if not reference_modules and not source_modules:
            
            print "[-] No path given from which to generate reference bytecode and no runtime downloaded for stdlib use"
            return
        elif reference_modules:
            source_modules = reference_modules
            
        ##Force a recompile so we know we are in a clean state
        self.do_recompile(downloaded_rt)
            
        source_modules = self.pyretic.normalise_path(source_modules)
        print "[=] Generating bytecode from .py's at: %s"%(source_modules)
        
        ##Where the bytecode output will go
        self.ref_pyb = os.path.join(self.pyretic.get_projectdir(), "pybs")
        
        ##We need to run in a standrd runtime (not the current one)to get reference 
        ##bytecode so we call out to the external Python runtime that is set
        if self.runtime_version == "default":
            version_to_gen = "2.5"
        else:
            for maj_ver in RUNTIME_LOCATION.keys():

                if maj_ver in self.runtime_version:
                    version_to_gen = maj_ver
                    break
            else:
                print "[-] Unknown runtime location for version specified: %s"%(self.runtime_version)
                return

        ##-S needed to supress any site specific import hooks that may be in the
        ## obfuscated package we are runnign from that will get in the way
        command = [RUNTIME_LOCATION[version_to_gen], "-S",
                   os.path.join(MODULE_LOCATION, "OpcodeRemap", "OpcodeRemap.py"), 
                   version_to_gen, self.ref_pyb, source_modules]
        print "[=] Using runtime located at %s to create reference bytecode"%(RUNTIME_LOCATION[version_to_gen])
        
        ## Reset environment of PYTHON* variables to avoid interference
        try:
            old_home = os.environ["PYTHONHOME"]
            del os.environ["PYTHONHOME"]
        except KeyError:
            old_home = None
            
        try:
            old_path = os.environ["PYTHONPATH"]
            del os.environ["PYTHONPATH"]
        except KeyError:
            old_path = None
        
        ##Spawn process to generate bytecodes
        try:
            subprocess.call(command)
            self.ref_pyb_generated = True
        except:
            print "[-] Error trying to execute: %s"%(command)

        ##Reset env
        if old_home:
            os.environ["PYTHONHOME"] = old_home
        if old_path:
            os.environ["PYTHONPATH"] = old_path
     
        print "[+] Reference bytecode generated"
        
        
    def do_gen_obf(self, obfuscated_modules = None):
        """
        Generate obfuscated Python bytecode for the modules at the path 
        specified using the current runtime we are running from. 
        The generated bytecode will be used to diff against the 
        reference bytecode to deduce a modified opcode map. In general you
        should point this at the directory containing the obfuscated
        stdlib .pyc's for the obfuscated runtime
        
        The more commonality between the reference and obfuscated bytecode there
        the higher the number of opcodes that will be able to be remapped.
  
        Usage:   gen_obf <path to directory of obfusctaed python .pyc's>
        Example: gen_obf /tmp/foo.app/Contents/Resources/runtime/site_packages/ 
        """
        if not obfuscated_modules:
            print "[-] No path given from which to generate obfuscated bytecode"
            return
        
        ##Make sure we have everything current
        if "OpcodeRemap" not in sys.modules.keys():
            from OpcodeRemap import OpcodeRemap
        else:
            OpcodeRemap = reload(OpcodeRemap)
        
        self.obf_pyb = os.path.join(self.pyretic.get_projectdir(), "pybs")
        
        obfuscated_modules = self.pyretic.normalise_path(obfuscated_modules)
        print "[=] Generating bytecode from .py's at: %s"%(obfuscated_modules)
        
        ##Call into OpcodeRemap
        if self.runtime_version == "default":
            version_to_gen = "2.5"
        else:
            version_to_gen = self.runtime_version

        OpcodeRemap.gen_obf(self.obf_pyb, obfuscated_modules, version_to_gen)
            
        print "[+] Obfuscated bytecode generated"
        
    
    def do_remap(self, dirs = None):
        """
        From the two sets of .pyb's produced by gen_r2x and gen_o2x do the compares
        to work out the new opcode map. From this new opcode map create new files
        opcode.py (for the running stdlib) and opcodes.py (for UnPYC) 
        
        Note: the .pyb's must already have been generated from the gen_xxx calls
        
        Usage: remap
        """
        if not dirs:

            try:
                os.stat(os.path.join(self.pyretic.get_projectdir(), "pybs","obf_pyb"))
                os.stat(os.path.join(self.pyretic.get_projectdir(), "pybs","ref_pyb"))
            except OSError:
                print "[-] No .pyb directories could be found and non specified"
                return

            ##Try setting to where pyb's would reside if they had already been gen'd
            ref_dir = os.path.join(self.pyretic.get_projectdir(), "pybs","ref_pyb")
            obf_dir = os.path.join(self.pyretic.get_projectdir(), "pybs","obf_pyb")


        else:
            ##Split supplied sirs string to ref and obf
            try:
                ref_dir, obf_dir = dirs.split(" ")
            except:
                print "[-] Reference or obfuscated .pyb sets not produced or specified"
                return
            
        ##Make sure we have everything current
        if "OpcodeRemap" not in sys.modules.keys():
            from OpcodeRemap import OpcodeRemap
        else:
            OpcodeRemap = reload(OpcodeRemap)

        ##Location where the opcode/opcodes.py will be dumped - with project
        output_dir= self.pyretic.get_project_mod_dir

        ##Call into OpcodeRemap
        try:
            OpcodeRemap.remap(ref_dir, obf_dir, self.pyretic.get_project_mod_dir())

        except OpcodeRemap.OpcodeRemapError, err:
            print "[-] Problem with remap: %s"%(err)
            

    def do_swap_opcodes(self, args = None):
        """
        Swap the remapped opcodes.py module for the original module in the UnPYC
        directory. Until this is done UnPYC will not be able to decompile 
        correctly as it will be using the wrong opcode map. The opcodes.py file
        that will be used is the one that is located at the PROJECT_DIR/libs

        Ssage: swap_modules
        """
        files = ["opcode", "opcodes"]
        
        for f in files:
            try:
                remap_name = os.path.join(self.pyretic.get_project_mod_dir(), "%s_remap.py"%f)
                os.stat(remap_name)
            except OSError:
                print "[-] Remapped %s_remap.py file cannot be found at: %s\n\t Has it been generated yet?"%(f, remap_name)
                continue
            
            ##Archive current opcodes.py module
            archive_name = os.path.join(self.pyretic.get_project_mod_dir(), "%s_orig.py"%f)
            curr_name    = os.path.join(self.pyretic.get_project_mod_dir(), "%s.py"%f)
            try:
                shutil.copyfile(curr_name,  archive_name)
                print "[+] Original %s.py archived to %s"%(f,archive_name)
    
                ##Copy over
                shutil.copyfile(remap_name, curr_name)
                self.do_module_restore = False
                
                #TODO force reload
                ##live.reload()
                
            except Exception, err:
                print "[-] Error copying a file: %s"%(err)
                
        print "[+] New opcode maps copied"
        print "[!!] *MUST restart REpdb for changes to take effect*"
        
##        ##Reload stdlib modules
##        self.__reload_modules()
##        
##        if "OpcodeRemap" not in sys.modules.keys():
##            print "IMPORT"
##            from OpcodeRemap import OpcodeRemap
##            OpcodeRemap.opcode.__file__
##        else:
##            print "RELOAD"
##            OpcodeRemap = reload(OpcodeRemap)
##            OpcodeRemap.opcode.__file__


            
    def do_restore_opcodes(self, args):
        """
        Restore the original opcode.py and opcodes.py module that was archived by swap_opcodes
        
        Usage: restore_opcodes
        """
        files_to_move = ["opcode", "opcodes"]
        
        
        for f in files_to_move:
            try:
                os.stat(os.path.join(self.pyretic.get_project_mod_dir(), "%s_orig.py"%(f)))
            
            except:
                print "[-] Archived file %s_orig.py cannot be found, check if has remapping occurred?"%(f)
                continue
            
            
            try:
                shutil.copyfile(os.path.join(self.pyretic.get_project_mod_dir(), "%s_orig.py"%(f)),
                                os.path.join(self.pyretic.get_project_mod_dir(), "%s.py"%(f)))
                
                print "[+] Restored original %s.py"%(f)
                
            except Exception, err:
                print "[-] Error copying file: %s"%(err)
                
        #print "[=] *MUST* restart REpdb for changes to take effect"
        #TODO force reload
        ##live.reload()
        self.__reload_modules()


    def do_recompile(self, path):
        """
        For the path specified do a recursive recompilation of all .py's found
        using the current runtimes compiler (if available)
        
        Usage: recompile <path to modules>
        Example: recompile /tmp/python_254/Libs
        """
        ##From the projects libs
        import compileall
        
        if not path:
            print "[-] No path to begin recompilation from specified"
            return
        
        path = self.pyretic.normalise_path(path)
        
        try:
            compileall.compile_dir(path, force=1)            
            print "[+] Recompilation complete"
        except Exception, err:
            print "[-] Unable to recompile: %s"

   
    def trace_dispatch(self, frame, event, arg):
        """
        Overide the bdb trace_dispatch method so as we can add in more
        trace hooks for other functionality such as call graphing
        """
        #print "\nCalling Frame : %s\nDebugger Frame: %s\n"%(frame, self.debugger_frame )
        self.debugger_frame = sys._getframe()
        self.calling_frame = frame
        
        if self.callgraph_started:
            pycallgraph.tracer(frame, event, arg)

        ##Call through to the original trace_dispatch to continue the
        ##debugger activity
        return pdb.bdb.Bdb.trace_dispatch(self, frame, event, arg)
        
    ##Extra none decompile related functionality
    def do_set_callgraph_exclude(self, excludes):
        """
        Set an exclusion filter for the callgraph functionality, this defines
        modules/functions that are not included in the callgraph tracing
        
        Argument is a comma seperated list of filter expresions
        
        Usage: set_callgraph_exclude foo,bar*,blat
        """
        
        self.cg_exclude += excludes.replace(" ","").split(",")
        
        print "[=] Set callgraph excludes to: %s"%(self.cg_exclude)
        
    
    def do_start_callgraph(self, name):
        """
        Initialise a callgraph trace using pycallgraph
        After this is set use the pdb commands 'n', 'c' etc to step through
        the application being debugged and generate the callgraph
        
        The callgraph can be stopped & written at anytime by 'stop_callgraph',
        if the debugging exits the callgraph is automatically stopped and written

        Usage: start_callgraph <name of callgraph if you want non-default name>
        """
        ##Both pdb and pycallgraph both want to set the tracer so we have to chain them
        ## sys.settrace applies globally to all frames
        if not CAN_CALLGRAPH:
            print "[-] pycallgraph module, or graphviz unavailable"
            return

        ##If no filename for the callgraph is given just use epoch to get one
        if not name:
            self.cg_name = "callgraph_%s"%(str(time.time()).split(".")[0])
        else:
            self.cg_name = name

        ##Try to cleanup graph a bit
        filter_func = pycallgraph.GlobbingFilter(exclude = self.cg_exclude, max_depth = 4)

        locals  = self.calling_frame.f_locals
        globals = self.calling_frame.f_globals        
        
        ##Call the callgraph funtion from the context f_backframe
        exec("from ThirdParty import pycallgraph", globals,locals)
        exec("pycallgraph.start_trace()", globals, locals)
        self.callgraph_started = True
        print "[+] Call graph initialised"


    def do_stop_callgraph(self, foo):
        """
        Stop & print callgraph
        
        Usage: stop_callgraph
        """
        if not self.callgraph_started:
            print "[-] Call graph not started yet. Use 'start_callgraph' to start"
            return

        graph_path = os.path.join(self.pyretic.get_projectdir(),
                                  "%s.jpg"%self.cg_name.strip(os.sep))

        print "[+] Outputting callgraph to: %s\n  This may take a while..."%(graph_path)

        ##Put in the calling frames context
        locals  = self.calling_frame.f_locals
        globals = self.calling_frame.f_globals   
        try:
            exec("pycallgraph.make_dot_graph('%s',format='jpg', tool='dot')"%graph_path, globals, locals)
            print "[+] Graph generation complete"
        except Exception, err:
            print "[-] Problem generating callgraph: %s"%err
            print "[?] Is graphviz installed on your system? (http://www.graphviz.org/Download..php)"
        
        self.callgraph_started = False


    def do_obj_mirror(self, args):
        """
        For the supplied object, all of it's methods/attributes etc are mirrored
        in the calling objects namespace
        This is a dirty way of acting as an object proxy meaning we can be injected
        in place of another object and be sure we won't break the larger app
        
        If no frame is specified then the frame from which the debugger was called is used
        If "debugger" is given as the frame the debugger frame is used
        
        Usage: obj_mirror <instantiated object to mirror>
        """
        import inspect
        
        if not args:
            print "[-] No object supplied to mirror"
            return 
        
        arg_list = args.split(" ")
        s_obj_to_mirror = arg_list[0]
        
        if len(arg_list) > 1:
            frame = arg_list[1]
        else:
            frame = None
        
        if not frame:
            ##Use context of calling frame
            frame_context = self.curframe
        
        elif frame == "debugger":
            ##Use context of the frame the debugger is executing in
            frame_context = self.debugger_frame
        
        else:
            ##None frame object supplied ... bail
            print "[-] None frame object supplied - object type was %s"%(type(frame))
            return
        
        locals  = frame_context.f_locals
        globals = frame_context.f_globals
        
        print "[=] Mirroring %s in the context of %s"%(s_obj_to_mirror, frame_context)
        
        try:
            obj_to_mirror = eval(s_obj_to_mirror, globals, locals)
        except:
            print "[-] Unknown object specified, cannot mirror"
            return

        for x in dir(obj_to_mirror):

            skip_list = ["__init__", "__builtins__", "__doc__", "__name__"]
            if inspect.isbuiltin(x) or x in skip_list:
                print "[-] skipping %s"%(x)
                continue

            print "[+] %s -> %s.%s"%(x, obj_to_mirror.__name__, x)
            exec("%s = %s.%s"%(x, obj_to_mirror.__name__, x), 
                 globals, locals)
            
    def cleanup(self, args):
        """
        Cleanup function, currently just stops the callgraph if it
        has been started
        """
        #print "[+] atexit cleanup function entered"
        if self.callgraph_started:
            self.do_stop_callgraph(None)
            
        if self.do_module_restore:
            self.do_restore_opcodes(None)
            
        
# Simplified interface - for similar uasage to pdb.py

def run(statement, globals=None, locals=None):
    REpdb().run(statement, globals, locals)

def runeval(expression, globals=None, locals=None):
    return REpdb().runeval(expression, globals, locals)

def runctx(statement, globals, locals):
    # B/W compatibility
    run(statement, globals, locals)

def runcall(*args, **kwds):
    return REpdb().runcall(*args, **kwds)

def set_trace(frame = None):

    REPDBInstance = REpdb()
    
    atexit.register( REPDBInstance.cleanup, REPDBInstance)
    
    REPDBInstance.set_trace(sys._getframe().f_back)
            

# Post-Mortem interface - for similar uasage to pdb.py

def post_mortem(t):
    p = REpdb()
    p.reset()
    while t.tb_next is not None:
        t = t.tb_next
    p.interaction(t.tb_frame, t)

def pm():
    post_mortem(sys.last_traceback)


if __name__ == "__main__":

    set_trace()
