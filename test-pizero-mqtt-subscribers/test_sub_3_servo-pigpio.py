import paho.mqtt.client as mqtt
import pigpio
from gpiozero import Motor  # ล้อใช้ gpiozero ต่อได้ปกติ
from time import sleep

# --- ตั้งค่า GPIO และขีดจำกัด ---
PAN_PIN = 17
TILT_PIN = 27
TILT_SAFE_MIN = 1150  # ระยะปลอดภัยป้องกันชน SD Card
PAN_CENTER = 1500
TILT_CENTER = 1500

# เชื่อมต่อ pigpio
pi = pigpio.pi()

# ตั้งค่า L298N (ล้อ) ด้วย pigpio เพื่อความนิ่ง
motor_left = Motor(forward=22, backward=23)
motor_right = Motor(forward=24, backward=25)


def move_servo(pin, pulse_width):
    """ฟังก์ชันสั่งงาน Servo พร้อมตรวจสอบความปลอดภัย"""
    if pin == TILT_PIN:
        if pulse_width < TILT_SAFE_MIN:
            print(f"Warn: {pulse_width} ต่ำเกินไป! ปรับเป็น {TILT_SAFE_MIN}")
            pulse_width = TILT_SAFE_MIN

    if pi.connected:
        pi.set_servo_pulsewidth(pin, pulse_width)


def reset_servos():
    """รีเซ็ต Servo มาตรงกลางตอนเริ่มต้น"""
    print(f"กำลังรีเซ็ต Servo... (Tilt Safe Min: {TILT_SAFE_MIN})")
    move_servo(PAN_PIN, PAN_CENTER)
    move_servo(TILT_PIN, TILT_CENTER)
    sleep(1)
    # ตัดสัญญาณหลังจากเซ็ตตำแหน่งเสร็จเพื่อลดอาการสั่น/ร้อน
    pi.set_servo_pulsewidth(PAN_PIN, 0)
    pi.set_servo_pulsewidth(TILT_PIN, 0)


def on_message(client, userdata, msg):
    command = msg.payload.decode()
    print(f"ได้รับคำสั่ง: {command}")

    # --- ควบคุม Servo ---
    if command == "pan_left":
        move_servo(PAN_PIN, 500)
    elif command == "pan_right":
        move_servo(PAN_PIN, 2500)
    elif command == "pan_center":
        move_servo(PAN_PIN, 1500)

    elif command == "tilt_up":
        move_servo(TILT_PIN, TILT_SAFE_MIN)  # ใช้ค่าปลอดภัยแทน min
    elif command == "tilt_down":
        move_servo(TILT_PIN, 2500)
    elif command == "tilt_center":
        move_servo(TILT_PIN, 1500)

    # --- ควบคุมล้อ ---
    elif command == "forward":
        motor_left.forward()
        motor_right.forward()
    elif command == "backward":
        motor_left.backward()
        motor_right.backward()
    elif command == "stop":
        motor_left.stop()
        motor_right.stop()


# --- เริ่มต้นระบบ ---
if not pi.connected:
    print("ไม่สามารถเชื่อมต่อ pigpio ได้! (กรุณารัน sudo pigpiod)")
    exit()

# 1. รีเซ็ตตำแหน่งทันทีที่รันโปรแกรม
reset_servos()

# 2. ตั้งค่า MQTT
MQTT_BROKER = "192.168.1.131"
TOPIC = "robot/control"

client = mqtt.Client()
client.on_message = on_message
client.connect(MQTT_BROKER, 1883, 60)
client.subscribe(TOPIC)

print("Pi Zero พร้อมทำงานและรอรับคำสั่ง MQTT...")
try:
    client.loop_forever()
except KeyboardInterrupt:
    # ปิดสัญญาณก่อนจบโปรแกรม
    pi.set_servo_pulsewidth(PAN_PIN, 0)
    pi.set_servo_pulsewidth(TILT_PIN, 0)
    pi.stop()
    print("หยุดการทำงาน")
