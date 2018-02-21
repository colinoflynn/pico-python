"""
OpenUnitAsync Demo.

By: Mark Harfouche

Shows how to use the openUnitAsync functionality.
On my computer, it takes 2.8 seconds to open the picoscope.
Maybe you want to do something useful with it :D.
"""

from __future__ import division
from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

import time
from picoscope import ps6000

if __name__ == "__main__":
    print(__doc__)

    ps = ps6000.PS6000(connect=False)

    print("Attempting to open Picoscope 6000...")

    ps.openUnitAsync()

    t_start = time.time()
    while True:
        (progress, completed) = ps.openUnitProgress()
        print("T = %f, Progress = %d, Completed = %d" %
              (time.time() - t_start, progress, completed))
        if completed == 1:
            break
        time.sleep(0.01)

    print("Completed opening the scope in %f seconds." %
          (time.time() - t_start))

    ps.close()
