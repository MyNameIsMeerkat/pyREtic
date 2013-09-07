pyREtic/REpdb HowTo
===================
v 0.5.1
Rich Smith - mynameismeerkat <@t> gmail.com

Latest version of pyREtic can be found at:

Homepage:
http://code.google.com/p/pyretic/
Mirror:
http://www.immunityinc.com

Command specific help
================================================================================
When at the REpdb command line type `help` for a full list of commands (both REpdb
 and pdb), `help <command>` will give more info about how to use each specific
command.

`q` or `quit` will drop you out of the REpdb command line.

`c`, `n` etc have the same effect as they do with standard pdb.


Getting 'in process'
================================================================================
To begin reversing a closed source Python application you need to get into the
running Python process of that application. Most obfuscated applications will come
packaged with their own modified Python runtime (an output from Py2Exe, Py2App, 
cxfreeze etc). Depending on the modifications that have been made to the runtime
and the packager used you can get 'in process' a few different ways. The easiest
is often to replace an obfuscated .pyc with a .py of the same name which you 
control, due to the logic of import.c in the Python runtime your .py should be 
loaded and from that point you can call into REpdb. For example:

* rename foo_app.pyc to foo_app_orig.pyc
* create file foo_app.py to be loaded
* place the pyREtic directory in the same directory as foo_app.py

The contents of foo_app.py could be as simple as:

<snip>

import sys, os
sys.path.append(os.path.join(".", "pyREtic"))

from pyREtic import REpdb
REpdb.set_trace()

</snip>

Now when you start the application you should be dropped to the REpdb shell
interface from where you can take a variety of actions.

If in order to bootstrap the application without crashing you need to replicate
the functionality of the file you renamed you can do this quite simply by calling:

<snip> 

import foo_app_orig
REpdb.obj_mirror(foo_app_orig)

</snip>

This will essentially make your module act as a proxy between the rest of the 
application and the  module you renamed.


Remapping and Decompilation
================================================================================

Use Auto mode to do steps 1-9 below for opcode remapping automagically
--------------------------------------------------------------------------------
From the REpdb interface:
    
    1. auto_remap <path to obfuscated app>
       e.g. auto-remap /_mp/ClosedSourceApp/lib/python2.5/site_packages
       
    2. Restart REpdb
    
    3. set_project auto-remap    **IMPORTANT!!!**
    
    4. Goto Step 12 below


Quick Start for manual control
--------------------------------------------------------------------------------
From the REpdb interface:
    
    1. Create a new project:
        `set_project example_project`
        
    2. The version of the python runtime you are in will then be detected, you
       will be prompted to pick the version you want to associate with this project
       or enter your own
       
    3. If the version of Python detected/chosen has not be downloaded pyREtic
       will ask to do so - this is so pyREtic has access to stdlib python files
       which are not obfuscated or altered
       
    4. Once downloaded and unpacked, the required modules will be copied to the
       projects module store
    
    If the Python bytecode has its opcode table remapped:

    5.  Generate a set of reference .pyb files using the downloaded Python
        `gen_ref`
        or if you have a particular set of modules you want to generate over
        `gen_ref <path to modules> `
        
    6.  Generate a set of .pyb's for the obfuscated .pyc's
        `gen_obf <path to obfuscated modules>`
         e.g. gen_obf /tmp/ClosedSourceApp/lib/python2.5/site_packages
         
    7.  Now remap the opcode table with the two sets of pyb's generated
        `remap`
        
    8.  Now swap the standard opcode tables for the remapped ones so we can decompile
        `swap_opcodes`
        
    9.  Currently pyREtic needs to be restarted here to take account of the new
        opcode tables :( [Will be fixed soon]
        `quit`
        
    10. Restart REpdb [this loads REpdb with your newly generated opcdoe tables]
    
    11. Resume your previous project
        `set_project example_project`
    
    
    If Python bytecode is not remapped start here:
        
    12 Decompile using the style most suitable to the obfuscated environment you are in. 
       The decompilation target can be either a single .py file or a directory. 
    
       * Walk the filesystem, getting module code via the marshal module 
         (requires both marshal module and filesystem access from the obfuscated runtime)
        
         `fs_um_decompile <path to pyc's to decompile>`
          e.g. fs_um_decompile /tmp/ClosedSourceApp/lib/python2.5/site_packages/TheAppDir
          
        * Walk the filesystem, getting module code via object interrogation
         (only requires filesystem access from the obfuscated runtime NOT the marshal module)
        
         `fs_mem_decompile <path to pyc's to decompile>`
          e.g. fs_mem_decompile /tmp/ClosedSourceApp/lib/python2.5/site_packages/TheAppDir
          
        * Walk the object hierachy, getting code via object interogation 
         (does NOT require either the marshal module or tfilesystem access to pyc files)
        
         `pure_mem_decompile <instantiated_object_to_decompile>`
          e.g. pure_mem_decompile TheApp.SecretCode

     [NOTE: When decompiling there will be A LOT of output, some may even make you think 
            things are not working. For the most part this can be ignored safely, in future
            versions this will get cleaned up :) ]

     13 The sourcecode produced will be in the 'sourcecode' directory of the pyREtic project
        you have created, a full path to it's location should be given at the end of the
        decompile.
    
    
Producing a callgraph
================================================================================
REpdb allows the simple creation of a callgraph using the pycallgraph module by
Gerald Kaszuba (http://pycallgraph.slowchop.com/).
To start the calligraphy trace simply use the following command at the REpdb prompt:

	`start_callgraph my_callgraph_name`

Then allow the application to continue its execution either through stepping through
using the `n` command of pdb, or just allow the whole application to continue by using
`c`. 

If REpdb is exited or the program crashes, an atexit hook *should* stop the trace 
and produce the calligraphy automatically. If you want to stop the calligraphy after a
certain operation has taken place then use the command:

	`stop_callgraph`

This allows you to graph out the functionality of an application which is obfuscated to 
you. This may well provide you the information you need to focus your reverse engineering
effort on interesting areas.