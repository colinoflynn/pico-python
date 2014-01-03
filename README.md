pico-python
===========
This is a Python 2.7+ library for the Pico Scope. It uses the provided DLL
for actual communications with the instrument. There have been a few examples
around, but this one tries to improve on them via:
  * Subclass instrument-specific stuff, so can support more families
  * Use exceptions to raise errors, and gives you nice english error messages (copied from PS Manual)
  * Provide higher-level functions (e.g. just setup timebase, function deals with instrument-specific limitations)

 o far INCOMPLETE and tested only with PS6000 scope. May change in the future.


Authors, Copyright, and Thanks
------------------------------
pico-python is Copyright (C) 2013 By:
 Colin O'Flynn <coflynn@newae.com>
 Mark Harfouche <mark.harfouche@gmail.com>
 All rights reserved.
See LICENSE.md for license terms.

Inspired by Patrick Carle's code at http://www.picotech.com/support/topic11239.html
which was adapted from http://www.picotech.com/support/topic4926.html