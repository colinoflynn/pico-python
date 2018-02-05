from setuptools import setup

setup(
    name = 'picoscope',
    version = '0.6.5',
    description = "Unofficial python wrapper for the PicoScope devices.",
    author = "Colin O'Flynn, Mark Harfouche",
    author_email = 'coflynn@newae.com, mark.harfouche@gmail.com',
    license = 'BSD',
    url = 'https://github.com/colinoflynn/pico-python/',
    download_url='https://github.com/colinoflynn/picoscope/tarball/0.6.5',
    packages = ['picoscope'],
    # See https://PyPI.python.org/PyPI?%3Aaction=list_classifiers
    classifiers = [
                     'Development Status :: 4 - Beta',
                     'Intended Audience :: Developers',
                     'Topic :: Software Development :: Libraries',
                     'Topic :: System :: Hardware',
                     'Topic :: Scientific/Engineering',
                     'License :: OSI Approved :: BSD License',
                     'Programming Language :: Python :: 2.7',
                     'Programming Language :: Python :: 3',
                 ],

                 # What does your project relate to?
                 keywords = 'picoscope peripherals hardware oscilloscope ATE',
    install_requires = ['numpy']
)
