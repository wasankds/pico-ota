""" 

ต้องส่ง argument ชื่อไฟล์ที่รัย process ที่ต้องการหยุด
เช่น python3 stop-2servo.py test-2servo-argrument-speed-que.py

"""

import pigpio
import os
import sys

# 1. ตัดสัญญาณ PWM ทันทีเพื่อให้มอเตอร์หยุดสั่น/คราง
pi = pigpio.pi()
if pi.connected:
    pi.set_servo_pulsewidth(17, 0)
    pi.set_servo_pulsewidth(27, 0)
    pi.stop()

# 2. สั่ง Kill process ตามชื่อที่ส่งมาจาก Server
if len(sys.argv) > 1:
    target_process = sys.argv[1]
    # ใช้ pkill -f เพื่อค้นหาชื่อไฟล์ใน command line ทั้งหมด
    os.system(f"pkill -f {target_process}")
    print(f"Stopped process: {target_process}")
else:
    print("No process name provided, only cleared PWM.")

print("Servo PWM set to 0 (Released)")
