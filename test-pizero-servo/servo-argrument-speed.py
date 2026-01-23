""" 
การทำงาน,คำสั่งตัวอย่าง
กวาดกล้องช้าๆ ไปซ้าย
python3 test-servo.py --pan 800 --speed 2

กวาดกล้องเร็วไปขวา
python3 test-servo.py --pan 2200 --speed 8

เงยหน้าขึ้นแบบนุ่มนวล
python3 test-servo.py --tilt 1800 --speed 3

สั่งเฉียง (พร้อมกัน)
python3 test-servo.py --pan 1000 --tilt 2000 --speed 4

รีเซ็ตกล้อง (กลับกลาง)
python3 test-servo.py --reset --speed 5


"""

import pigpio
import sys
import argparse
import time
import os

# --- Settings ---
PAN_PIN, TILT_PIN = 17, 27
PAN_MIN, PAN_MAX = 500, 2500
TILT_MIN_SAFE = 1150
TILT_MAX = 2500
NEUTRAL = 1500

# กำหนดให้ไฟล์เก็บตำแหน่งอยู่ที่เดียวกับโค้ด
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
POS_FILE = os.path.join(BASE_DIR, "last_servo_pos.txt")


def load_last_pos():
    if os.path.exists(POS_FILE):
        try:
            with open(POS_FILE, "r") as f:
                coords = f.read().split(',')
                return int(coords[0]), int(coords[1])
        except:
            pass
    return NEUTRAL, NEUTRAL


def save_current_pos(p, t):
    try:
        with open(POS_FILE, "w") as f:
            f.write(f"{p},{t}")
    except Exception as e:
        print(f"Error saving position: {e}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--pan', type=int)
    parser.add_argument('--tilt', type=int)
    parser.add_argument('--speed', type=int, default=5)
    parser.add_argument('--reset', action='store_true')

    args = parser.parse_args()
    pi = pigpio.pi()
    if not pi.connected:
        sys.exit()

    # 1. โหลดตำแหน่งที่มอเตอร์จอดอยู่จริงครั้งล่าสุด
    curr_p, curr_t = load_last_pos()

    # 2. ตั้งเป้าหมาย
    target_p = max(PAN_MIN, min(PAN_MAX, args.pan)
                   ) if args.pan is not None else curr_p
    target_t = max(TILT_MIN_SAFE, min(TILT_MAX, args.tilt)
                   ) if args.tilt is not None else curr_t

    if args.reset:
        target_p, target_t = NEUTRAL, NEUTRAL

    # 3. คำนวณการหน่วงเวลา (ยิ่ง speed น้อย ยิ่งหน่วงมาก)
    # ใช้ delay ที่นิ่งขึ้น
    step_delay = (11 - args.speed) * 0.003

    print(
        f"Moving from {curr_p},{curr_t} -> {target_p},{target_t} (Speed: {args.speed})")

    try:
        # 4. ลูปขยับพร้อมกัน (Simultaneous Move)
        # วิธีนี้จะทำให้มอเตอร์ไม่ดีด และขยับนิ่มทุกตำแหน่ง
        while curr_p != target_p or curr_t != target_t:
            # ขยับ Pan ทีละ 15 (ก้าวกำลังดี ไม่สั่น)
            if curr_p < target_p:
                curr_p = min(curr_p + 15, target_p)
            elif curr_p > target_p:
                curr_p = max(curr_p - 15, target_p)

            # ขยับ Tilt ทีละ 15
            if curr_t < target_t:
                curr_t = min(curr_t + 15, target_t)
            elif curr_t > target_t:
                curr_t = max(curr_t - 15, target_t)

            pi.set_servo_pulsewidth(PAN_PIN, curr_p)
            pi.set_servo_pulsewidth(TILT_PIN, curr_t)
            time.sleep(step_delay)

        # บันทึกตำแหน่งปัจจุบันลงไฟล์ไว้ใช้ครั้งหน้า
        save_current_pos(curr_p, curr_t)

    finally:
        time.sleep(0.2)
        pi.set_servo_pulsewidth(PAN_PIN, 0)
        pi.set_servo_pulsewidth(TILT_PIN, 0)
        pi.stop()


if __name__ == "__main__":
    main()
