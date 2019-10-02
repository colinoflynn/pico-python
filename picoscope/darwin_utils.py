from ctypes import cdll
from pathlib import Path
import shutil
import subprocess
import tempfile

import sys


def LoadLibraryDarwin(library):
    """Wrapper around cdll.LoadLibrary that works around how SIP breaks
    dynamically linked libraries. This improves upon the process described
    here:

    http://ulthiel.com/vk2utl/picoscope-python-interface-under-mac-os-x/
    """
    PICO_LIB_PATH = "/Applications/PicoScope6.app/Contents/Resources/lib/"

    # Libraries that depend on libiomp5.dylib
    IOMP5_DEPS = ["libpicoipp.dylib", "libpicoipp.1.dylib"]

    try:
        # Get the library normally. This should work if SIP is disabled and
        # DYLD_LIBRARY_PATH is set properly.
        return cdll.LoadLibrary(library)
    except OSError:
        # 2.7 Fix. This only fixes flake8
        if sys.version_info[0] == 2:
            FileNotFoundError = IOError
        if not Path(PICO_LIB_PATH).is_dir():
            raise FileNotFoundError(
                    "/Applications/PicoScope6.app is missing")

        # Modifying the libraries in-place breaks their signatures, causing
        # PicoScope6.app to fail to detect the oscilloscope.  Instead, patch
        # copies of the libraries in a temporary directory.
        tempLibDir = tempfile.TemporaryDirectory()
        patchedPicoPath = tempLibDir.name + "/lib/"
        shutil.copytree(PICO_LIB_PATH, patchedPicoPath)

        # Patch libraries that depend on libiomp5.dylib to refer to it by an
        # absolute path instead of a relative path, which is not allowed by
        # SIP.
        for libraryToPatch in IOMP5_DEPS:
            subprocess.run(["install_name_tool", "-change", "libiomp5.dylib",
                            patchedPicoPath + "/libiomp5.dylib",
                            patchedPicoPath + "/" + libraryToPatch
                            ]).check_returncode()

        # Finally, patch the originally requested library to look in the
        # patched directory.
        patchedLibrary = patchedPicoPath + "/" + library
        subprocess.run(["install_name_tool", "-add_rpath", patchedPicoPath,
                        patchedLibrary]).check_returncode()
        loadedLibrary = cdll.LoadLibrary(patchedLibrary)

        # Sneak the directory into the library so it's not deleted until the
        # library is garbage collected.
        loadedLibrary.tempLibDir = tempLibDir
        return loadedLibrary
