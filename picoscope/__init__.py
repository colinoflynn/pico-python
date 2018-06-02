__author__ = "Colin O'Flynn, Mark Harfouche"
__license__ = "FreeBSD"

__all__ = ["ps2000",
           "ps2000a",
           "ps3000",
           "ps3000a",
           "ps4000",
           "ps4000a",
           "ps5000a",
           "ps6000"]

from ._version import get_versions
__version__ = get_versions()['version']
del get_versions
