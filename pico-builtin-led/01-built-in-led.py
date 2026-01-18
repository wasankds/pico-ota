import network
import time
from machine import Pin
from umqtt.simple import MQTTClient

# 1. ตั้งค่า WiFi (ใช้ข้อมูลที่คุณให้ไว้)
SSID = 'WK_AIS_2.4G'
PASSWORD = '0813996766'
MQTT_BROKER = '192.168.1.100' # << ใส่ IP ของ Broker
CLIENT_ID = 'Pico2W_Test'

led = Pin("LED", Pin.OUT) # LED บนบอร์ด Pico 2 W

# 2. เชื่อมต่อ WiFi
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(SSID, PASSWORD)

while not wlan.isconnected():
    print('กำลังเชื่อมต่อ WiFi...')
    time.sleep(1)
print('WiFi เชื่อมต่อแล้ว!')

# ฟังก์ชันเมื่อได้รับข้อความจาก MQTT
def on_message(topic, msg):
    print(f"ได้รับข้อความ: {msg.decode()} บนหัวข้อ: {topic.decode()}")
    if msg.decode() == "ON":
        led.value(1)
    elif msg.decode() == "OFF":
        led.value(0)
        
# 3. เชื่อมต่อ MQTT Broker
client = MQTTClient(CLIENT_ID, MQTT_BROKER)
client.set_callback(on_message)
client.connect()
client.subscribe("pico/led")
print(f'เชื่อมต่อกับ Broker {MQTT_BROKER} แล้ว และรอรับคำสั่งที่ pico/led')

try:
    while True:
        client.check_msg()  # รอเช็คข้อความเข้า
        time.sleep(0.01)       # หน่วงเวลาเล็กน้อย - ป้องกันการใช้ CPU สูงเกินไป
except Exception as e:
    print(f"Error: {e}")
finally:
    client.disconnect()
