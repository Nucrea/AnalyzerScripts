import sys
import os
import msvcrt
import struct
import serial
import keyboard

import numpy as np
from enum import Enum
#from matplotlib import pyplot as plt
from collections import deque

from PyQt5 import QtWidgets
from PyQt5.QtWidgets import *
from PyQt5.QtSerialPort import QSerialPort
from PyQt5.QtCore import QTimer
from pyqtgraph import PlotWidget, plot
import pyqtgraph as pg

from AnalyzerModule import *


class MainWindow(QtWidgets.QMainWindow):

    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)
        
        self.setWindowTitle("Мониторинг тензодатчика")
        
        self.module = AnalyzerModule("COM28")
        time.sleep(1)
        self.x = np.arange(100)
        self.y = np.zeros(100)
        self.values = deque(self.y, 100)
        
        pg.setConfigOptions(antialias=True)
        self.graphWidget = pg.GraphicsLayoutWidget()
        self.plot = self.graphWidget.addPlot(0, 0, title="Сила (грамм)")
        self.plot.setYRange(150, -20, update=True)
        #self.setCentralWidget(self.graphWidget)
        
        self.timer = QTimer()
        self.timer.timeout.connect(self.tick_func)
        self.timer.start(50)
        
        self.vlayout = QVBoxLayout()
        self.hlayout = QHBoxLayout()
        
        self.btnTenzoToZero = QPushButton()
        self.btnTenzoToZero.setText("Обнулить тензо")
        self.btnTenzoToZero.clicked.connect(self.tenzoToZeroClicked)
        
        self.btnTenzoSetCoeff = QPushButton()
        self.btnTenzoSetCoeff.setText("Уст. коэффициент")
        self.btnTenzoSetCoeff.clicked.connect(self.tenzoSetCoeffClicked)
        
        self.editCoeff = QLineEdit()
        self.textValue = QLabel()
        
        self.vlayout.addWidget(self.btnTenzoToZero, 0)
        self.vlayout.addWidget(self.btnTenzoSetCoeff, 0)
        self.vlayout.addWidget(self.editCoeff, 0)
        self.vlayout.addWidget(self.textValue, 0)
        self.vlayout.addStretch(1)
        
        self.hlayout.addLayout(self.vlayout)
        self.hlayout.addWidget(self.graphWidget, 1)
        
        self.w = QWidget()
        self.w.setLayout(self.hlayout)
        self.setLayout(self.hlayout)
        self.setCentralWidget(self.w)
        
        self.mode = 0
        
    def tenzoToZeroClicked(self):
        self.module.tenzoToZero()
        
    def tenzoSetCoeffClicked(self):
        self.module.setTenzoCoeff( float(self.editCoeff.text()) )
        
    def tick_func(self):
        if (self.mode == 0):
            self.mode = 1
            self.module.moveRelative(100, 10, 50)
        if (self.mode == 1):
            if (self.module.isOperationFinished()):
                self.mode = 2
                self.module.moveRelative(20, 8, 250)
        if (self.mode == 2):
            if (self.module.isOperationFinished()):
                self.mode = 3
                self.module.moveBack()
        if (self.mode == 3):
            if (self.module.isOperationFinished()):
                self.mode = 0
    
        force = self.module.readForce()
        if force is not None:
            self.values.append(force)
            self.plot.plot(self.x, self.values, clear=True)
            self.textValue.setText("Посл. знач.: " + str(force))

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    main = MainWindow()
    time.sleep(2)
    main.show()
    sys.exit(app.exec_())
            
            
            
