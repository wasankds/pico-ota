""" 

ขาแนะนำที่ควรใช้: เพื่อให้จัดการง่าย ผมแนะนำให้ใช้ขาที่อยู่ใกล้กันและรองรับ PWM (Pulse Width Modulation):
1.) Pan (ส่ายซ้าย-ขวา): ต่อเข้ากับ GPIO 17 (Pin 11)
2.) Tilt (ก้ม-เงย): ต่อเข้ากับ GPIO 27 (Pin 13)

"""


from gpiozero import Servo
from time import sleep

# กำหนดขา GPIO ที่เชื่อมต่อ
pan_pin = 17
tilt_pin = 27

# สร้าง Object สำหรับ Servo
# คาบสัญญาณมาตรฐานคือ min_pulse_width=1/1000, max_pulse_width=2/1000
pan = Servo(pan_pin)
tilt = Servo(tilt_pin)

try:
    print("เริ่มการทดสอบ Pan/Tilt... กด Ctrl+C เพื่อหยุด")
    while True:
        # ทดสอบ Pan (ซ้าย -> กลาง -> ขวา)
        print("Pan: ไปที่ต่ำสุด")
        pan.min()
        sleep(1)

        print("Pan: ไปที่ตรงกลาง")
        pan.mid()
        sleep(1)

        print("Pan: ไปที่สูงสุด")
        pan.max()
        sleep(1)

        # ทดสอบ Tilt (ก้ม -> กลาง -> เงย)
        print("Tilt: ก้ม")
        tilt.min()
        sleep(1)

        print("Tilt: ตรงกลาง")
        tilt.mid()
        sleep(1)

        print("Tilt: เงย")
        tilt.max()
        sleep(1)

except KeyboardInterrupt:
    print("\nหยุดการทำงาน")


""" 
scp D:\aWK_LeaseSystem\EagleEyeLegion\pizero-child\test-2servo.py wasankds@pizero2w:~/eagle-eye-legion-pizero $
"""
