import pigpio
import time

# ตั้งค่าขา GPIO
PAN_PIN = 17
TILT_PIN = 27

# --- ตั้งค่าขอบเขตความปลอดภัย (Safety Range) ---
TILT_SAFE_DOWN = 1150  # จุดต่ำสุดที่ก้มได้ (เหนือหัวน็อต)
TILT_UP = 2500  # จุดเงยสูงสุด
PAN_LEFT = 500  # ส่ายซ้ายสุด
PAN_RIGHT = 2500  # ส่ายขวาสุด
CENTER = 1500  # จุดกึ่งกลางมาตรฐาน

pi = pigpio.pi()

if not pi.connected:
    print("กรุณารัน sudo pigpiod ก่อนเริ่มใช้งาน")
    exit()


def test_move(pin, value, label):
    print(f"กำลังเคลื่อนที่ {label} ไปยังค่า: {value} us")
    pi.set_servo_pulsewidth(pin, value)
    time.sleep(1)


try:
    print("เริ่มการทดสอบแบบจำกัดระยะปลอดภัย... กด Ctrl+C เพื่อหยุด")
    while True:
        # --- ทดสอบ Pan (ซ้าย-กลาง-ขวา) ---
        test_move(PAN_PIN, PAN_LEFT, "Pan (ซ้าย)")
        test_move(PAN_PIN, CENTER, "Pan (กลาง)")
        test_move(PAN_PIN, PAN_RIGHT, "Pan (ขวา)")
        test_move(PAN_PIN, CENTER, "Pan (กลาง)")

        # --- ทดสอบ Tilt (ก้มปลอดภัย-กลาง-เงย) ---
        test_move(TILT_PIN, TILT_SAFE_DOWN, "Tilt (ก้มสุด-ปลอดภัย)")
        test_move(TILT_PIN, CENTER, "Tilt (กลาง)")
        test_move(TILT_PIN, TILT_UP, "Tilt (เงย)")
        test_move(TILT_PIN, CENTER, "Tilt (กลาง)")

except KeyboardInterrupt:
    print("\nหยุดการทำงาน และรีเซ็ตกลับจุดกลาง")
    pi.set_servo_pulsewidth(PAN_PIN, CENTER)
    pi.set_servo_pulsewidth(TILT_PIN, CENTER)
    time.sleep(0.5)
finally:
    pi.set_servo_pulsewidth(PAN_PIN, 0)
    pi.set_servo_pulsewidth(TILT_PIN, 0)
    pi.stop()
