import time
import sys
import os
from AnalyzerModule import *
import serial.tools.list_ports as list_ports


modules = [ AnalyzerModule.searchModules()[0] ]


while True:
    for module in modules:
        module.moveBack()
    AnalyzerModule.waitOperationsFinished(modules)
    time.sleep(0.5)

    for module in modules:
        module.moveRelative(30, 12, 100)
    AnalyzerModule.waitOperationsFinished(modules)
    time.sleep(0.5)
    
    for module in modules:
        module.moveRelative(30, 12, 100)
    AnalyzerModule.waitOperationsFinished(modules)
    time.sleep(0.5)
    
    for module in modules:
        module.moveRelative(30, 12, 100)
    AnalyzerModule.waitOperationsFinished(modules)
    time.sleep(0.5)
