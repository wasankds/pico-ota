
""" 

เพิ่มระบบรอ Que ถ้ามีคำสั่งจาก Server มาพร้อมๆกันหลายคำสั่ง


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
import fcntl  # ใช้สำหรับการล็อกไฟล์

# --- Config & Path ---
PAN_PIN, TILT_PIN = 17, 27
PAN_MIN, PAN_MAX = 500, 2500
TILT_MIN_SAFE = 1150
TILT_MAX = 2500
NEUTRAL = 1500

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
POS_FILE = os.path.join(BASE_DIR, "last_servo_pos.txt")
LOCK_FILE = os.path.join(BASE_DIR, "servo.lock")  # ไฟล์สำหรับทำกุญแจล็อก


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
    with open(POS_FILE, "w") as f:
        f.write(f"{p},{t}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--pan', type=int)
    parser.add_argument('--tilt', type=int)
    parser.add_argument('--speed', type=int, default=5)
    parser.add_argument('--reset', action='store_true')
    args = parser.parse_args()

    # --- ส่วนการล็อกไฟล์ (Locking System) ---
    lock_file_handle = open(LOCK_FILE, 'w')
    try:
        # พยายามล็อกไฟล์ (ถ้าล็อกไม่ได้จะรอจนกว่าจะว่าง)
        # หากต้องการให้ 'ข้าม' แทนที่จะ 'รอ' ให้ใช้ fcntl.LOCK_EX | fcntl.LOCK_NB
        fcntl.flock(lock_file_handle, fcntl.LOCK_EX)

        pi = pigpio.pi()
        if not pi.connected:
            sys.exit()

        curr_p, curr_t = load_last_pos()

        target_p = max(PAN_MIN, min(PAN_MAX, args.pan)
                       ) if args.pan is not None else curr_p
        target_t = max(TILT_MIN_SAFE, min(TILT_MAX, args.tilt)
                       ) if args.tilt is not None else curr_t
        if args.reset:
            target_p, target_t = NEUTRAL, NEUTRAL

        step_delay = (11 - args.speed) * 0.003

        while curr_p != target_p or curr_t != target_t:
            if curr_p < target_p:
                curr_p = min(curr_p + 15, target_p)
            elif curr_p > target_p:
                curr_p = max(curr_p - 15, target_p)

            if curr_t < target_t:
                curr_t = min(curr_t + 15, target_t)
            elif curr_t > target_t:
                curr_t = max(curr_t - 15, target_t)

            pi.set_servo_pulsewidth(PAN_PIN, curr_p)
            pi.set_servo_pulsewidth(TILT_PIN, curr_t)
            time.sleep(step_delay)

        save_current_pos(curr_p, curr_t)

    except Exception as e:
        print(f"Error: {e}")
    finally:
        # ปล่อยสัญญาณและปลดล็อกไฟล์
        if 'pi' in locals():
            pi.set_servo_pulsewidth(PAN_PIN, 0)
            pi.set_servo_pulsewidth(TILT_PIN, 0)
            pi.stop()

        # ปลดล็อกกุญแจเพื่อให้คำสั่งถัดไปทำงานได้
        fcntl.flock(lock_file_handle, fcntl.LOCK_UN)
        lock_file_handle.close()


if __name__ == "__main__":
    main()
