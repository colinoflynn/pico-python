pico-python
===========
This is a Python 2.7+ library for the Pico Scope. It uses the provided DLL
for actual communications with the instrument. There have been a few examples
around, but this one tries to improve on them via:
  * Subclass instrument-specific stuff, so can support more families
  * Use exceptions to raise errors, and gives you nice english error messages (copied from PS Manual)
  * Provide higher-level functions (e.g. just setup timebase, function deals with instrument-specific limitations)

System has support for:
 * PS6000
 * PS5000A Class (PicoScope 5242A/5243A/5244A/5442A/5443A/5444A/5242B/5244B/5442B/5443B/5444B)
 * PS3000A Class (PicoScope 3204A/3204B/3205A/3205B/3206A/3206B/3207A/3207B/3204/3205/3206/3404A/3404B/3405A/3405A/3406A/3406B)
 * PS2000 Class (PicoScope 2104/2105/2202/2203/2204/2205/2204A/2205A)

Note the 'A' series covers a different ground than the non-A series! Check the programming manuals posted at http://www.picotech.com/document/ for details.

Installation Information
------------------------------
If you will be getting updated code from git, use git clone to put the directory
somewhere. Then do the following to generate a link to your git directory:
```
python setup.py develop
```

If you want the normal installation (e.g. copies files to Python installation) use:
```
python setup.py install
```

Currently the code is changing frequently. Thus you may wish to use the git clone + develop option to
keep up with new changes.


Similar Projects
------------------------------
PicoPy uses Cython to interface with a PicoScope 3000A
https://github.com/hgomersall/PicoPy


Authors, Copyright, and Thanks
------------------------------
pico-python is Copyright (C) 2013 By:
 * Colin O'Flynn <coflynn@newae.com>
 * Mark Harfouche <mark.harfouche@gmail.com>
 
 All rights reserved.
See LICENSE.md for license terms.

Inspired by Patrick Carle's code at http://www.picotech.com/support/topic11239.html
which was adapted from http://www.picotech.com/support/topic4926.html
