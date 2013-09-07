#pyREtic 0.5.1 README

Rich Smith - mynameismeerkat@gmail.com

Latest version of pyREtic can be found at: [https://github.com/MyNameIsMeerkat/pyREtic](https://github.com/MyNameIsMeerkat/pyREtic)


##What is it ?

**pyREtic** is an extensible framework to assist in performing various reverse  engineering tasks for Python language projects.

It assists a reverse engineer in gaining sourcecode (.py's) back from bytecode (.pyc's), in particular it assists when the code that is being reversed has put some effort into trying to stop decompilation using standard toolsets.

It consists of 3 main parts:

* **REpdb** : A RE centric superset of the pdb functionality to allow the easy interaction by a reverser to the code they are reversing.
              
* **OpcodeRemap** : The component that is able to deduce a new opcode table from a Python runtime that has changed its opcode layout in order to confuse many standard Python decompilers.
                    
* **LiveUnpyc** : An extension to Dmitri Kornev's UnPyc decompiler project [http://unpyc.sourceforge.net/](http://unpyc.sourceforge.net/) which allows live Python objects in memory to be decompiled back to Python sourcecode via 3 different methods.
                  
                  
The capabilities within the pyREtic toolkit were written to be effective against the protections that a majority of closed source Python developers were using to protect the code they were distributing from being read in its source form.

The output from pyREtic was to produce a source code representation of an object to which you could gain access to in a running instance of the target application. This representation only needed to be good enough to be able to assess the security of the target application rather than being absolutely perfect copy.

##HowTo

A detailed howto document can be found in the `docs/` directory.

##License

pyREtic is released under the GPLv3 which can be found in the `docs/` directory or [GPLv3](http://www.gnu.org/licenses/gpl.html).

Other components which pyREtic uses are released under their own licenses:

UnPyc [http://unpyc.sourceforge.net/](http://unpyc.sourceforge.net/)         : BSD License   
pycallgraph [http://pycallgraph.slowchop.com/](http://pycallgraph.slowchop.com/): GPLv2


##History

pyREtic began life when I worked at Immunity Inc, and was first publicly presented at the BlackHat 2010 conference in Las Vegas, and then at Defcon 17. A paper that accompanied its release can be found in the `docs/` dir

I am now no longer employed by Immunity but Dave Aitel was kind enough to allow me to release the code under the GPL to allow people to access it and allow its development to continue.

The latest version of the framework can be found at [https://github.com/MyNameIsMeerkat/pyREtic](https://github.com/MyNameIsMeerkat/pyREtic).

I recently moved the project to a new home on GitHub due to renewed interest from some in the community and will be releasing some enhancements that until now never saw the light of day.


##Future
The features that will be added to pyREtic in future will reflect the development of my needs for dealing with reversing Python applications moving forward. If you have suggestions however let me know.


##Technical Details
For those interested more of the technicalities of how pyREtic does things can be found in the paper `pyREtic: In memory reverse engineering for obfuscated Python bytecode` which is in the `docs/` directory, and a presentation discussing it can be found at : 

[http://prezi.com/kmyvgiobsl1d/pyretic-rich-smith-blackhatdefcon-2010]()


