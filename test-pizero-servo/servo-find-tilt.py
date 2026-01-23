""" 
กด a => ตำแหน่งปัจจุบัน: 1140 us นี่เป้นค่าต่ำสุดที่ชนหัวน็อตพอดี
tilt down ห้ามเกินนี้

"""

import pigpio
import time

pi = pigpio.pi()
TILT_PIN = 27

# เริ่มต้นที่จุดกลาง (1500) ซึ่งปลอดภัยแน่นอน
current_pos = 1500

print("โหมดหาจุดปลอดภัย (Calibration)")
print("กด Ctrl+C เมื่อได้จุดที่ต้องการแล้ว")

try:
    while True:
        pi.set_servo_pulsewidth(TILT_PIN, current_pos)
        print(f"ตำแหน่งปัจจุบัน: {current_pos} us")

        val = input("พิมพ์ 'a' เพื่อลดค่า (-10) หรือ 'd' เพื่อเพิ่มค่า (+10): ")

        if val == 'a':
            # ค่อยๆ ลดค่าลง (เลื่อนไปหาจุดต่ำสุด)
            current_pos -= 10
        elif val == 'd':
            current_pos += 10

        # ป้องกันไม่ให้ค่าต่ำหรือสูงเกินสเปกมอเตอร์ทั่วไป (500-2500)
        current_pos = max(800, min(2200, current_pos))

except KeyboardInterrupt:
    print(f"\nหยุด! ค่าที่คุณหาได้คือ: {current_pos}")
    pi.set_servo_pulsewidth(TILT_PIN, 0)
    pi.stop()
