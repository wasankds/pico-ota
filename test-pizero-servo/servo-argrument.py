import pigpio
import sys
import argparse
import time

# --- การตั้งค่าขอบเขตความปลอดภัย (Safety Limits) ---
PAN_PIN, TILT_PIN = 17, 27
PAN_MIN, PAN_MAX = 500, 2500
TILT_MIN_SAFE = 1150  # จุดปลอดภัยที่คำนวณไว้ไม่ให้ชนน็อต
TILT_MAX = 2500
NEUTRAL = 1500


def main():
    parser = argparse.ArgumentParser(
        description='ควบคุม Servo MG996R แบบเสถียร')
    parser.add_argument('--pan', type=int, help='ค่า Pan (500-2500)')
    parser.add_argument('--tilt', type=int, help='ค่า Tilt (1150-2500)')
    parser.add_argument('--reset', action='store_true',
                        help='รีเซ็ตกลับจุด Neutral (1500, 1500)')

    args = parser.parse_args()
    pi = pigpio.pi()

    if not pi.connected:
        print("Error: ไม่สามารถเชื่อมต่อ pigpio ได้ กรุณารัน 'sudo pigpiod'")
        sys.exit()

    try:
        # กรณีสั่ง RESET: ให้กลับไปจุดกลางทั้งคู่ทันที
        if args.reset:
            print(f"Resetting to Neutral: Pan={NEUTRAL}, Tilt={NEUTRAL}")
            pi.set_servo_pulsewidth(PAN_PIN, NEUTRAL)
            pi.set_servo_pulsewidth(TILT_PIN, NEUTRAL)
            time.sleep(1)  # ให้เวลามอเตอร์หมุนให้ถึงจุดก่อนตัดสัญญาณ

        # กรณีสั่งระบุตำแหน่งเอง
        else:
            if args.pan is not None:
                # จำกัดช่วงการหมุนของ Pan
                val_pan = max(PAN_MIN, min(PAN_MAX, args.pan))
                print(f"Pan Target: {val_pan}")
                pi.set_servo_pulsewidth(PAN_PIN, val_pan)

            if args.tilt is not None:
                # จำกัดช่วงการหมุนของ Tilt (สำคัญ: ไม่ให้ต่ำกว่า 1150)
                val_tilt = max(TILT_MIN_SAFE, min(TILT_MAX, args.tilt))
                print(f"Tilt Target: {val_tilt}")
                pi.set_servo_pulsewidth(TILT_PIN, val_tilt)

            # หน่วงเวลาสั้นๆ เพื่อให้มอเตอร์เคลื่อนที่ไปยังเป้าหมาย
            time.sleep(0.8)

    finally:
        # ตัดสัญญาณ PWM (0) เพื่อหยุดการสั่น (Jitter) และถนอมมอเตอร์
        # MG996R จะหยุดนิ่งที่ตำแหน่งนั้นด้วยแรงเบรกของเฟืองเหล็ก
        pi.set_servo_pulsewidth(PAN_PIN, 0)
        pi.set_servo_pulsewidth(TILT_PIN, 0)
        pi.stop()


if __name__ == "__main__":
    main()
