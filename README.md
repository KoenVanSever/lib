# LIB

This repository consists of specific libraries written for easier handling of data/...

## PYLIB

Pylib contain python files that can be used in different projects.

- scopeparser.py: parser scope with classmethods `from_isf()` and `from_alb()` which represent data from Tektronix scopes and Agilent/Keysight scopes respectively
    - internal dependency -> [scope_functions.py](scope_functions.py)
- pandasscopeparser.py: same use as scopeparser.py --> <b>DEPRECATED!</b>
    - internal dependency -> [scope_functions.py](scope_functions.py)
- scope_functions.py: consists of set of function that are usefull in handling numeric data from scopes (rms, avg, alpha-filter, ...)
- tek_connect.py: handles connection with tektronix scopes using VISA protocol
- agilent_connect.py: handles connection with agilent/keysight scopes using VISA protocol
- wrappers.py: if handy selfmade wrappers/decorators are defined, put them here
- safeserial.py: inherited class from Serial (pyserial package) to be able to handle serial debug communication with SafeLED more efficiëntly
    (safeserial_old.py: old version --> <b>DEPRECATED</b>)
- asp.py: Rx -> takes readouts from HPC input measurement and process them to useful data

