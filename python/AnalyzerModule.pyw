import sys
import os
import time
import struct
import serial

import numpy as np
from enum import Enum
from enum import IntEnum

import serial.tools.list_ports as list_ports


class AnalyzerModule(serial.Serial):

    CALIBRATED_IDS = [0xA0, 0xA1, 0xA2, 0xA3, 0xA4, 0xA5, 0xA6, 0xA7, 0xA8]

    #Virtual timer
    class VTimer(object):
        def __init__(self):
            self.is_active = False
            self.time_point = 0

        def getTimeMS(self):
            return round(time.time() * 1000)

        def start(self, period):
            self.time_point = period + self.getTimeMS()
            self.is_active = True

        def stop(self, period):
            self.is_active = False

        def isFired(self):
            if (self.is_active):
                if (self.getTimeMS() - self.time_point >= 0):
                    self.is_active = False
                    return True
            return False

    class Operations(IntEnum):
        NONE = 0
        MOVE = 1
        MOVE_BACK = 2
        MOVE_FORWARD = 3
        TOUCH = 4
        MEASURE = 5
        TOUCH_AND_MEASURE = 6

    class Status(IntEnum):
        OK = 0
        EXECUTING = 1
        STOPPED = 2
        ERROR = 3

    class Commands(IntEnum):
        SET_POSITION_MODE = 1
        SET_POSITION = 2
        SET_SPEED = 3
        SET_FORCE = 4
        ECHO = 5
        STOP = 6
        START_OPERATION = 7
        SET_ID = 8
        READ_ID = 9
        READ_SENSORS = 10
        READ_STATUS = 11
        TENZO_TO_ZERO = 0xA1
        SET_TENZO_COEFF_L = 0xA2
        SET_TENZO_COEFF_H = 0xA3
        SIMPLE_ROTATE_FORWARD = 0xF1
        SIMPLE_ROTATE_BACK = 0xF2

    class SensorsArguments(IntEnum):
        BUTTON_BACK = 1
        BUTTON_FORWARD = 2
        BUTTON_TOUCH = 3
        FORCE = 4
        SPEED = 5
        POSITION = 6

    class StatusArguments(IntEnum):
        IS_OPERATION_FINISHED = 1
        STATUS = 2
        TRIGGER = 3
        RADIUS = 4
        STIFFNESS = 5
        EMG = 6
        RADIUS_DELTA = 7

    class PositionMode:
        ABSOLUTE = 0
        RELATIVE = 1

    TYPES_CHAR = { 'float': 'f', 'u16': 'H', 'i16': 'h', 'u8': 'B', 'i8': 'b', 'bool': '?' }
    TYPES_SIZE = { 'float': 4, 'u16': 2, 'i16': 2, 'u8': 1, 'i8': 1, 'bool': 1 }

    def __init__(self):
        super().__init__(timeout=0.020)

    def __init__(self, port):
        super().__init__(port, 115200, timeout=0.020)

    #Однократная попытка записи\чтения данных модуля
    def writeAndRead_try(self, cmd, arg, type_str):
        try:
            dataBytes = 2 + self.TYPES_SIZE[type_str]
            self.read(self.in_waiting)
            self.write( struct.pack("<Hh", cmd, arg) )
            arr = self.read(dataBytes)
            if (len(arr)!=dataBytes or self.in_waiting!=0):
                return None
            else:
                ret_cmd, value = struct.unpack("<H" + self.TYPES_CHAR[type_str], arr)
                return value if ret_cmd==cmd else None
        except Exception:
            return None

    #Серия попыток чтения\записи
    def writeAndRead(self, cmd, arg, type_str):
        for i in range(4):
            result = self.writeAndRead_try(cmd, arg, type_str)
            if (result is not None):
                return result
        raise ValueError("Can't pefrorm module R/W task")

    #----------------------------------------------------------------------------------------------------------
    #Base func
    def readEcho(self):
        return self.writeAndRead(self.Commands.ECHO, 0, 'u8') == self.Commands.ECHO

    def readEchoNoexcept(self):
        try:
            return self.writeAndRead(self.Commands.ECHO, 0, 'u8') == self.Commands.ECHO
        except:
            return False

    def stop(self):
        return self.writeAndRead(self.Commands.STOP, 0, 'u8')

    def startOperation(self, operation):
        return self.writeAndRead(self.Commands.START_OPERATION, operation, 'u8')

    def setID(self, b_id):
        return self.writeAndRead(self.Commands.SET_ID, b_id, 'u8')

    def readID(self):
        return self.writeAndRead(self.Commands.READ_ID, 0, 'u8')

    #----------------------------------------------------------------------------------------------------------
    #Read sensors and values group
    def readButtonBack(self):
        return self.writeAndRead(self.Commands.READ_SENSORS, self.SensorsArguments.BUTTON_BACK, 'bool')

    def readButtonForward(self):
        return self.writeAndRead(self.Commands.READ_SENSORS, self.SensorsArguments.BUTTON_FORWARD, 'bool')

    def readButtonTouch(self):
        return self.writeAndRead(self.Commands.READ_SENSORS, self.SensorsArguments.BUTTON_TOUCH, 'bool')

    def readForce(self):
        return self.writeAndRead(self.Commands.READ_SENSORS, self.SensorsArguments.FORCE, 'i16')

    def readSpeed(self):
        return self.writeAndRead(self.Commands.READ_SENSORS, self.SensorsArguments.SPEED, 'float')

    def readPosition(self):
        return self.writeAndRead(self.Commands.READ_SENSORS, self.SensorsArguments.POSITION, 'float')

    #----------------------------------------------------------------------------------------------------------
    #Read module status and measured data
    def isOperationFinished(self):
        return self.writeAndRead(self.Commands.READ_STATUS, self.StatusArguments.IS_OPERATION_FINISHED, 'bool')

    def readOperationStatus(self):
        return self.writeAndRead(self.Commands.READ_STATUS, self.StatusArguments.STATUS, 'u8')

    def readOperationTrigger(self):
        return self.writeAndRead(self.Commands.READ_STATUS, self.StatusArguments.TRIGGER, 'u8')

    def readMeasuredRadius(self):
        return self.writeAndRead(self.Commands.READ_STATUS, self.StatusArguments.RADIUS, 'float')

    def readMeasuredStiffness(self):
        return self.writeAndRead(self.Commands.READ_STATUS, self.StatusArguments.STIFFNESS, 'float')

    def readMeasuredEmg(self):
        return self.writeAndRead(self.Commands.READ_STATUS, self.StatusArguments.EMG, 'float')

    def readMeasuredRadiusDelta(self):
        return self.writeAndRead(self.Commands.READ_STATUS, self.StatusArguments.RADIUS_DELTA, 'float')

    #----------------------------------------------------------------------------------------------------------
    #Module operations
    def moveRelative(self, delta, speed, force):
        self.writeAndRead(self.Commands.SET_POSITION_MODE, self.PositionMode.RELATIVE, 'u8')
        self.writeAndRead(self.Commands.SET_POSITION, int(delta), 'u8')
        self.writeAndRead(self.Commands.SET_SPEED, speed, 'u8')
        self.writeAndRead(self.Commands.SET_FORCE, force, 'u8')
        return self.writeAndRead(self.Commands.START_OPERATION, self.Operations.MOVE, 'u8')

    def moveBack(self):
        return self.writeAndRead(self.Commands.START_OPERATION, self.Operations.MOVE_BACK, 'u8')

    def moveForward(self):
        return self.writeAndRead(self.Commands.START_OPERATION, self.Operations.MOVE_FORWARD, 'u8')

    def doTouch(self):
        return self.writeAndRead(self.Commands.START_OPERATION, self.Operations.TOUCH, 'u8')

    def doTouchAndMeasure(self):
        return self.writeAndRead(self.Commands.START_OPERATION, self.Operations.TOUCH_AND_MEASURE, 'u8')

    def rotateForward(self, sps):
        return self.writeAndRead(self.Commands.SIMPLE_ROTATE_FORWARD, sps, 'u8')

    def rotateBack(self, sps):
        return self.writeAndRead(self.Commands.SIMPLE_ROTATE_BACK, sps, 'u8')

    #----------------------------------------------------------------------------------------------------------
    #Tenzo calibration functions
    def tenzoToZero(self):
        return self.writeAndRead(self.Commands.TENZO_TO_ZERO, 0, 'u8')

    def setTenzoCoeff(self, coeff):
        values = struct.unpack('<hh', struct.pack('<f', coeff) )
        self.writeAndRead(self.Commands.SET_TENZO_COEFF_L, values[0], 'u16')
        return self.writeAndRead(self.Commands.SET_TENZO_COEFF_H, values[1], 'u16')

    #----------------------------------------------------------------------------------------------------------
    #Поиск доступных модулей
    @staticmethod
    def searchModules():
        comports = filter((lambda x: 'arduino' in x[1].lower() or 'ch340' in x[1].lower()), list_ports.comports())
        devices = [AnalyzerModule(comport[0]) for comport in comports]
        time.sleep(2)
        modules = filter((lambda device: device.readEchoNoexcept()), devices)
        modules = sorted(modules, key=lambda module: module.readID(), reverse=False)
        return modules

    #Откалиброваны ли модули
    @staticmethod
    def isModulesCalibrated(modules):
        ids = [module.readID() for module in modules]
        print(ids)
        print(AnalyzerModule.CALIBRATED_IDS)
        return (AnalyzerModule.CALIBRATED_IDS == ids)

    #Ожидание завершения операций на всех заданных модулях
    @staticmethod
    def waitOperationsFinished(modules, sleep_time=0):
        while True:
            time.sleep(0.005)
            finished = True
            for module in modules:
                if not module.isOperationFinished():
                    finished = False
            if finished:
                break
        if (time!=0): time.sleep(sleep_time)

    #Ожидание завершения операции данного модуля
    def waitOperationFinished(self, sleep_time=0):
        while True:
            time.sleep(0.005)
            if  self.isOperationFinished():
                break
        if (time!=0): time.sleep(sleep_time)
