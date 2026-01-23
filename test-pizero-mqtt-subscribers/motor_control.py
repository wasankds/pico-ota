# Python

import paho.mqtt.client as mqtt
import RPi.GPIO as GPIO

# ตั้งค่าขา GPIO สำหรับ L298N
ENA = 18  # ความเร็วมอเตอร์ (PWM)
IN1 = 23
IN2 = 24

GPIO.setmode(GPIO.BCM)
GPIO.setup(ENA, GPIO.OUT)
GPIO.setup(IN1, GPIO.OUT)
GPIO.setup(IN2, GPIO.OUT)

pwm = GPIO.PWM(ENA, 100)  # ความถี่ 100Hz
pwm.start(0)

# ฟังก์ชันเมื่อเชื่อมต่อ MQTT สำเร็จ


def on_connect(client, userdata, flags, rc):
    print("Connected to Pi 5 Broker with result code "+str(rc))
    client.subscribe("robot/motor")  # รอฟังหัวข้อนี้

# ฟังก์ชันเมื่อได้รับข้อความ (คำสั่ง)


def on_message(client, userdata, msg):
    command = msg.payload.decode()
    print(f"Received: {command}")

    if command == "forward":
        GPIO.output(IN1, GPIO.HIGH)
        GPIO.output(IN2, GPIO.LOW)
        pwm.ChangeDutyCycle(80)  # วิ่งความเร็ว 80%
    elif command == "stop":
        GPIO.output(IN1, GPIO.LOW)
        GPIO.output(IN2, GPIO.LOW)
        pwm.ChangeDutyCycle(0)


client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

# ใส่ IP Address ของ Pi 5 ที่นี่
client.connect("192.168.1.XX", 1883, 60)

client.loop_forever()  # รันค้างไว้เพื่อรอรับคำสั่ง
