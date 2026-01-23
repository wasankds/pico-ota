import pigpio
import time
import math

pi = pigpio.pi()

PAN_PIN = 17
TILT_PIN = 27

# --- Settings ---
PAN_CENTER = 1500   # จุดกึ่งกลาง Pan
TILT_CENTER = 1500  # จุดกึ่งกลาง Tilt
TILT_MIN_SAFE = 1160  # จุดต่ำสุดที่ปลอดภัย (เหนือหัวน็อต) ห้ามต่ำกว่านี้
PAN_AMPLITUDE = 1000
TILT_AMPLITUDE = 1000

if not pi.connected:
    print("กรุณารัน sudo pigpiod")
    exit()


def orbit_slow_motion(duration_sec=60):
    # ปรับตัวคูณตรงนี้: 0.3 คือช้ามาก, 0.5 คือปานกลาง, 1.0 คือเร็ว
    speed_factor = 0.4

    print(f"เริ่มการทดสอบ Orbit แบบช้าๆ (Speed: {speed_factor})")
    start_time = time.time()

    try:
        while (time.time() - start_time) < duration_sec:
            # คำนวณค่า t โดยใช้ speed_factor ควบคุมความเร็ว
            t = (time.time() - start_time) * speed_factor

            pan_val = PAN_CENTER + (math.cos(t) * PAN_AMPLITUDE)
            tilt_val = TILT_CENTER + (math.sin(t) * TILT_AMPLITUDE)

            # Safety Limits
            pan_val = max(500, min(2500, pan_val))
            tilt_val = max(TILT_MIN_SAFE, min(2500, tilt_val))

            pi.set_servo_pulsewidth(PAN_PIN, int(pan_val))
            pi.set_servo_pulsewidth(TILT_PIN, int(tilt_val))

            # หน่วงเวลาสั้นๆ เพื่อให้การเคลื่อนที่ดูสมูท (50 เฟรมต่อวินาที)
            time.sleep(0.02)

    except KeyboardInterrupt:
        pass

    # กลับจุดกลาง
    pi.set_servo_pulsewidth(PAN_PIN, PAN_CENTER)
    pi.set_servo_pulsewidth(TILT_PIN, TILT_CENTER)
    time.sleep(1)


if __name__ == "__main__":
    try:
        orbit_slow_motion(60)  # ทดสอบนาน 1 นาที
    finally:
        pi.set_servo_pulsewidth(PAN_PIN, 0)
        pi.set_servo_pulsewidth(TILT_PIN, 0)
        pi.stop()
