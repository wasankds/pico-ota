import pigpio
import sys
import argparse
import time
import os
import fcntl

# --- Config & Path ---
PAN_PIN, TILT_PIN = 17, 27
PAN_MIN, PAN_MAX = 500, 2500
TILT_MIN_SAFE = 1150
TILT_MAX = 2500
NEUTRAL = 1500

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
POS_FILE = os.path.join(BASE_DIR, "last_servo_pos.txt")
LOCK_FILE = os.path.join(BASE_DIR, "servo.lock")


def load_last_pos(pi):
    # พยายามอ่านจาก Hardware จริงก่อน ถ้าไม่ได้ค่อยอ่านจากไฟล์
    hw_p = pi.get_servo_pulsewidth(PAN_PIN)
    hw_t = pi.get_servo_pulsewidth(TILT_PIN)

    if hw_p > 0 and hw_t > 0:
        return hw_p, hw_t

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
    except:
        pass


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--pan', type=int)
    parser.add_argument('--tilt', type=int)
    parser.add_argument('--speed', type=int, default=5)
    parser.add_argument('--reset', action='store_true')
    args = parser.parse_args()

    lock_file_handle = open(LOCK_FILE, 'w')
    pi = pigpio.pi()

    try:
        # ล็อกไฟล์ (Queue System)
        fcntl.flock(lock_file_handle, fcntl.LOCK_EX)

        if not pi.connected:
            sys.exit()

        # อ่านตำแหน่งล่าสุด (เน้นจาก Hardware จริง)
        curr_p, curr_t = load_last_pos(pi)

        # กำหนดเป้าหมาย
        target_p = max(PAN_MIN, min(PAN_MAX, args.pan)
                       ) if args.pan is not None else curr_p
        target_t = max(TILT_MIN_SAFE, min(TILT_MAX, args.tilt)
                       ) if args.tilt is not None else curr_t

        if args.reset:
            target_p, target_t = NEUTRAL, NEUTRAL

        step_delay = (11 - args.speed) * 0.003

        # เริ่มเคลื่อนที่
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

            # **แก้ไขสำคัญ: บันทึกตำแหน่งทุกก้าว** เพื่อให้ตอนถูก pkill ค่าจะแม่นยำที่สุด
            save_current_pos(curr_p, curr_t)
            time.sleep(step_delay)

    except Exception as e:
        print(f"Error: {e}")
    finally:
        # ปลดล็อกกุญแจเพื่อให้คำสั่งถัดไปทำงานได้
        fcntl.flock(lock_file_handle, fcntl.LOCK_UN)
        lock_file_handle.close()

        # ห้ามสั่ง set_servo_pulsewidth(pin, 0) ที่นี่
        # เพราะจะทำให้มอเตอร์คลายตัวและเสียตำแหน่ง
        if 'pi' in locals():
            pi.stop()


if __name__ == "__main__":
    main()
