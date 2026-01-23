import paho.mqtt.client as mqtt
MQTT_BROKER = "192.168.1.131" 	# เปลี่ยนเป็น IP ของ Pi 5
TOPIC = "robot/control"

# ฟังก์ชันเมื่อได้รับข้อความ


def on_message(client, userdata, msg):
    print(f"ได้รับคำสั่ง: {msg.payload.decode()} บน Topic: {msg.topic}")


client = mqtt.Client()
client.on_message = on_message

client.connect(MQTT_BROKER, 1883, 60)
client.subscribe(TOPIC)

print("Pi Zero กำลังรอรับคำสั่ง...")
client.loop_forever()
