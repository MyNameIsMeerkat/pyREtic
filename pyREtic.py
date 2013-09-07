#!/usr/bin/env python
##WingHeader v1 
###############################################################################
## File       :  pyREtic.py
## Description:  Main module of the pyREtic suite where decompilation and 
##            :  source reconstruction logic lives
## Created_On :  Tue Aug  3 20:26:04 2010
## Created_By :  Rich Smith
## Modified_On:  Wed Dec 22 05:36:14 2010
## Modified_By:  Rich Smith
## License    :  GPLv3 (Docs/LICENSE.txt)
##
## (c) Copyright 2010, Rich Smith all rights reserved.
###############################################################################
__author__ = "Rich Smith"
__version__= "0.5.1"

import os
import os.path
import sys
import shutil

##Allows easy relative writes to the location this dir later
MODULE_LOCATION = os.path.dirname(__file__)

class pyREtic:
    """
    Main pyREtic decompilation functionality
    Encompasses both a way to walk a series of objects (filesystem or memory)
    as well as the way in which the bytecode is obtained (via unmarshalling or importing)
    """
    def __init__(self, write_source = True, display_source = False,
                 project_name = "default", project_root = None, decompiler = "unpyc"):
        """
        Set project name and where to dump the code produced
        """        
        ##What is the decompiler we are using
        self.decompiler = decompiler
        
        if not project_root:
            self.project_root = os.path.join(MODULE_LOCATION, "Projects" )
        else:
            self.project_root = project_root
        
        ##These need to be set so that the fallback procedure for future name changes doesn't fail
        self.project_name = project_name.strip(os.sep)
        self.project_dir  = os.path.join(self.project_root, self.project_name)
        
        self.set_projectroot(self.project_root)
        
        try:
            os.stat(self.project_dir)
            ##Project already exists - switching to it
            self.switch_project(self.project_name)
        except:
            ##Project does not exist - create it
            self.new_project(project_name)
        
        #print "[+] Outputting decompiled files to: %s"%(self.dump_dir)
        
        ##How to use source code produced
        self.write_sourcecode   = write_source        
        self.display_sourcecode = display_source  
        
        
    def _quiet_makedir(self, dirname):
        """
        Make a dir, supress message if already exists
        """        
        try:
            os.makedirs(dirname)
        except Exception, err:
            if "Errno 17" not in str(err):
                print "[-] Problem creating output directory '%s': %s"%(dirname, err)
                raise
            
    def normalise_path(self, path):
        """
        Try and expand environment variables and '~' etc that are in paths
        
        Return:
               expanded path - string
        """
        return os.path.expandvars(os.path.expanduser(path))
        

##    def set_project(self, name):
##        """
##        Set the variable for the *name* of the project & alter the filesyetm 
##        location accordingly
##        Calls set_projectdir
##        """
##        self.prev_project_name = self.get_project()
##        
##        self.project_name = name.strip(os.sep)
##        
##        ##Adjust the project dir and sourcode dump within project dir accordingly
##        return self.set_projectdir()
        
        
    def get_project(self):
        """
        Get the current project name
        """
        return self.project_name  
    
    
    def switch_project(self, name, set_env = True):
        """
        Set variable for the location of the project directory & call init_project
        to initialise the whole project filesystem structure
        
 
        """
        self.prev_project_name = self.get_project()

        self.project_name = name.strip(os.sep)
        
        ##Store previous location of the project dir
        self.prev_project_dir = self.get_projectdir()
        
        ##project directory location
        self.project_dir = os.path.join(self.project_root, self.project_name)
        
        ##sourcode dump location inside project
        self.dump_dir = os.path.join(self.project_dir, "sourcecode")
        
        ## Alter the python path to reference the new project libs dir to allow
        ## overiding of modules (e.g. opcode.py) + remove previous project dirs
        if set_env:
            
            old_path = os.path.join(self.prev_project_dir, "libs")
            
            if old_path in sys.path:
                sys.path.remove(old_path)
            
            sys.path = [os.path.join(self.get_projectdir(), "libs") ] + sys.path
                    
       
    
    
    def get_projectdir(self):
        """
        Get the directory for the project
        """
        return self.project_dir
    
    
    def new_project(self, name, py_version = None):
        """
        Create a new project, setting the version of python it is for to the version
        supplied
        """        
        self.switch_project(name, False)
        
        ret = self.init_project(py_version)
        
        ## Alter the python path to reference the new project libs dir to allow
        ## overiding of modules (e.g. opcode.py) + remove previous project dirs
        if ret:
            
            old_path = os.path.join(self.prev_project_dir, "libs")
            
            if old_path in sys.path:
                sys.path.remove(old_path)
            
            sys.path = [os.path.join(self.get_projectdir(), "libs") ] + sys.path
                    
        return ret
    
    
    def get_project_mod_dir(self):
        """
        Get the directory for the project specific modules
        """
        return os.path.join(self.project_dir, "libs")
                
    
    def set_projectroot(self, location):
        """
        Set the root filesystem location for ALL projects, create on the filesystem
        if needed
        Calls set_projectdir to reassign & create the projectdir/dumps dirs etc
        """
        ##Store previous location of the project root
        self.prev_project_root = self.get_projectroot()
        
        location = self.normalise_path(location)
        
        ##Create the root location for ALL projects
        self._quiet_makedir(location)
        self.project_root = location
                
        ##Adjust the project dir and sourcode dump within project dir accordingly
        return self.switch_project(self.get_project())
                
                
    def get_projectroot(self):
        """
        Get current project root
        """
        return self.project_root
        
        
    def get_dump_dir(self):
        """
        Get where the source code dump is 
        """
        return self.dump_dir
        
    
    def init_project(self, py_ver):
        """
        Setup the initial project structure on the filesystem
        
        Return False on error & True on successful creation of new project dirs 
        """ 
        #TODO - initial project creation when py_ver unknown 
        if not py_ver:
            ##initial default project with no version has been set - just use 2.5.4 modules and hope....
            py_ver = "default"
            
        try:
            ##Create dir structure on fs
            self._quiet_makedir(os.path.join(self.get_projectdir(), "sourcecode") )
            self._quiet_makedir(os.path.join(self.get_projectdir(), "pybs") )
            self._quiet_makedir(os.path.join(self.get_projectdir(), "libs") )
            
            ##Create __init__.py's for dirs from which imports may occur
            f = open( os.path.join(self.get_projectdir(), "libs", "__init__.py"),"wb")
            f.close()
            f = open( os.path.join(self.get_projectdir(), "__init__.py"),"wb")
            f.close()
            
            #TODO - 2.7 support, change to just copy entire module set ?
            rt_root = os.path.join(MODULE_LOCATION, "Downloaded_Runtimes","Python-%s"%(py_ver))
            
            stdlib_files = {"default" : ["compileall.py", "copy.py", "dis.py", "inspect.py", "opcode.py",
                                         "py_compile.py", "struct.py", "token.py", "tokenize.py",
                                         "traceback.py", "types.py"],
                            "2.5"     : ["compileall.py", "copy.py", "dis.py", "inspect.py", "opcode.py",
                                         "py_compile.py", "struct.py", "token.py", "tokenize.py",
                                         "traceback.py", "types.py"],
                            "2.6"     : ["_abcoll.py", "abc.py", "collections.py", "compileall.py", 
                                         "dis.py", "inspect.py", "opcode.py", "py_compile.py",
                                         "traceback.py", "types.py"]}
            
            for k in stdlib_files.keys():
                if k not in py_ver:
                    continue
               
                for f in stdlib_files[k]:
                    try:
                        shutil.copyfile(os.path.join(rt_root, "Lib", f), 
                                        os.path.join(self.get_projectdir(), "libs", f))
                    except Exception, err:
                        print "[-] Problem copying one of the stdlib files for project library: %s"%(err)
                break
            else:
                print "[-] version of Python %s not supported. Add files to project library by hand"%(py_ver)
               
            ##Copy the opcodes .py for unpyc
            #TODO - seperate decompiler specific code from main into specific stubs for each
            if self.decompiler.lower() == "unpyc":
                try:
                    ##Copy the unpyc opcode table into the project libs
                    shutil.copyfile(os.path.join(MODULE_LOCATION, "Decompilers","unpyc", "opcodes_std.py"), 
                                    os.path.join(self.get_projectdir(), "libs", "opcodes.py"))
                except Exception, err:
                    print "[-] Problem copying opocdes.py for unpyc: %s"%(err)
                    print "[!] You must copy an appropriate opocdes.py to %s by hand"%(os.path.join(self.get_projectdir(), "libs"))
                    
            ##Save version to the project as this may be ifferent than what the runtime reports
            try:
                f = open(os.path.join(self.get_projectdir(), "meta"), "w")
                f.write("version:%s"%(py_ver))
                f.close()
            except Exception, err:
                print "[-] Problem writing project meta data : %s"%(err)
            
            return True
            
        except Exception, err:
            print "[-] Problem creating project directory structure: %s"%(err)
            self.restore_previous_project_structure()
            return False
        
        
        
    def restore_previous_project_structure(self):
        """
        If there was a problem creating the new project structure restore the previous values
        """        
        self.project_name = self.prev_project_name
        self.project_dir  = self.prev_project_dir
        self.project_root = self.prev_project_root
        self.dump_dir     = os.path.join(self.prev_project_dir, "sourcecode")
        
    
    def fs_unmarshal(self, fs_root, depth=None):
        """
        Walk the filesystem from start directory indicated & to a depth inidicated
        
        The unmarshal technique will be used on each .pyc/.pyo found
        """
        #TODO depth, make decompiler independent
        from Decompilers.unpyc import liveUnPYC as live
        
        tag = "fs_um"
        self._quiet_makedir(os.path.join(self.dump_dir, tag))
        
        lupc = live.liveUnPYC(self)
        
        fs_root = self.normalise_path(fs_root)

        ##Single file supplied no need to walk the directory
        if os.path.isfile(fs_root):
            
            print "[+] Decompiling single file: %s"%(fs_root)
            sc   = lupc.fs_decompile(fs_root)
            
            ##Do the output style specified
            if self.write_sourcecode:
                filename = os.path.split(fs_root)[-1]
                self._write_source(sc, "singlefile", filename, tag)
                
            if self.display_sourcecode:
                self._display_source(sc)
             
            
        else:
            print "[+] Decompiling directory starting at: %s"%(fs_root)
            for (path, dirs, pyx) in self._fs_walk(fs_root, depth, tag):
        
                print "[+] Decompiling via unmarshal '%s'...."%(pyx)
                sc   = lupc.fs_decompile(os.path.join(path,pyx))
                
                ##Do the output style specified
                if self.write_sourcecode:
                    self._write_source(sc, path, pyx, tag)
                    
                if self.display_sourcecode:
                    self._display_source(sc)

                    
    def fs_objwalk(self, fs_root,  depth=None):
        """
        Walk the filesystem from start directory indicated & to the depth indicated
        
        For each object and traverse into children and decompile - no unmarshaling
        
        No access to unmarshaling required 
        """
        #TODO depth, make decompiler independent
        from Decompilers.unpyc import liveUnPYC as live
        
        tag = "fs_obj"
        self._quiet_makedir(os.path.join(self.dump_dir, tag))
        
        lupc = live.liveUnPYC(self)
        
        fs_root = self.normalise_path(fs_root)
        
        ##Single file supplied no need to walk the directory
        if os.path.isfile(fs_root):
            
            #TODO single file memory traversal
            print "[-] single file memory traversal not supported yet"
            return
        
        for (path, dirs, pyx) in self._fs_walk(fs_root, depth, tag):
            
            print "[+] Decompiling in-memory '%s'...."%(pyx)
            
            subpath, package = os.path.split(path.strip("/"))
            ##Lazy, add path at start of path for eay import
            sys.path.insert(0, subpath)
            
            
            ##Attempt to import the .pyc/.pyo
            to_import = "%s.%s"%(package, os.path.splitext(pyx)[0])
            try:
                #TODO - account for relative imports ?
                print "[+] Importing: from %s import %s"%(package, os.path.splitext(pyx)[0])
                try:
                    p_obj = __import__(package, globals(), locals(), [os.path.splitext(pyx)[0]], -1)
                    p_obj = eval("p_obj.%s"%(os.path.splitext(pyx)[0]))
                except (ValueError, ImportError):
                    __import__(pyx)
                    p_obj = sys.modules[pyx]
                    
                print "[+] Imported %s  "%(p_obj)


            except Exception, err:
                print "[-] Error importing %s : %s"%(to_import, err)
                import traceback
                traceback.print_exc()
                raw_input()
                
                sys.path.remove(subpath)
                continue
                
   
            try:
                ##Pure memory decompile
                lupc.set_top_level_module(p_obj.__name__)
                sc   = lupc.get_py(p_obj)

                
            except Exception, err:
                import traceback
                print "[-] Error decompiling %s : %s"%(p_obj, err)
                traceback.print_exc()
                continue
    
            
            ##Do the output style specified
            if self.write_sourcecode:
                self._write_source(sc, path, pyx, tag)
                
            if self.display_sourcecode:
                self._display_source(sc)
                
                
            ##Keep syspath clean - remove what we added
            sys.path.remove(subpath) 
            
                    
    def mem_objwalk(self, obj):
        """
        Pure in-memory decompile.
        
        Start at the specified object and traverse into children and decompile
        
        No file system access, marshal access or bytecode access required
        """
        #TODO make decompiler independent
        from Decompilers.unpyc import liveUnPYC as live
        
        tag = "mem_obj"
        self._quiet_makedir(os.path.join(self.dump_dir, tag))
        
        ## No top level module specified so EVERYTHING encountered will be
        ## decompiled .....may take a while
        lupc = live.liveUnPYC(self) 
        sc   = lupc.get_py(obj)
        
        ##Do the output style specified
        try:
            name = "%s.py"%(obj.__name__)
        except:
            name = "%s.py"%(repr(obj))
            
        if self.write_sourcecode:
            self._write_source(sc, "", name , tag)
            
        if self.display_sourcecode:
            self._display_source(sc)

                    
                    
    def blind_mirror(self, orig_module, debug = False):
        """
        Mirror all the attributes of the module we are masquearding as so that we
        can be called as that module would be from other areas of the code and
        expected functionality is maintained
        
        IN:
           orig_module - the name of the module we are masquearding as - string
        OUT:
           True/False - success or failure - boolean
        """
        orig = __import__(orig_module)
        orig.__name__ = "orig"
        
        for atrr in dir(orig):
            if attr[:2] == "__":
                continue
        
            if debug:
                print "%s -> %s.%s"%(attr, attr.__file__, attr)
            exec("%s = orig.%s"%(attr, attr))    
            

    
    def _fs_walk(self, fs_root, depth, tag):
        """
        General function to walk a file system & yield up files which are pyc's
        
        Essentially walk & selectively yield path, dirs, file everything that matches
        criteria of .pyc or .pyo
        
        for .py just shortcut and dump
        """
            
        print "[+] Walking filesystem from %s"%(fs_root)        
        for (path, dirs, files) in os.walk(fs_root):
            
            for pyx in files:
                
                ##If the file is .py just dump it's contents - go straight to output
                if os.path.splitext(pyx)[1] == ".py":
                    f_py = open(os.path.join(path,pyx), "rb")
                    sc = f_py.read()
                    f_py.close
                    
                    ##Do the output as specified
                    if self.write_sourcecode:
                        self._write_source(sc, path, pyx, tag)
                        
                    if self.display_sourcecode:
                        self._display_source(sc)
                    
                ##Decompile .pyc/.pyo 
                elif os.path.splitext(pyx)[1] == ".pyc" or\
                   os.path.splitext(pyx)[1] == ".pyo" :
                
                    yield (path, dirs, pyx)
                    
                
                ##If the file is not .py/.pyc./.pyo skip it
                else:
                    continue
    
    def _display_source(self, source):
        """
        Print the source code to stdout
        """
        print "\n\n",source,"\n\n"
                    
    
    def _write_source(self, sourcecode, path, filename, tag):
        """
        Write the decompiled sourcecode to disk location
        """
        dump_dir = os.path.join(self.dump_dir, tag, path.strip(os.sep))
            
        #TODO - cleanup
        self._quiet_makedir(dump_dir)

        location = os.path.join(dump_dir, filename)
        
        ext = os.path.splitext(location)[1]

        if ext == ".pyc":
            location = location.replace(".pyc",".py")
        elif ext == ".pyo":
            location = location.replace(".pyo", ".py")
 
        try:
            f = open(location, "wb")
            f.write(sourcecode)
            f.close()
            print "[+] Source code written to: %s"%location
        except Exception, err:
            print "[-] Problem writing sourcecode to %s [%s]"%(location, err)
        
    