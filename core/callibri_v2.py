from neurosdk.scanner import Scanner
from neurosdk.sensor import Sensor

class SavingDataSensor(Sensor):
    data = [] # when receiving data, save it to this variable.
def sensor_found(scanner: Scanner, sensors):
   for i in range(len(sensors)):
       print('Sensor %s' % sensors[i])

def on_callibri_signal_data_received(sensor: SavingDataSensor, data):
    sensor.data = data