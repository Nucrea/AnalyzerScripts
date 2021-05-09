import time
import sys
import os
from AnalyzerModule import *
import serial.tools.list_ports as list_ports


#Filter comports
devices = filter((lambda x: 'arduino' in x[1].lower() or 'ch340' in x[1].lower()), list_ports.comports())
ports = [AnalyzerModule(x[0]) for x in devices]

#Filter modules
time.sleep(2)
modules = [x for x in ports if x.readEcho()]
module = modules[0]


while True:
    module.moveBack()
    AnalyzerModule.waitOperationsFinished(modules)

    #module.doTouch()
    #AnalyzerModule.waitOperationsFinished(modules)

    module.doTouchAndMeasure()
    AnalyzerModule.waitOperationsFinished(modules)
        
    print("----------------------")
    print("Радиус точки:", "{0:.1f}".format(75.0 - module.readMeasuredRadius()), 'mm')
    print("Жесткость:", "{0:.1f}".format(module.readMeasuredStiffness()) )
    print("Дельта расстояния:", "{0:.1f}".format(module.readMeasuredRadiusDelta()), "mm")
