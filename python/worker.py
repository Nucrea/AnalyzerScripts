import sys
import os
import serial
import serial.tools.list_ports as list_ports
from subprocess import Popen, PIPE

from AnalyzerModule import *


AVRDUDE_MODULE = "avrdude -c arduino -b 57600 -p atmega328p -P {0} -u -U flash:w:../../AnalyzerModule/build/module.hex"
AVRDUDE_Z_DRIVE = "avrdude -c arduino -b 57600 -p atmega328p -P {0} -u -U flash:w:../../AnalyzerModule/build/z_drive.hex"


if __name__ == '__main__':
    #Filter comports
    print("Поиск портов... ", end="")
    comports = filter((lambda x: 'arduino' in x[1].lower() or 'ch340' in x[1].lower()), list_ports.comports())
    ports = [x[0] for x in comports]
    print("Ок")

    #Connect and filter devices
    print("Подключение... ", end="")
    devices = [AnalyzerModule(port) for port in ports]
    time.sleep(2)
    modules = filter((lambda device: device.readEchoNoexcept()), devices)
    modules = sorted(modules, key=lambda module: module.readID(), reverse=False)
    ids = [module.readID() for module in modules]
    is_calibrated = AnalyzerModule.isModulesCalibrated(modules)
    is_all_modules_connected = (len(modules)==9)
    print("Ок")

    print( "Найдено: устройств({0}), модулей({1})".format(len(devices), len(modules)) )
    print("Статус калибровки: ", "Ок" if is_calibrated else "Отсутствует")
    time.sleep(1)

    if (len(sys.argv) == 2):
        result = True

        if ("flash" in sys.argv[1] and sys.argv[1] != "-flash_analyzer"):
            for device in devices: device.close()

        #Прошить только Z привод (нижний)
        if (sys.argv[1] == "-flash_z_drive"):
            if is_calibrated:
                process = Popen(AVRDUDE_Z_DRIVE.format(modules[8]), stdout=PIPE, stderr=PIPE)
            else:
                process = Popen(AVRDUDE_Z_DRIVE.format(ports[0]), stdout=PIPE, stderr=PIPE)
            process.wait()
            if (process.returncode != 0): result = False

        #Прошить все девайсы прошивкой для измерительных модулей
        elif (sys.argv[1] == "-flash_modules"):
            if (is_calibrated):
                commands = [AVRDUDE_MODULE.format(module.name) for module in modules[:8]]
            else:
                commands = [AVRDUDE_MODULE.format(port) for port in ports]
            cmd_groups = [commands[i:i+3] for i in range(0, len(commands), 3)]
            for cmd_group in cmd_groups:
                processes = [Popen(cmd, stdout=PIPE, stderr=PIPE) for cmd in cmd_group]
                for process in processes: process.wait()
                for process in processes:
                    if (process.returncode != 0): result = False
                if result == False:
                    break

        #Прошить анализатор (модули и Z привод)
        elif (sys.argv[1] == "-flash_analyzer"):
            if not is_all_modules_connected:
                print("*** Подключены не все модули (8 + 1) ***")
                result = False
        
            else: 
                if not is_calibrated:
                    print("Зажмите два концевика на приводе Z...")
                    while True:
                        flag_break = False
                        for module in modules:
                            if module.readButtonBack() and module.readButtonForward():
                                modules.remove(module)
                                modules.append(module)
                                flag_break = True
                                break
                        if flag_break:
                            break
                
                for device in devices: device.close()
                
                commands = [AVRDUDE_MODULE.format(module.name) for module in modules[:8]]
                commands.append( AVRDUDE_Z_DRIVE.format(modules[8].name) )
                cmd_groups = [commands[i:i+3] for i in range(0, len(commands), 3)]
                for cmd_group in cmd_groups:
                    print("Прошиваю...")
                    processes =  [Popen(cmd, stdout=PIPE, stderr=PIPE) for cmd in cmd_group]
                    for process in processes: process.wait()
                    for process in processes:
                        if (process.returncode != 0): result = False
                    if result == False:
                        break

        #Откалибровать анализатор
        elif (sys.argv[1] == "-calibrate"):
            if is_all_modules_connected:
                print("Установка положений приводов...")
            
                for module in modules:
                    module.moveBack()
                AnalyzerModule.waitOperationsFinished(modules, 0.5)
                
                for module in modules:
                    module.moveRelative(20, 10, 100)
                AnalyzerModule.waitOperationsFinished(modules, 0.5)
                
                modules_copy = modules.copy()
                
                for i in range(8):
                    print( "[@] Нажмите любую кнопку на модуле #{0}".format(i+1) )
                    while True:
                        flag_break = False
                        for module in modules_copy:
                            if (module.readButtonBack() or module.readButtonForward() or module.readButtonTouch()):
                                module.setID(0xA0+i)
                                modules_copy.remove(module)
                                flag_break = True
                        if flag_break: break
                modules_copy[0].setID(0xA8)
                
                for module in modules:
                    module.moveBack()
                AnalyzerModule.waitOperationsFinished(modules, 0.5)
            else:
                print("*** Число модулей не равно 9 (8+1), подключите все модули ***")

        #Установить коэффициенты для тензодатчиков
        elif (sys.argv[1] == "-set_tenzo_coefficients"):
            print("--------------------------------------")
            tenzo_coeff = input("Введите коэффициент: ")
            for module in modules:
                if not module.setTenzoCoeff( float(tenzo_coeff) ):
                    print( "Ошибка установки значения ({0})".format(module.port) )
                    result = False

        if result:
            print("Операция завершена успешно")
        else:
            print("*** ОШИБКА! ОПЕРАЦИЯ ПРЕРВАНА ***")
    else:
        print("*** Не найдены аргументы строки! Выход ***")

    #input("Нажмите (Enter) для выхода")
