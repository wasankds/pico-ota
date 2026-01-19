import time
import machine
from machine import Pin
from umqtt.simple import MQTTClient
import senko
import wifi_manager
import config

# --- การตั้งค่าขาอุปกรณ์ ---
led = Pin("LED", Pin.OUT)
button = Pin(15, Pin.IN, Pin.PULL_UP) # ต่อสวิตช์ GP15 กับ GND

# --- ตัวแปรควบคุมระบบ ---
needs_to_send_status = False
last_button_state = 1 # สถานะปุ่มก่อนหน้า (1 คือไม่กด)

# --- ระบบ OTA ---
OTA = senko.Senko(
    user=config.OTA_USER, repo=config.OTA_REPO,
    working_dir=config.OTA_DIR, files=config.OTA_FILES
)

# --- ฟังก์ชันส่งสถานะไป MQTT ---
def send_status(client):
    global needs_to_send_status
    try:
        current_val = "ON" if led.value() == 1 else "OFF"
        client.publish(config.TOPIC_S1_STATUS, current_val, retain=False, qos=1)
        print(f"Reported to Web: {current_val}")
        needs_to_send_status = False 
    except Exception as e:
        print("Publish failed:", e)

# --- ฟังก์ชันเมื่อมีข้อความจาก Web เข้ามา ---
def on_message(topic, msg):
    global needs_to_send_status
    t = topic.decode()
    m = msg.decode().upper()
    print(f"Web Command: {t} -> {m}")
    
    if t == config.TOPIC_S1_ACTION:
        if m == "ON": led.value(1)
        elif m == "OFF": led.value(0)
        needs_to_send_status = True # ยกธงเพื่อให้ส่งสถานะกลับไปยืนยันบนหน้าเว็บ
    elif t == config.TOPIC_QUERY:
        needs_to_send_status = True

# --- เริ่มการทำงาน ---
time.sleep(1) # รอระบบเสถียร

if wifi_manager.connect_wifi(config.WIFI_CONFIGS):
  
    # 1. เช็ค OTA (ถ้าเปิดใช้งานใน config)
    if getattr(config, 'ENABLE_OTA', False):
        print("Checking for updates...")
        try:
            if OTA.fetch():
                if OTA.update():
                    print("Update found! Rebooting...")
                    machine.reset()
        except: pass
    else:
        print("OTA Bypassed")

    # 2. ตั้งค่า MQTT
    client = MQTTClient(config.CLIENT_ID, config.MQTT_BROKER)
    client.set_callback(on_message)
    client.set_last_will(config.TOPIC_AVAIL, "OFFLINE", retain=True, qos=1)

    try:
        client.connect()
        client.publish(config.TOPIC_AVAIL, "ONLINE", retain=True, qos=1)
        client.subscribe(config.TOPIC_S1_ACTION, qos=1)
        client.subscribe(config.TOPIC_QUERY, qos=1)
        
        send_status(client) # แจ้งสถานะครั้งแรกตอนเริ่มเครื่อง        
        print("System Ready! ลองกดปุ่มที่บอร์ด หรือสั่งจาก Web ได้เลย")

        while True:
          
            # ก. เช็คคำสั่งจากหน้าเว็บ
            client.check_msg() 

            # ข. เช็คการกดปุ่มที่ตัวบอร์ด (Logic ที่เราเพิ่งทดสอบกัน)
            current_btn = button.value()
            if current_btn != last_button_state and current_btn == 0:
              
              # สลับไฟ LED
              led.value(not led.value())
              print("Physical Button Pressed!")
              
              # ยกธงบอกโปรแกรมว่า "ต้องรีบไปบอกหน้าเว็บว่าไฟเปลี่ยนแล้วนะ"
              needs_to_send_status = True
              time.sleep(0.2) # Debounce
            
            last_button_state = current_btn

            # ค. ถ้ามีการยกธง (จากปุ่มกด หรือจากคำสั่งเว็บ) ให้ส่งข้อมูล
            if needs_to_send_status:
                send_status(client)

            time.sleep(0.1) # รักษาความไว (Response time)

    except Exception as e:
        print("Error:", e)
        time.sleep(5)
        machine.reset()