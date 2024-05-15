# v2 / 29.01.2024

# Зависимости к установке:

# pip install pyneurosdk2
# pip install numpy
# pip install PyQt5 matplotlib

# Рекомендации:

# 1) Все возможные настройки см. в файлах cmn_types.py, sensor.py, sample.py и пр. в библиотеке neurosdk по адресу ...\Python310\Lib\site-packages\neurosdk

# 2) Обратите внимание, что кириллицу использовать в EDF нельзя

# 3) Выход из программы (в PowerShell или командной строке): Crtl+C (после этого EDF-файл обновится, и его можно будет открыть не в режиме стрима, а как обычно) + закрыть окно с графиками

from neurosdk.scanner import Scanner
from neurosdk.sensor import Sensor
from neurosdk.callibri_sensor import CallibriSensor
from neurosdk.cmn_types import *
from edfwriter import EDFwriter
from datetime import datetime
import numpy as np
import decimal
import random
import signal
import sys
import time
import threading

from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

samplerate = 250
edfsignals = 1+3+3 # Основной канал + Акселерометр (3) + Гироскоп (3)
edfNames = ["EEG/EOG/EMG","Acc_X","Acc_Y","Acc_Z","Gyro_X","Gyro_Y","Gyro_Z"]
edfE = ["uV","value","value","value","value","value","value"]
edfMinPhysical = [-6400,-2,-2,-2,-300,-300,-300]
edfMaxPhysical = [6400,2,2,2,300,300,300]
bSignal = np.empty(samplerate, np.float64, "C")
bAccX = np.empty(samplerate, np.float64, "C")
bAccY = np.empty(samplerate, np.float64, "C")
bAccZ = np.empty(samplerate, np.float64, "C")
bGyroX = np.empty(samplerate, np.float64, "C")
bGyroY = np.empty(samplerate, np.float64, "C")
bGyroZ = np.empty(samplerate, np.float64, "C")

plotSeconds = 5
bSignal_plot = np.empty(samplerate*plotSeconds, np.float64, "C")
bAccX_plot = np.empty(samplerate*plotSeconds, np.float64, "C")
bAccY_plot = np.empty(samplerate*plotSeconds, np.float64, "C")
bAccZ_plot = np.empty(samplerate*plotSeconds, np.float64, "C")
bGyroX_plot = np.empty(samplerate*plotSeconds, np.float64, "C")
bGyroY_plot = np.empty(samplerate*plotSeconds, np.float64, "C")
bGyroZ_plot = np.empty(samplerate*plotSeconds, np.float64, "C")


strong_signal_threshold = 2.8
weak_signal_threshold = 1.65

edfCount = 0
hdl = None


# =================== Интерфейс ===================

app_instance = None

class PlotCanvas(FigureCanvas):
    def __init__(self, parent=None, width=10, height=8, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        FigureCanvas.__init__(self, self.fig)
        self.setParent(parent)
        self.ax1 = self.fig.add_subplot(224)  # График ускорений
        self.ax2 = self.fig.add_subplot(211)  # FFT график
        self.ax3 = self.fig.add_subplot(223)  # График сигнала
        self.fig.subplots_adjust(left=0.1, right=0.9, top=0.9, bottom=0.1)
        self.fig.tight_layout()
        
    def plot(self, data):
        # Обновление данных для графиков
        bSignal, bAccX, bAccY, bAccZ, samplerate = data

        # Очистка графиков
        self.ax1.clear()
        self.ax2.clear()
        self.ax3.clear()

        # Построение графиков
        self.ax1.plot(bAccX, 'r', label='X-axis')
        self.ax1.plot(bAccY, 'g', label='Y-axis')
        self.ax1.plot(bAccZ, 'b', label='Z-axis')
        self.ax1.legend(loc='upper right')
        self.ax1.set_title('Acceleration Data')

        self.ax2.plot(bSignal, 'k')
        self.ax2.set_title('Signal Data')

        N = len(bSignal)
        T = 1.0 / samplerate
        xf = np.linspace(0.0, 1.0/(2.0*T), N//2)
        yf = np.fft.fft(bSignal)
        self.ax3.plot(xf, 2.0/N * np.abs(yf[:N//2]))
        self.ax3.set_title('FFT Analysis')

        self.draw()

class App(QMainWindow):
    def __init__(self):
        super().__init__()
        self.canvas = PlotCanvas(self, width=10, height=8)
        self.setCentralWidget(self.canvas)
        self.title = 'Callibri Data Plotting'
        self.initUI()

    def initUI(self):
        self.setWindowTitle(self.title)
        self.showMaximized()  # Открытие окна во весь экран        
        self.show()

    def update_plot(self, data):
        self.canvas.plot(data)

# Функция запуска PyQt приложения
def run_app():
    global app_instance
    app = QApplication(sys.argv)
    app_instance = App()
    sys.exit(app.exec_())
    
# =================== Старый код =================== 

def start_record():
    global samplerate,edfNames,edfE,hdl
    now = datetime.now()
    nowString = "{}-{}-{}-{}-{}-{}".format(now.year,now.month,now.day,now.hour,now.minute,now.second)
    hdl = EDFwriter(nowString+'.edf', EDFwriter.EDFLIB_FILETYPE_EDFPLUS, edfsignals)
    for i in range(0, edfsignals):
        hdl.setPhysicalMinimum(i, edfMinPhysical[i])
        hdl.setPhysicalMaximum(i, edfMaxPhysical[i])
        hdl.setDigitalMinimum(i, -32768)
        hdl.setDigitalMaximum(i, 32767)
        hdl.setSampleFrequency(i, samplerate)
        hdl.setSignalLabel(i, edfNames[i])
        hdl.setPhysicalDimension(i, edfE[i])
        hdl.setPreFilter(i, "")
        hdl.setTransducer(i, "")

    hdl.setPatientCode("0000")
    hdl.setPatientBirthDate(2000, 1, 1)
    hdl.setPatientName("-")
    hdl.setAdditionalPatientInfo("-")
    hdl.setAdministrationCode("0000")
    hdl.setTechnician("-")
    hdl.setEquipment("Callibri")
    hdl.setAdditionalRecordingInfo("-")
    
    # Запуск обновления графиков в отдельном потоке
    app_thread = threading.Thread(target=run_app)
    app_thread.start()
    
def float_to_str(f):
    d1 = ctx.create_decimal(repr(f))
    return format(d1, 'f')
       
def on_sensor_state_changed(sensor, state):
    print('Sensor {0} is {1}'.format(sensor.name, state))
    
def on_battery_changed(sensor, battery):
    print('Battery: {0}'.format(battery))   
    
def on_memsDataReceived(sensor, data):    
    global lastAccX,lastAccY,lastAccZ,lastGyroX,lastGyroY,lastGyroZ
    for j in range(0, len(data)):                
        lastAccX = data[j].Accelerometer.X
        lastAccY = data[j].Accelerometer.Y
        lastAccZ = data[j].Accelerometer.Z
        lastGyroX = data[j].Gyroscope.X
        lastGyroY = data[j].Gyroscope.Y
        lastGyroZ = data[j].Gyroscope.Z 
    
def sensorFound(scanner, sensors):
   for i in range(len(sensors)):
       global sensor, doStart, scanStarted
       scanStarted = False
       print('Sensor %s' % sensors[i])
       sensor = scanner.create_sensor(sensors[i])
       sensor.sensorStateChanged = on_sensor_state_changed
       sensor.batteryChanged = on_battery_changed
       sensor.signalDataReceived = on_callibri_signal_data_received         
       sensor.memsDataReceived = on_memsDataReceived
       sensor.connect()
       print("\n==================") 
       print("\n# sensor.parameters:") 
       print(sensor.parameters) 
       print("\n# sensor.features:") 
       print(sensor.features) 
       print("\n# sensor.commands:") 
       print(sensor.commands)
       print("\n==================\n") 
       doStart = True   
    
def on_callibri_signal_data_received(sensor, data):
    global curPos, edfCount, bSignal, bAccX, bAccY, bAccZ, bGyroX, bGyroY, bGyroZ, \
           bSignal_plot, bAccX_plot, bAccY_plot, bAccZ_plot, bGyroX_plot, bGyroY_plot, bGyroZ_plot, app_instance
    
    updateFrequency = round(samplerate/5)  # Обновление графиков 2 раза в секунду
    
    for j in range(len(data)):
        for i in range(9):
            # Обновление основных массивов данных
            bSignal[curPos] = data[j].Samples[i] * 500000
            bAccX[curPos] = lastAccX
            bAccY[curPos] = lastAccY
            bAccZ[curPos] = lastAccZ
            bGyroX[curPos] = lastGyroX
            bGyroY[curPos] = lastGyroY
            bGyroZ[curPos] = lastGyroZ

            # Обновление расширенных массивов данных для графиков
            bSignal_plot = np.roll(bSignal_plot, -1)
            bSignal_plot[-1] = data[j].Samples[i] * 500000
            bAccX_plot = np.roll(bAccX_plot, -1)
            bAccX_plot[-1] = lastAccX
            bAccY_plot = np.roll(bAccY_plot, -1)
            bAccY_plot[-1] = lastAccY
            bAccZ_plot = np.roll(bAccZ_plot, -1)
            bAccZ_plot[-1] = lastAccZ
            bGyroX_plot = np.roll(bGyroX_plot, -1)
            bGyroX_plot[-1] = lastGyroX
            bGyroY_plot = np.roll(bGyroY_plot, -1)
            bGyroY_plot[-1] = lastGyroY
            bGyroZ_plot = np.roll(bGyroZ_plot, -1)
            bGyroZ_plot[-1] = lastGyroZ



            curPos += 1
            if curPos % updateFrequency == 0 and app_instance:
                app_instance.update_plot([bSignal_plot, bAccX_plot, bAccY_plot, bAccZ_plot, samplerate])
            
            if curPos == samplerate:
                print("EDF > #"+str(edfCount))
                edfCount += 1

                #TODO это значение сигнала является нашей метрикой о "секундном" интервале
                signal_rms = np.sqrt(np.mean(np.square(bSignal)))

                if edfCount % 2 != 0:
                    print("===============")
                    print(f"   Моргайте    {signal_rms}")
                    print("===============")

                if edfCount % 2 == 0:
                    if signal_rms > strong_signal_threshold:
                        print(f">>>>ТИРЕ<<<< {signal_rms}")
                    elif signal_rms > weak_signal_threshold:
                        print(f"====ТОЧКА==== {signal_rms}")

                curPos = 0

                if (edfCount % 2 != 0):
                    continue

                curPos = 0
                # Запись в EDF
                hdl.writeSamples(bSignal)
                hdl.writeSamples(bAccX)
                hdl.writeSamples(bAccY)
                hdl.writeSamples(bAccZ)
                hdl.writeSamples(bGyroX)
                hdl.writeSamples(bGyroY)
                hdl.writeSamples(bGyroZ)
                # Обновление графиков
                if app_instance:
                    app_instance.update_plot([bSignal_plot, bAccX_plot, bAccY_plot, bAccZ_plot, samplerate])
                    
def exit_handler(signal, frame):
    print("\nExit...\n")
    hdl.close()
    sys.exit(0) 

lastAccX = 0.0
lastAccY = 0.0
lastAccZ = 0.0
lastGyroX = 0.0
lastGyroY = 0.0
lastGyroZ = 0.0

ctx = decimal.Context()
ctx.prec = 30

curPos = 0  
sensor = None
doStart = False
scanner = Scanner([SensorFamily.LEBrainBit, SensorFamily.LECallibri])
scanStarted = True
signal.signal(signal.SIGINT, exit_handler)  
scanner.sensorsChanged = sensorFound
scanner.start()  

while(True):
    time.sleep(1)
    if (doStart):
       time.sleep(1)
       start_record()
       doStart = False
       
       # Все возможные настройки см. в файлах cmn_types.py, sensor.py, sample.py и пр.
       # в библиотеке neurosdk по адресу ...\Python310\Lib\site-packages\neurosdk
       
       sensor.signal_type = CallibriSignalType.EEG
       # EEG = 0, EMG = 1, ECG = 2, EDA = 3, StrainGaugeBreathing = 4, ImpedanceBreathing = 5, Unknown = 6
       
       sensor.hardware_filters = [SensorFilter.HPFBwhLvl1CutoffFreq1Hz]      
       # HPFBwhLvl1CutoffFreq1Hz = 0, HPFBwhLvl1CutoffFreq5Hz = 1, BSFBwhLvl2CutoffFreq45_55Hz = 2, BSFBwhLvl2CutoffFreq55_65Hz = 3, HPFBwhLvl2CutoffFreq10Hz = 4, LPFBwhLvl2CutoffFreq400H = 5, HPFBwhLvl2CutoffFreq80Hz = 6, Unknown = 0xFF       
       
       sensor.ext_sw_input = SensorExternalSwitchInput.MioElectrodes
       # MioElectrodesRespUSB = 0, MioElectrodes = 1, MioUSB = 2, RespUSB = 3       
       
       sensor.sampling_frequency = SensorSamplingFrequency.FrequencyHz250
       # FrequencyHz10 = 0, FrequencyHz20 = 1, FrequencyHz100 = 2, FrequencyHz125 = 3, FrequencyHz250 = 4, FrequencyHz500 = 5, FrequencyHz1000 = 6, FrequencyHz2000 = 7, FrequencyHz4000 = 8, FrequencyHz8000 = 9, FrequencyUnsupported = 10
       
       sensor.adc_input = SensorADCInput.Electrodes
       # Electrodes = 0, Short = 1, Test = 2, Resistance = 3      
       
       sensor.exec_command(SensorCommand.StartSignal)
       sensor.exec_command(SensorCommand.StartMEMS)     
       