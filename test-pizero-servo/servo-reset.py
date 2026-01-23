""" 

# สคริปต์นี้ใช้สำหรับสั่งรีเซ็ตมอเตอร์เซอร์โว 2 ตัว (PAN และ TILT) ไปที่ค่ากลาง 1500us
nano ~/.bashrc

# เพิ่มบรรทัดนี้ลงไปข้างล่างสุดของไฟล์
alias servo-test='python3 /home/pi/eagle-eye-legion-pizero/test-2servo.py'

# บันทึกไฟล์แล้วออกมา จากนั้นรันคำสั่งนี้เพื่อโหลดการเปลี่ยนแปลง
source ~/.bashrc


"""

import pigpio
import time

# เชื่อมต่อกับ pigpio daemon
pi = pigpio.pi()

if not pi.connected:
    print("ไม่สามารถเชื่อมต่อกับ pigpio daemon ได้! (ลองพิมพ์ sudo pigpiod)")
    exit()

# กำหนดขา GPIO
PAN_PIN = 17
TILT_PIN = 27

print("กำลังสั่งรีเซ็ตไปที่ 1500us (ค่ากลางมาตรฐาน)...")

# สั่ง Pulse Width ไปที่ 1500 (คือจุดกึ่งกลางเป๊ะของเครื่อง Tester)
pi.set_servo_pulsewidth(PAN_PIN, 1500)
pi.set_servo_pulsewidth(TILT_PIN, 1500)

time.sleep(1)

# ปิดสัญญาณ (เพื่อไม่ให้มอเตอร์สั่นหรือร้อน)
pi.set_servo_pulsewidth(PAN_PIN, 0)
pi.set_servo_pulsewidth(TILT_PIN, 0)

pi.stop()
print("เสร็จสิ้น")
