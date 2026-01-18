import network
import time
from machine import Pin
from umqtt.simple import MQTTClient

# 1. ตั้งค่า WiFi (ใช้ข้อมูลที่คุณให้ไว้)
MQTT_BROKER = '192.168.1.100' # << ใส่ IP ของ Broker
SSID = 'WK_AIS_2.4G'
PASSWORD = '0813996766'
CLIENT_ID = 'Pico2W_Test'
TOPIC_LED = "pico-test/led"
TOPIC_QUERY = "pico-test/query"   # <--- หัวข้อไว้รอรับคำถามจาก Node.js
TOPIC_STATUS = "pico-test/status" # <--- หัวข้อไว้ส่งคำตอบกลับไป

led = Pin("LED", Pin.OUT) # LED บนบอร์ด Pico 2 W

# 2. เชื่อมต่อ WiFi
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(SSID, PASSWORD)

while not wlan.isconnected():
    print('กำลังเชื่อมต่อ WiFi...')
    time.sleep(1)
print('WiFi เชื่อมต่อแล้ว!')

# รอจนกว่าจะต่อติด...
if wlan.isconnected():
  status = wlan.ifconfig()
  print(f"✅ Connected! Pico IP Address: {status[0]}")
  
# ฟังก์ชันเมื่อได้รับข้อความจาก MQTT
def on_message(topic, msg):
    t = topic.decode()
    m = msg.decode()
    print(f"ได้รับข้อความ: {m} บนหัวข้อ: {t}")
    
    if t == TOPIC_LED:
        if m == "ON":
            led.value(1)
        elif m == "OFF":
            led.value(0)
            
    # แก้ตรงนี้: ถ้ามีคนส่งอะไรมาที่หัวข้อ query ให้ตอบกลับที่หัวข้อ status
    elif t == TOPIC_QUERY:
        current_status = "ON" if led.value() == 1 else "OFF"
        # ปกติถ้าไม่ใส่ retain=True ข้อความที่ Pico ส่งมาจะเหมือน "เสียงตะโกน" ที่ดังขึ้นแล้วหายไปเลย ใครไม่ได้ฟังอยู่ตอนนั้น (เช่น หน้าเว็บกำลังโหลด) ก็จะไม่ได้ยิน
        # ส่งแบบ Retain เป็น True และ QoS เป็น 1
        client.publish(TOPIC_STATUS, current_status, True, 1)
        print(f"ส่งสถานะปัจจุบันกลับไปที่ {TOPIC_STATUS}: {current_status}")
        
# 3. เชื่อมต่อ MQTT Broker
client = MQTTClient(CLIENT_ID, MQTT_BROKER)
client.set_callback(on_message)
client.connect()
# subscribe หัวข้อต่างๆ 
client.subscribe(TOPIC_LED, qos=1)
client.subscribe(TOPIC_QUERY, qos=1) # Subscribe แค่หัวข้อที่รอฟังคำสั่ง
# ไม่ต้อง Subscribe TOPIC_STATUS เพราะเราเป็นคนส่ง (เดี๋ยวจดหมายตีกัน)
print(f'เชื่อมต่อกับ Broker {MQTT_BROKER} แล้ว และรอรับคำสั่งที่ {TOPIC_LED}')

try:
    while True:
        client.check_msg() # รอเช็คข้อความเข้า
        time.sleep(0.01)
except Exception as e:
    print(f"Error: {e}")
finally:
    client.disconnect()
