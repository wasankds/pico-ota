import network
import time
import machine  # เพิ่มการ import machine เพื่อใช้ reset()
from machine import Pin
from umqtt.simple import MQTTClient

# OTA with Senko
import senko
OTA = senko.Senko(               # ข้อมูล GitHub สำหรับ OTA
  user="wasankds", # ชื่อ User GitHub ของคุณ
  repo="pico-ota",       # ชื่อโปรเจกต์
  working_dir="pico-001",           # โฟลเดอร์ใน GitHub ที่เก็บโค้ด (ถ้ามี)
  files=["main.py"]            # ไฟล์ที่ต้องการให้อัปเดต
)

# --- 0. ตัวแปรสถานะ (Flag) ---
needs_to_send_status: bool = False

# --- 1. ข้อมูลประจำตัวอุปกรณ์ ---
MQTT_BROKER = '192.168.1.100' 
DEVICE_ID = "pico-001"
CLIENT_ID = 'pico_001'
SSID = 'WK_AIS_2.4G'
PASSWORD = '0813996766'

# --- 2. การกำหนด Topic ---
TOPIC_S1_ACTION = DEVICE_ID + "/s1/action"
TOPIC_S1_STATUS = DEVICE_ID + "/s1/status"
TOPIC_QUERY     = DEVICE_ID + "/system/query"
TOPIC_AVAIL     = DEVICE_ID + "/system/availability"

led = Pin("LED", Pin.OUT)

def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(SSID, PASSWORD)
    print('Connecting to WiFi...', end='')
    while not wlan.isconnected():
        print('.', end='')
        time.sleep(1)
    print('\nWiFi Connected! IP:', wlan.ifconfig()[0])

def send_status():
    global needs_to_send_status
    try:
        current_val = "ON" if led.value() == 1 else "OFF"
        client.publish(TOPIC_S1_STATUS, current_val, retain=False, qos=1)
        print(f"Reported status: {current_val}")
        
        needs_to_send_status = False 
    except Exception as e:
        print("Publish failed:", e)

def on_message(topic, msg):
    global needs_to_send_status
    t = topic.decode()
    m = msg.decode().upper()
    print(f"Message received: {t} -> {m}")
    
    if t == TOPIC_S1_ACTION:
        if m == "ON": 
            led.value(1)
        elif m == "OFF": 
            led.value(0)
        needs_to_send_status = True
        
    elif t == TOPIC_QUERY:
        needs_to_send_status = True
        
time.sleep(3)
connect_wifi()
print("Checking for updates...")

try:
  if OTA.fetch():
    print("A newer version is available!")
    if OTA.update():
        print("Update completed! Rebooting...")
        machine.reset()
except Exception as e:
  print("OTA Error:", e)
    
client = MQTTClient(CLIENT_ID, MQTT_BROKER)
client.set_callback(on_message)
client.set_last_will(TOPIC_AVAIL, "OFFLINE", retain=True, qos=1)

try:
    client.connect()
    print("MQTT Connected!")
    client.publish(TOPIC_AVAIL, "ONLINE", retain=True, qos=1)
    # บอก Broker ว่า หัวข้อเหล่านี้ขอรับแบบ QoS 1 นะ (ถ้าฉันได้รับแล้ว เดี๋ยวฉันจะส่ง PUBACK กลับไปบอก Broker เอง)
    client.subscribe(TOPIC_S1_ACTION, qos=1)
    client.subscribe(TOPIC_QUERY, qos=1)
    
    # ส่งสถานะครั้งแรก
    send_status()
    
    while True:
        client.check_msg() 
        
        # ส่ง Status นอก Callback เพื่อป้องกัน Recursion Error
        if needs_to_send_status:
            send_status()
            
        time.sleep(0.1)

except Exception as e:
    print("Loop error:", e)
    time.sleep(5)
    machine.reset() # การสั่ง Restart บอร์ดเมื่อเกิด Error
finally:
    try:        
        client.publish(TOPIC_AVAIL, "OFFLINE", retain=True, qos=1)
        client.disconnect()
    except: 
        pass
