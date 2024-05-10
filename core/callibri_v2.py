def sensor_found(scanner, sensors): #scanner is used when running scanner.start()
   for i in range(len(sensors)):
       print('Sensor %s' % sensors[i])

import neurosdk.cmn_types
import neurosdk.scanner
scanner = neurosdk.scanner.Scanner([neurosdk.cmn_types.SensorFamily.LECallibri])
scanner.sensorsChanged = sensor_found
scanner.start()  