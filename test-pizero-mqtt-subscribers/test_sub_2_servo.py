""" 
pi มีอาการกระตุก ทั้งๆที่ยังไม่ได้สั่งงาน 

"""

import paho.mqtt.client as mqtt
from gpiozero import Servo, Motor
from time import sleep

# --- การตั้งค่าขา GPIO (ปรับเปลี่ยนได้ตามที่ต่อจริง) ---
# Servo 2 ตัว
servo1 = Servo(17)  # ขา GPIO 17
servo2 = Servo(27)  # ขา GPIO 27

# L298N + TT Motor (ล้อ)
# ล้อซ้าย: Forward=GPIO 22, Backward=GPIO 23
motor_left = Motor(forward=22, backward=23)
# ล้อขวา: Forward=GPIO 24, Backward=GPIO 25
motor_right = Motor(forward=24, backward=25)

MQTT_BROKER = "192.168.1.131"  # เปลี่ยนเป็น IP ของ Pi5x2
TOPIC = "robot/control"


def on_message(client, userdata, msg):
    command = msg.payload.decode()
    print(f"ได้รับคำสั่ง: {command}")

    # --- ส่วนการควบคุมล้อ ---
    if command == "forward":
        motor_left.forward()
        motor_right.forward()
    elif command == "backward":
        motor_left.backward()
        motor_right.backward()
    elif command == "stop":
        motor_left.stop()
        motor_right.stop()

    # --- ส่วนการควบคุม Servo ---
    elif command == "look_left":
        servo1.min()
    elif command == "look_right":
        servo1.max()
    elif command == "look_center":
        servo1.mid()

    # เพิ่มส่วนตัดสัญญาณ PWM หลังเคลื่อนที่เสร็จ
    elif command == "look_left":
        servo1.min()
        sleep(0.5)      # รอให้เคลื่อนที่ถึงจุด
        servo1.detach()  # ตัดสัญญาณ PWM ออก (จะหยุดสั่นทันที)


client = mqtt.Client()
client.on_message = on_message
client.connect(MQTT_BROKER, 1883, 60)
client.subscribe(TOPIC)

print("Pi Zero พร้อมควบคุมมอเตอร์แล้ว...")
client.loop_forever()
