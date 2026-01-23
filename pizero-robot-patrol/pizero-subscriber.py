import threading
import paho.mqtt.client as mqtt
import pigpio
import time

# --- การตั้งค่า GPIO (ย้ายขึ้นมาไว้ด้านบนสุดเพื่อให้ทุกฟังก์ชันมองเห็น) ---
PAN_PIN = 17
TILT_PIN = 27
IN1, IN2 = 6, 13
IN3, IN4 = 19, 26

PAN_MIN, PAN_MAX = 500, 2500
TILT_MIN, TILT_MAX = 1150, 2500
PAN_CENTER, TILT_CENTER = 1500, 1500

# ตัวแปรสถานะ
curr_pan = PAN_CENTER
curr_tilt = TILT_CENTER
servo_move_dir = None

pi = pigpio.pi()


def servo_loop():
    """ฟังก์ชันทำงานเบื้องหลังคอยขยับ Servo"""
    global curr_pan, curr_tilt, servo_move_dir
    while True:
        if servo_move_dir == 'pan_l':
            curr_pan = max(PAN_MIN, curr_pan - 20)
            pi.set_servo_pulsewidth(PAN_PIN, curr_pan)
        elif servo_move_dir == 'pan_r':
            curr_pan = min(PAN_MAX, curr_pan + 20)
            pi.set_servo_pulsewidth(PAN_PIN, curr_pan)
        elif servo_move_dir == 'tilt_u':
            curr_tilt = min(TILT_MAX, curr_tilt + 20)
            pi.set_servo_pulsewidth(TILT_PIN, curr_tilt)
        elif servo_move_dir == 'tilt_d':
            curr_tilt = max(TILT_MIN, curr_tilt - 20)
            pi.set_servo_pulsewidth(TILT_PIN, curr_tilt)

        time.sleep(0.05)


# เริ่ม Thread ทันที
t = threading.Thread(target=servo_loop, daemon=True)
t.start()


def move_to_target(pin, target_pw, delay=0.005):
    global curr_pan, curr_tilt
    target_pw = max(500, min(2500, target_pw))  # กันค่าเกิน

    current = curr_pan if pin == PAN_PIN else curr_tilt
    if current != target_pw:
        step_dir = 5 if target_pw > current else -5
        for pw in range(current, target_pw, step_dir):
            pi.set_servo_pulsewidth(pin, pw)
            time.sleep(delay)

    pi.set_servo_pulsewidth(pin, target_pw)
    if pin == PAN_PIN:
        curr_pan = target_pw
    else:
        curr_tilt = target_pw


def wheels_control(l1, l2, r1, r2):
    pi.write(IN1, l1)
    pi.write(IN2, l2)
    pi.write(IN3, r1)
    pi.write(IN4, r2)


def on_message(client, userdata, msg):
    # จุดสำคัญ: ต้องประกาศ global servo_move_dir ที่นี่!
    global curr_pan, curr_tilt, servo_move_dir
    command = msg.payload.decode()

    # จัดการคำสั่งล้อ (ลดการทำงานซ้ำ)
    wheel_cmds = ["forward", "backward", "left", "right", "stop"]
    if command in wheel_cmds:
        if hasattr(on_message, "last_wheel_cmd") and on_message.last_wheel_cmd == command:
            return
        on_message.last_wheel_cmd = command
        print(f"Executing Wheel: {command}")

        # --- แก้ไขส่วนควบคุมล้อตามทิศทางใหม่ที่คุณต้องการ ---
        if command == "forward":  # ปุ่ม UP ในเว็บ
            # แก้ให้สั่งงานเป็น Left (ตามที่คุณบอกว่า Up เป็น Left)
            wheels_control(0, 1, 1, 0)

        elif command == "backward":  # ปุ่ม DOWN ในเว็บ
            # แก้ให้สั่งงานเป็น Right (ตามที่คุณบอกว่า Down เป็น Right)
            wheels_control(1, 0, 0, 1)

        elif command == "left":     # ปุ่ม LEFT ในเว็บ
            # แก้ให้สั่งงานเป็น Forward (ตามที่คุณบอกว่า Left เป็น Forward)
            wheels_control(1, 0, 1, 0)

        elif command == "right":    # ปุ่ม RIGHT ในเว็บ
            # แก้ให้สั่งงานเป็น Backward (ตามที่คุณบอกว่า Right เป็น Down/Backward)
            wheels_control(0, 1, 0, 1)

        elif command == "stop":
            wheels_control(0, 0, 0, 0)

    # จัดการคำสั่ง Servo แบบต่อเนื่อง
    elif "_start" in command or command == "servo_stop":
        print(f"Executing Servo: {command}")
        if command == "pan_left_start":
            servo_move_dir = 'pan_l'
        elif command == "pan_right_start":
            servo_move_dir = 'pan_r'
        elif command == "tilt_up_start":
            servo_move_dir = 'tilt_u'
        elif command == "tilt_down_start":
            servo_move_dir = 'tilt_d'
        elif command == "servo_stop":
            servo_move_dir = None

    # จัดการคำสั่ง Reset
    elif command == "pan_center":
        servo_move_dir = None
        move_to_target(PAN_PIN, PAN_CENTER)
    elif command == "tilt_center":
        servo_move_dir = None
        move_to_target(TILT_PIN, TILT_CENTER)


if not pi.connected:
    exit()

try:
    print("ระบบกำลังเริ่มต้น: รีเซ็ต Servo...")
    move_to_target(PAN_PIN, PAN_CENTER)
    move_to_target(TILT_PIN, TILT_CENTER)
    wheels_control(0, 0, 0, 0)

    client = mqtt.Client()
    client.on_message = on_message
    client.connect("192.168.1.131", 1883, 60)
    client.subscribe("robot/control")

    print("--- EagleEye Robot: Ready (Smooth Continuous Mode) ---")
    client.loop_forever()

except KeyboardInterrupt:
    print("\nปิดระบบ...")
finally:
    servo_move_dir = None
    wheels_control(0, 0, 0, 0)
    pi.set_servo_pulsewidth(PAN_PIN, 0)
    pi.set_servo_pulsewidth(TILT_PIN, 0)
    pi.stop()
