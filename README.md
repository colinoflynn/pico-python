pico-python
===========
This is a Python 2.7+ library for the Pico Scope. It uses the provided DLL
for actual communications with the instrument. There have been a few examples
around, but this one tries to improve on them via:
  * Subclass instrument-specific stuff, so can support more families
  * Use exceptions to raise errors, and gives you nice english error messages (copied from PS Manual)
  * Provide higher-level functions (e.g. just setup timebase, function deals with instrument-specific limitations)
  * Supports both Windows and Linux

System has support for:
 * PS6000
 * PS5000A Class (PicoScope 5242A/5243A/5244A/5442A/5443A/5444A/5242B/5244B/5442B/5443B/5444B)
 * PS3000 Class (PicoScope 3204/3205/3206/3224/3424/3425)
 * PS3000A Class (PicoScope 3204A/3204B/3205A/3205B/3206A/3206B/3207A/3207B/3204/3205/3206/3404A/3404B/3405A/3405A/3406A/3406B)
 * PS2000 Class (PicoScope 2104/2105/2202/2203/2204/2205/2204A/2205A)
 * PS2000A Class (PicoScope 2206/2206A/2206B/2207/2207A/2207B/2208/2208A/2208B/2205A MSO/2206B MSO/2207B MSO/2208B MSO/2405A/2406B/2407B/2408B)

Note the 'A' series covers a different ground than the non-A series! Check the programming manuals posted at http://www.picotech.com/document/ for details.

Getting DLLs
------------

You will require the PicoScope DLLs for this package to work. The easiest method is to install the latest PicoScope software
or SDK from https://www.picotech.com/downloads .

Installation Information from PyPI
----------------------------------

You can install the program with a simple:
```
pip install picoscope
```

You will require the DLLs (described above).



Installation Information from GIT
---------------------------------
If you will be getting updated code from git, use git clone to put the directory
somewhere. Then do the following to generate a link to your git directory:
```
python setup.py develop
```

If you want the normal installation (e.g. copies files to Python installation) use:
```
python setup.py install
```

Additional Installation Information for Linux
---------------------------------------------
Install the PicoScope Beta for Linux version of PicoScope as describe under Getting DLL's (above).  Currently this is the only way to install the shared libraries (SDK)

Install pico-python using either method described above.

Once you have PicoScope running you need to add your login account to the pico group in order to access the USB.  The examples will crash if you don't have permission to use the USB.  This is true for use of the shared libraries in general, even if you're not using pico-python.

```
useradd -G pico <username>
```

Finally, you need to log in again for the group change to pick up:

```
su <username>
```
Additional Installation Information for Mac OSX
---------------------------------------------
You either want to add this everytime before you start python or ipython, but I think it is best to add this line to 
`.bash_profile` (or the Mac Equivalent ????).
```bash
export DYLD_LIBRARY_PATH=$DYLD_LIBRARY_PATH:/Applications/PicoScope6.app/Contents/Resources/lib
```

See [Issue 80](https://github.com/colinoflynn/pico-python/issues/80#issuecomment-314149552) for more information on how this was found.
Unfortunately, I don't have a Mac so I can't test this for myself. Feel free to create an Issue so that we can update these instructions.

You should also add yourself to the pico group so that your user has access to the picoscope as a USB device
```bash
# Create the new pico group :
sudo dseditgroup -o create pico
# Add the current user to the pico group :
sudo dseditgroup -o edit -a $USER -t user pico
```
Additional Instructions for installs using Anaconda/Conda
---------------------------------------------------------
Seems like Anaconda has an issue with ctypes. See the comment [here](https://github.com/pymedusa/Medusa/issues/1843#issuecomment-310126049) imdatacenters says to:
> If you are using a special version of Python [like Anaconda] and you can't fix it.
> Navigate to line 362 of lib/ctypes/init.py and change it to:
> `self._handle = _dlopen(str(self._name), mode)`


Driver woes
-----------
If you are having issues installing the driver, you can try to install the original drivers that came with your CD, then upgrading as mentionned in [Issue #103](https://github.com/colinoflynn/pico-python/issues/103). As always, try installing, then rebooting your computer. I would also suggest trying to run Picoscope's included graphical interface to ensure that your scope is working.


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

Contributing
------------------------------
1. Fork.
2. Make a new branch.
3. Commit to your new branch.
4. Add yourself to the authors/acknowledgements (whichever you find appropriate).
5. Submit a pull request.

Developer notes
------------------------------
To update versions, make sure to update the version tag in a few locations
1. `setup.py`
    - `version = X.Y.Z`
    - `download_url = [...]/X.Y.Z`
2. `picoscope/__init__.py`
    - `__version__ = "X.Y.Z"`

Once the versions have been updated, commit and create a new tag with git
```bash
git commit
git tag -a X.Y.Z -m "Short descripted message"
```

Push the tags to the repo
```bash
git push origin X.Y.Z
```

or to push all tags
```bash
git push --tags
```


