@echo off
REM Set following to python version you want to use
REM Otherwise can comment out...
python -m pydoc -w picoscope
python -m pydoc -w picoscope.picobase
python -m pydoc -w picoscope.ps2000
python -m pydoc -w picoscope.ps2000a
python -m pydoc -w picoscope.ps3000
python -m pydoc -w picoscope.ps3000a
python -m pydoc -w picoscope.ps4000
python -m pydoc -w picoscope.ps5000a
python -m pydoc -w picoscope.ps6000
move *.html doc\.
