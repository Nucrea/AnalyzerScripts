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
        
        try:
            self.module = AnalyzerModule("COM7")
        except:
            print("Port open err")
            exit()
        
        self.setWindowTitle("Управление мотором")
        self.w = QWidget(self)
        self.eSpeed = QLineEdit(self.w)
        self.bFwd = QPushButton(self.w)
        self.bBck = QPushButton(self.w)
        self.bStop = QPushButton(self.w)
        self.layout = QHBoxLayout()
        self.layout.addWidget(self.eSpeed)
        self.layout.addWidget(self.bFwd)
        self.layout.addWidget(self.bBck)
        self.layout.addWidget(self.bStop)
        self.setCentralWidget(self.w)
        self.w.setLayout(self.layout)
        
        self.bFwd.setText("Вперед")
        self.bBck.setText("Назад")
        self.bStop.setText("Стоп")
        
        self.bFwd.clicked.connect(self.fwd_clicked)
        self.bBck.clicked.connect(self.bck_clicked)
        self.bStop.clicked.connect(self.stop_clicked)
        
        
    def fwd_clicked(self):
        self.module.rotateForward( int(self.eSpeed.text()) )
            
    
    def bck_clicked(self):
        self.module.rotateBack( int(self.eSpeed.text()) )
            
    
    def stop_clicked(self):
        self.module.stop()


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    main = MainWindow()
    main.show()
    sys.exit(app.exec_())
            
            
            
