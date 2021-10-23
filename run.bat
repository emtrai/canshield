@echo off

SET COMMAND=python3 can.py --logcan
echo %COMMAND%
%COMMAND%

set /p DUMMY=Hit ENTER to continue...