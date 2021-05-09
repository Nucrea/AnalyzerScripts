import sys
import os
import time
import socket
import math
from AnalyzerModule import *
from queue import Queue
from enum import IntEnum

#Точка с данными измерения
class Point:
    x = 0.0
    y = 0.0
    z = 0.0
    radius = 0.0
    delta = 0.0

#Держатель рабочих данных и флагов скрипта
class WorkData:
    flag_calibrated = False
    flag_error = False
    flag_busy = False
    flag_layer_ready = False
    flag_stop = False

    flag_tenzo = False
    flag_emg = False
    flag_measure = False
    modules = []
    model = []
    layer_step = 10.0
    layers_count = 10

#Команды, получаемые с ПК
class Commands(IntEnum):
    MEASURE = 0x41
    STOP = 0x42
    READ_MODEL = 0x43
    READ_STATUS = 0x44
    READ_ECHO = 0x45
    READ_LAST_LAYER = 0x46

#Обрабочтик команд, устанавливает флаги операций
class CommandHandler(object):
    def __init__(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.settimeout(0.001)
        self.socket.bind( ("127.0.0.1", 14002) )

    def processCommands(self, work_data):
        cmd = 0
        addr = None
        data = None
        try:
            data, addr = self.socket.recvfrom(1024)
            if (len(data)==0):
                return
            cmd = data[0]
        except:
            return

        if (cmd == Commands.STOP):
            work_data.flag_stop = True
            self.socket.sendto( bytes([1]), addr )

        elif (cmd == Commands.READ_ECHO):
            self.socket.sendto( bytes([1]), addr )

        elif (cmd == Commands.READ_STATUS):
            arr = bytearray([])
            arr.append(1 if work_data.flag_calibrated else 0)
            arr.append(1 if work_data.flag_error else 0)
            arr.append(1 if work_data.flag_busy else 0)
            arr.append(1 if work_data.flag_layer_ready else 0)
            arr.append( len(work_data.modules) )
            arr.append( len(work_data.model) )
            self.socket.sendto(arr, addr)

        elif (cmd == Commands.READ_LAST_LAYER):
            if work_data.flag_layer_ready:
                layer = work_data.model[-1]
                arr = bytearray([])
                for point in layer:
                    arr.extend( struct.pack("<f", point.x) )
                    arr.extend( struct.pack("<f", point.y) )
                    arr.extend( struct.pack("<f", point.z) )
                    arr.extend( struct.pack("<f", point.radius) )
                    arr.extend( struct.pack("<f", point.delta) )
                self.socket.sendto(arr, addr)
                work_data.flag_layer_ready = False
            else:
                self.socket.sendto( bytes([0]), addr )

        elif (cmd == Commands.MEASURE):
            work_data.flag_measure = True
            work_data.flag_tenzo = True if data[1]==1 else False
            work_data.layers_count = struct.unpack("<I", data[3:7])[0]
            work_data.layer_step = struct.unpack("<f", data[7:11])[0]
            self.socket.sendto( bytes([1]), addr )

        elif (cmd == Commands.READ_MODEL):
            arr = bytearray([])
            arr.append( len(work_data.model) )
            for layer in work_data.model:
                for point in work_data.model:
                    arr.extend( struct.pack("<f", point.x) )
                    arr.extend( struct.pack("<f", point.y) )
                    arr.extend( struct.pack("<f", point.z) )
                    arr.extend( struct.pack("<f", point.radius) )
                    arr.extend( struct.pack("<f", point.delta) )
            self.socket.sendto(arr, addr)

#Сохранить модель из WorkData
def saveModel(file_name, work_data):
    file = open(file_name, "w+")
    file.seek(0)

    for layer in work_data.model:
        counter = 1
        for point in layer:
            file.write( "%.4f;" % point.x )
            file.write( "%.4f;" % point.y )
            file.write( "%.4f;" % point.z )
            file.write( "%.4f;" % point.delta )
            file.write( "%i;" % counter )
            file.write("\r\n")
            counter += 1
    file.close()

#Ожидание завершения операций модулей
def waitOperationsFinished(modules, work_data, cmd_handler, sleep_time=0):
    if work_data.flag_stop:
        return

    while True:
        time.sleep(0.005)
        finished = True
        for module in modules:
            cmd_handler.processCommands(work_data)
            if work_data.flag_stop:
                break
            if not module.isOperationFinished(): finished = False
        if finished or work_data.flag_stop:
            break

    if work_data.flag_stop:
        for module in modules:
            module.stop()
        return

    if sleep_time!=0:
        vtimer = AnalyzerModule.VTimer()
        vtimer.start(sleep_time)
        while not vtimer.isFired():
            cmd_handler.processCommands(work_data)

#Сдвинуть заданные модули относительно
def moveModulesRelative(modules, delta, speed, force, delay, work_data, cmd_handler):
    if work_data.flag_stop:
        return

    for module in modules:
        cmd_handler.processCommands(work_data)
        module.moveRelative(delta, speed, force)
    waitOperationsFinished(modules, work_data, cmd_handler, delay)

#Отход заданных модулей назад
def moveModulesBack(modules, delay, work_data, cmd_handler):
    if work_data.flag_stop:
        return

    for module in modules:
        cmd_handler.processCommands(work_data)
        module.moveBack()
    waitOperationsFinished(modules, work_data, cmd_handler, delay)

#Начать измерение
def doMeasure(modules, shaft, work_data, cmd_handler):
    moveModulesBack(modules + [shaft], 0.5, work_data, cmd_handler)

    for i in range(work_data.layers_count):
        #Touch separately
        moveModulesRelative(modules, 150, 10, 40, 0.2, work_data, cmd_handler)
        rads1 = [(70.0 - module.readPosition()) for module in modules]

        #Measure delta (if tenzo flag is set)
        if work_data.flag_tenzo:
            moveModulesRelative(modules, 6, 8, 180, 0.2, work_data, cmd_handler)
            rads2 = [(70.0 - module.readPosition()) for module in modules]
        else:
            rads2 = rads1

        if not work_data.flag_stop:
            layer = []
            for j in range(8):
                point = Point()
                point.z = work_data.layer_step*(len(work_data.model))
                point.x = rads1[j]*math.cos(math.pi/2 + j * 6.28/8.0)
                point.y = rads1[j]*math.sin(math.pi/2 + j * 6.28/8.0)
                point.delta = rads1[j] - rads2[j]
                layer.append(point)
            work_data.model.append(layer)
            work_data.flag_layer_ready = True
        else:
            return

        if (i == work_data.layers_count-1):
            break

        #Back
        #moveModulesRelative(modules, -15, 12, 400, 0.2, work_data, cmd_handler)
        moveModulesBack(modules, 0.2, work_data, cmd_handler)

        #Z-Drive shift
        moveModulesRelative([shaft], work_data.layer_step, 10, 300, 0.2, work_data, cmd_handler)

    #Return after measure stop
    moveModulesBack(modules, 0.5, work_data, cmd_handler)
    moveModulesBack([shaft], 0.5, work_data, cmd_handler)


if __name__ == "__main__":

    work_data = WorkData()
    cmd_handler = CommandHandler()

    all_modules = AnalyzerModule.searchModules()
    modules = all_modules[0:8]
    shaft = all_modules[8] #Z-Привод

    while True:
        vtimer = AnalyzerModule.VTimer()
        vtimer.start(500)

        #Ждем команд, раз в 500мс проверяем ECHO модулей
        while not work_data.flag_measure:
            cmd_handler.processCommands(work_data)
            if vtimer.isFired():
                vtimer.start(500)
                for module in all_modules:
                    module.readEcho()

        work_data.flag_busy = True
        work_data.flag_layer_ready = False
        work_data.flag_stop = False
        work_data.model = []

        doMeasure(modules, shaft, work_data, cmd_handler)

        saveModel("model.csv", work_data)

        #Если экстренная остановка (из программы), отход всех модулей
        if (work_data.flag_stop):
            for module in modules:
                module.moveBack()
            while True:
                finished = True
                for module in modules:
                    cmd_handler.processCommands(work_data)
                    if not module.isOperationFinished():
                        finished = False
                if finished:
                    break

        work_data.flag_busy = False
        work_data.flag_measure = False
