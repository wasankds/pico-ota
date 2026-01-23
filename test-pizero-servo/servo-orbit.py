""" 
เนื่องจาก MG996R เป็นมอเตอร์เฟืองเหล็กและกินไฟสูง เมื่อมันเคลื่อนที่พร้อมกันสองตัว ให้สังเกตว่า Raspberry Pi ของคุณมีไฟสีแดงกระพริบหรือค้างหรือไม่ ถ้ามีอาการ Pi ค้าง แสดงว่า Step Down จ่ายแอมป์ไม่พอครับ

"""

import pigpio
import time
import math

pi = pigpio.pi()

# กำหนดขา GPIO
PAN_PIN = 17   # ตัวล่าง Pan
TILT_PIN = 27  # ตัวบน Tilt

# --- การตั้งค่าขอบเขตความปลอดภัย (MG996R) ---
PAN_CENTER = 1500
TILT_CENTER = 1500
TILT_SAFE_MIN = 1150  # จุดที่หาไว้ไม่ให้ชนน็อต

# ระยะการส่าย (Amplitude) - ปรับลด/เพิ่มได้ตามต้องการ
# เราจะไม่ส่ายสุด 180 องศาเพื่อความนุ่มนวลในการทดสอบ orbit
PAN_RANGE = 400   # จะส่ายระหว่าง 1100 ถึง 1900
TILT_RANGE = 300   # จะก้มเงยระหว่าง 1200 ถึง 1800 (ปลอดภัยจาก 1150)

if not pi.connected:
    print("กรุณารัน sudo pigpiod ก่อน!")
    exit()


def orbit_test(duration_sec=20):
    print(f"เริ่มการทดสอบ Orbit ({duration_sec} วินาที)...")
    start_time = time.time()

    try:
        while (time.time() - start_time) < duration_sec:
            # ใช้เวลาเป็นตัวแปรสร้างมุม (t)
            t = (time.time() - start_time) * 2  # คูณ 2 คือความเร็วในการหมุน

            # คำนวณตำแหน่ง Pan (วงกลมใช้ Cosine)
            pan_val = PAN_CENTER + (math.cos(t) * PAN_RANGE)

            # คำนวณตำแหน่ง Tilt (วงกลมใช้ Sine)
            tilt_val = TILT_CENTER + (math.sin(t) * TILT_RANGE)

            # ตรวจสอบความปลอดภัยของ Tilt อีกครั้งก่อนสั่งงาน
            if tilt_val < TILT_SAFE_MIN:
                tilt_val = TILT_SAFE_MIN

            # ส่งคำสั่งพร้อมกัน
            pi.set_servo_pulsewidth(PAN_PIN, int(pan_val))
            pi.set_servo_pulsewidth(TILT_PIN, int(tilt_val))

            # หน่วงเวลาเล็กน้อยเพื่อให้การเคลื่อนที่นุ่มนวล (50Hz)
            time.sleep(0.02)

    except KeyboardInterrupt:
        pass

    # รีเซ็ตกลับจุดกลาง
    print("\nจบการทดสอบ กลับสู่จุดกึ่งกลาง")
    pi.set_servo_pulsewidth(PAN_PIN, PAN_CENTER)
    pi.set_servo_pulsewidth(TILT_PIN, TILT_CENTER)
    time.sleep(1)


if __name__ == "__main__":
    try:
        orbit_test(30)  # ทดสอบ 30 วินาที
    finally:
        # ปิดสัญญาณเพื่อถนอมมอเตอร์
        pi.set_servo_pulsewidth(PAN_PIN, 0)
        pi.set_servo_pulsewidth(TILT_PIN, 0)
        pi.stop()
        print("เสร็จสิ้น")
