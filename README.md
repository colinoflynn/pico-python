# pico-python
[![Build Status](https://travis-ci.org/colinoflynn/pico-python.svg?branch=master)](https://travis-ci.org/colinoflynn/pico-python)

This is a Python 2.7+ library for the Pico Scope. It uses the provided DLL
for actual communications with the instrument. There have been a few examples
around, but this one tries to improve on them via:
  * Subclass instrument-specific stuff, so can support more families
  * Use exceptions to raise errors, and gives you nice English error messages (copied from PS Manual)
  * Provide higher-level functions (e.g. just setup timebase, function deals with instrument-specific limitations)
  * Supports both Windows and Linux and Mac

System has support for:
 * PS6000
 * PS5000A Class (PicoScope 5242A/5243A/5244A/5442A/5443A/5444A/5242B/5244B/5442B/5443B/5444B)
 * PS4000A Class (PicoScope 4444/4824)
 * PS3000 Class (PicoScope 3204/3205/3206/3224/3424/3425)
 * PS3000A Class (PicoScope 3204A/3204B/3205A/3205B/3206A/3206B/3207A/3207B/3204/3205/3206/3404A/3404B/3405A/3405A/3406A/3406B)
 * PS2000 Class (PicoScope 2104/2105/2202/2203/2204/2205/2204A/2205A)
 * PS2000A Class (PicoScope 2206/2206A/2206B/2207/2207A/2207B/2208/2208A/2208B/2205A MSO/2206B MSO/2207B MSO/2208B MSO/2405A/2406B/2407B/2408B)

Note the 'A' series covers a different ground than the non-A series! Check the programming manuals posted at http://www.picotech.com/document/ for details.


## Installation
You need to install the Python module as well as the Picoscope libraries for your Operating system.

### Module installation
#### PyPi
```
pip install picoscope
```

#### Git
If you are developping the library, or need some feature that we haven't pushed to PyPi yet, use
git clone to put the directory somewhere.
Then use the setup.py script to install the library in development mode:
```bash
git clone git@github.com:colinoflynn/pico-python.git
cd pico-python
python setup.py develop
```

### OS specific
#### Windows
You will require the PicoScope DLLs for this package to work. The easiest method is to install the latest PicoScope software
or SDK from https://www.picotech.com/downloads .

#### Linux
Install the PicoScope Beta for Linux version of PicoScope as describe under Getting DLL's (above).  Currently this is the only way to install the shared libraries (SDK)

Once you have PicoScope running you need to add your login account to the pico group in order to access the USB.  The examples will crash if you don't have permission to use the USB.  This is true for use of the shared libraries in general, even if you're not using pico-python.

```
useradd -G pico $USER
```

#### Mac OSX
You either want to add this every time before you start python or IPython, but I think it is best to add this line to
`.bash_profile` (or the Mac Equivalent ????).
```bash
export DYLD_LIBRARY_PATH=$DYLD_LIBRARY_PATH:/Applications/PicoScope6.app/Contents/Resources/lib
```

Recently, this directory has moved to a new location See [Issue #143](https://github.com/colinoflynn/pico-python/issues/143)
```
export DYLD_LIBRARY_PATH="$DYLD_LIBRARY_PATH:/Applications/PicoScope 6.app/Contents/Resources/lib"
```

See [Issue 80](https://github.com/colinoflynn/pico-python/issues/80#issuecomment-314149552) for more information on how this was found.

You should also add yourself to the pico group so that your user has access to the picoscope as a USB device
```bash
# Create the new pico group :
sudo dseditgroup -o create pico
# Add the current user to the pico group :
sudo dseditgroup -o edit -a $USER -t user pico
```

### Using Anaconda/Conda
Seems like Anaconda has an issue with ctypes. See the comment [here](https://github.com/pymedusa/Medusa/issues/1843#issuecomment-310126049) imdatacenters says to:
> If you are using a special version of Python [like Anaconda] and you can't fix it.
> Navigate to line 362 of lib/ctypes/init.py and change it to:
> `self._handle = _dlopen(str(self._name), mode)`

# Similar Projects
PicoPy uses Cython to interface with a PicoScope 3000A
https://github.com/hgomersall/PicoPy

Picoscope offers their official wrappers,
https://github.com/picotech/picosdk-python-wrappers

# Authors, Copyright, and Thanks
pico-python is Copyright (C) 2013 By:
 * Colin O'Flynn <coflynn@newae.com>
 * Mark Harfouche <mark.harfouche@gmail.com>

All rights reserved.
See LICENSE.md for license terms.

Inspired by Patrick Carle's code at http://www.picotech.com/support/topic11239.html
which was adapted from http://www.picotech.com/support/topic4926.html

# Contributing
1. Fork.
2. Make a new branch.
3. Commit to your new branch.
4. Add yourself to the authors/acknowledgments (whichever you find appropriate).
5. Submit a pull request.

Alternatively, you can follow more thorough instructions
[here](http://scikit-image.org/docs/dev/contribute.html).

# Developer notes
Commit and create a new tag with git
```
git commit
git tag -a X.Y.Z -m "Short descriptive message"
```

Push the tags to the repo
```
git push origin X.Y.Z
```

or to push all tags
```
git push --tags
```

[versioneer](https://github.com/warner/python-versioneer) takes care of updating the version.
New tags will be pushed to PyPi automatically by Travis.
