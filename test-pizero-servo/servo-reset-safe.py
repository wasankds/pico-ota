import pigpio
import time

pi = pigpio.pi()

# กำหนดขา GPIO
PAN_PIN = 17
TILT_PIN = 27

# --- ตั้งค่าขีดจำกัดความปลอดภัย ---
TILT_SAFE_MIN = 1150  # ต่ำกว่านี้จะชนน็อต
PAN_CENTER = 1500
TILT_CENTER = 1500


def move_servo(pin, pulse_width):
    """ฟังก์ชันสั่งงาน Servo พร้อมตรวจสอบความปลอดภัย"""
    if pin == TILT_PIN:
        # ถ้าสั่ง Tilt ต่ำกว่า 1150 ให้ดึงกลับมาที่ 1150 ทันที
        if pulse_width < TILT_SAFE_MIN:
            print(
                f"Warn: {pulse_width} ต่ำเกินไป! ปรับเป็นจุดปลอดภัย {TILT_SAFE_MIN}")
            pulse_width = TILT_SAFE_MIN

    pi.set_servo_pulsewidth(pin, pulse_width)


if not pi.connected:
    print("ไม่สามารถเชื่อมต่อ pigpio ได้!")
    exit()

try:
    print(f"กำลังรีเซ็ต... (Tilt จะไม่ต่ำกว่า {TILT_SAFE_MIN})")

    # ใช้ฟังก์ชันที่สร้างใหม่แทนการสั่งตรงๆ
    move_servo(PAN_PIN, PAN_CENTER)
    move_servo(TILT_PIN, TILT_CENTER)

    time.sleep(1)

finally:
    # ปิดสัญญาณเพื่อถนอมมอเตอร์
    pi.set_servo_pulsewidth(PAN_PIN, 0)
    pi.set_servo_pulsewidth(TILT_PIN, 0)
    pi.stop()
    print("เสร็จสิ้น")
