import time
import sys
import os
from AnalyzerModule import *


if __name__ == '__main__':

    modules = [ AnalyzerModule.searchModules()[3] ]
    
    if len(modules)==0:
        exit()

    while True:
        for module in modules:
            module.doTouch()
        AnalyzerModule.waitOperationsFinished(modules)
            
        for module in modules:
            module.moveBack()
        AnalyzerModule.waitOperationsFinished(modules)
