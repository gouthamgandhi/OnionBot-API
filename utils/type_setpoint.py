from servo import Servo
import time

import sys
import os
sys.path.insert(1, os.path.join(sys.path[0], '..'))
servo = Servo()

while True:
    x = float(input("Type setpoint: "))
    servo.update_setpoint(x)
    time.sleep(.1)
