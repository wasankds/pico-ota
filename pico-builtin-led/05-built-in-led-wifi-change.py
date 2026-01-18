""" 

เมื่อเปลี่ยนสถานะ WiFi (เชื่อมต่อ/ตัดการเชื่อมต่อ)

"""

import network
import time
import machine
from machine import Pin
from umqtt.simple import MQTTClient
import senko

# --- ตั้งค่า OTA ---
OTA = senko.Senko(
  user="wasankds",
  repo="pico-ota",
  working_dir="pico-builtin-led",
  files=["main.py"]
)

needs_to_send_status = False

# --- ข้อมูลประจำตัวอุปกรณ์ ---
MQTT_BROKER = '192.168.1.100' 
DEVICE_ID = "pico-001"
CLIENT_ID = 'pico-001'

TOPIC_S1_ACTION = DEVICE_ID + "/s1/action"
TOPIC_S1_STATUS = DEVICE_ID + "/s1/status"
TOPIC_QUERY     = DEVICE_ID + "/system/query"
TOPIC_AVAIL     = DEVICE_ID + "/system/availability"

led = Pin("LED", Pin.OUT)

def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    
    # แก้ไข: เพิ่ม comma หลังรายการแรก และลบ comma หลังรายการสุดท้ายเพื่อความสะอาด
    configs = [
      ('Galaxy A7189EE', '12345678'), 
      ('WK_AIS_2.4G', '0813996766')
    ]
    
    for ssid, pwd in configs:
        print(f'\nConnecting to {ssid}...')
        wlan.connect(ssid, pwd)

        for _ in range(10):
            if wlan.isconnected():
                print(f'\nConnected! IP: {wlan.ifconfig()[0]}')
                return True
            time.sleep(1)
            print('.', end='')
        print(f'\nFailed to connect to {ssid}')
        
    return False

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
        if m == "ON": led.value(1)
        elif m == "OFF": led.value(0)
        needs_to_send_status = True
    elif t == TOPIC_QUERY:
        needs_to_send_status = True

# --- เริ่มการทำงาน ---
time.sleep(3) 

if connect_wifi():
    # --- ส่วน OTA: ตรวจสอบและอัปเดต (ทำครั้งเดียวหลังต่อ WiFi ติด) ---
    print("Checking for updates...")
    try:
        if OTA.fetch():
            print("!!! ===> A newer version is available!")
            if OTA.update():
                print("Update completed! Rebooting...")
                machine.reset()
    except Exception as e:
        print("OTA Error:", e)

    # --- ส่วน MQTT: เริ่มทำงานปกติ ---
    client = MQTTClient(CLIENT_ID, MQTT_BROKER)
    client.set_callback(on_message)
    client.set_last_will(TOPIC_AVAIL, "OFFLINE", retain=True, qos=1)

    try:
        client.connect()
        print("MQTT Connected! V2 ====================")
        client.publish(TOPIC_AVAIL, "ONLINE", retain=True, qos=1)
        client.subscribe(TOPIC_S1_ACTION, qos=1)
        client.subscribe(TOPIC_QUERY, qos=1)
        send_status()
        
        while True:
            client.check_msg() 
            if needs_to_send_status:
                send_status()
            time.sleep(0.1)

    except Exception as e:
        print("Loop error:", e)
        time.sleep(5)
        machine.reset()
    finally:
        try:        
            client.publish(TOPIC_AVAIL, "OFFLINE", retain=True, qos=1)
            client.disconnect()
        except: pass
else:
    print("No WiFi available. System will retry in 30s.")
    time.sleep(30)
    machine.reset()