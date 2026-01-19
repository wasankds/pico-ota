import time
import machine
from machine import Pin
from umqtt.simple import MQTTClient
import senko
import wifi_manager
import config

# --- เตรียมระบบ OTA ---
OTA = senko.Senko(
  user=config.OTA_USER, repo=config.OTA_REPO,
  working_dir=config.OTA_DIR, files=config.OTA_FILES
)
led = Pin("LED", Pin.OUT)
needs_to_send_status = False

# --- ฟังก์ชันส่งสถานะ (ดึง Topic จาก config) ---
def send_status(client):
  global needs_to_send_status
  try:
    current_val = "ON" if led.value() == 1 else "OFF"
    client.publish(config.TOPIC_S1_STATUS, current_val, retain=False, qos=1)
    print(f"Reported status: {current_val}")
    needs_to_send_status = False 
  except Exception as e:
    print("Publish failed:", e)

# --- ฟังก์ชันเมื่อมีข้อความเข้า ---
def on_message(topic, msg):
    global needs_to_send_status
    t = topic.decode()
    m = msg.decode().upper()
    print(f"Message received: {t} -> {m}")
    
    if t == config.TOPIC_S1_ACTION:
      if m == "ON": led.value(1)
      elif m == "OFF": led.value(0)
      needs_to_send_status = True  # ยกธงบอกว่า "ไฟเปลี่ยนสถานะแล้ว ต้องรายงาน"

    elif t == config.TOPIC_QUERY:
      needs_to_send_status = True  # ยกธงบอกว่า "มีคนถามสถานะเข้ามา ต้องตอบกลับ"

# --- เริ่มการทำงาน ---
time.sleep(3)

if wifi_manager.connect_wifi(config.WIFI_CONFIGS):

    # 1. OTA Update
    if config.ENABLE_OTA:
      try:
          if OTA.fetch():
              if OTA.update():
                  print("Update completed! Rebooting...")
                  machine.reset()
      except: pass
    else:
      print("OTA is disabled (Bypassed)")

    # 2. MQTT Setup
    client = MQTTClient(config.CLIENT_ID, config.MQTT_BROKER)
    client.set_callback(on_message)
    # ตั้งค่า Last Will (บอก Broker ว่าถ้าฉันหายไปให้ประกาศ OFFLINE)
    client.set_last_will(config.TOPIC_AVAIL, "OFFLINE", retain=True, qos=1)

    try:
        client.connect()
        print(f"MQTT Connected! Device: {config.DEVICE_ID}")
        client.publish(config.TOPIC_AVAIL, "ONLINE", retain=True, qos=1)
        
        # Subscribe หัวข้อที่ต้องการ
        client.subscribe(config.TOPIC_S1_ACTION, qos=1)
        client.subscribe(config.TOPIC_QUERY, qos=1)
        
        send_status(client) # ส่งสถานะครั้งแรก
        
        while True:
            client.check_msg() 

            if needs_to_send_status:
                send_status(client)
            time.sleep(0.1)

    except Exception as e:
        print("Error:", e)
        time.sleep(5)
        machine.reset()
    finally:
        try:
            client.publish(config.TOPIC_AVAIL, "OFFLINE", retain=True, qos=1)
            client.disconnect()
        except: pass
else:
    time.sleep(10)
    machine.reset()