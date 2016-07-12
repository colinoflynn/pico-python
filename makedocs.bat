@echo off
REM Set following to python version you want to use
REM Otherwise can comment out...
set PYTHONBIN=c:\Python27-32bit
%PYTHONBIN%\python.exe %PYTHONBIN%\Lib\pydoc.py -w picoscope
%PYTHONBIN%\python.exe %PYTHONBIN%\Lib\pydoc.py -w picoscope.picobase
%PYTHONBIN%\python.exe %PYTHONBIN%\Lib\pydoc.py -w picoscope.ps2000
%PYTHONBIN%\python.exe %PYTHONBIN%\Lib\pydoc.py -w picoscope.ps2000a
%PYTHONBIN%\python.exe %PYTHONBIN%\Lib\pydoc.py -w picoscope.ps3000
%PYTHONBIN%\python.exe %PYTHONBIN%\Lib\pydoc.py -w picoscope.ps3000a
%PYTHONBIN%\python.exe %PYTHONBIN%\Lib\pydoc.py -w picoscope.ps4000
%PYTHONBIN%\python.exe %PYTHONBIN%\Lib\pydoc.py -w picoscope.ps5000a
%PYTHONBIN%\python.exe %PYTHONBIN%\Lib\pydoc.py -w picoscope.ps6000
move *.html doc\.
