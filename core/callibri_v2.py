from neurosdk.scanner import Scanner
from neurosdk.sensor import Sensor
import numpy as np

def onCallibriSignalDataReceived(sensor: Sensor, data):
   sensor.data = np.ravel([np.array(i.Samples) for i in data]) #WARNING: you must add 'Sensor.data = []' to the code.

def find_sensors(scanner: Scanner):
    sensors_found = scanner.sensors()
    while not sensors_found:
        sensors_found = scanner.sensors()
    return sensors_found