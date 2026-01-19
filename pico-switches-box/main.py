from machine import Pin, SPI
import machine
import utime
import dht
import ntptime
import config
import wifi_manager
import gc # เพิ่มไว้ที่หัวไฟล์
from umqtt.simple import MQTTClient
from tft_control import TFTDisplay, C_BLACK, C_WHITE, C_YELLOW, COLOR_BTN_ON, COLOR_BTN_OFF, COLOR_TEMP, COLOR_HUMID
sysname : str = "Eagle Eye Legion"
version : str = "1.0.4"

# --- 1. Hardware Setup ---
relay1 = Pin(14, Pin.OUT, value=1)
relay2 = Pin(15, Pin.OUT, value=1)
sensor = dht.DHT11(Pin(22))

# SPI ความเร็วมาตรฐาน 10MHz เสถียรสำหรับจอ 2.8/3.2 นิ้ว
spi = SPI(0, baudrate=10000000, polarity=0, phase=0, sck=Pin(18), mosi=Pin(19), miso=Pin(16, Pin.IN, Pin.PULL_UP))
lcd_pins = {"lcd_cs": Pin(17, Pin.OUT, value=1), "dc": Pin(20, Pin.OUT, value=0), "rst": Pin(21, Pin.OUT, value=1), "touch_cs": Pin(2, Pin.OUT, value=1)}
tft = TFTDisplay(spi, **lcd_pins)

# --- 2. System Variables ---
client = None
mqtt_connected = False
last_mqtt_reconnect = 0
needs_to_send_status = False 
old_t, old_h, old_time = "", "", ""

btn1 = {"x": 20, "y": 95, "w": 120, "h": 110, "state": False, "label": "#1", "relay": relay1, "topic": config.TOPIC_S1_STATUS}
btn2 = {"x": 180, "y": 95, "w": 120, "h": 110, "state": False, "label": "#2", "relay": relay2, "topic": config.TOPIC_S2_STATUS}

# --- 3. Functions ---

def draw_btn(btn):
    color = COLOR_BTN_ON if btn["state"] else COLOR_BTN_OFF
    tft.fill_rect(btn["x"], btn["y"], btn["w"], btn["h"], color)
    tft.draw_text(btn["x"] + 40, btn["y"] + 30, btn["label"], C_WHITE, 3)
    tft.draw_text(btn["x"] + 30, btn["y"] + 70, "ON" if btn["state"] else "OFF", C_WHITE, 3)

def send_all_status(mqtt_client):
  global needs_to_send_status
  try:
    mqtt_client.publish(config.TOPIC_S1_STATUS, "ON" if btn1["state"] else "OFF", retain=True, qos=1)
    mqtt_client.publish(config.TOPIC_S2_STATUS, "ON" if btn2["state"] else "OFF", retain=True, qos=1)
    send_dht_data(mqtt_client)
    needs_to_send_status = False
    print("MQTT Status Synced")
  except: pass

# --- เพิ่มฟังก์ชันนี้เพื่อจัดการ OTA โดยเฉพาะ ---
def trigger_ota():
    global mqtt_connected, client
    print("Received Update Command via MQTT")
    
    # 1. แสดงสถานะบนจอก่อนเลย
    tft.fill_rect(0, 0, 320, 240, C_BLACK)
    tft.draw_text(60, 100, "SYSTEM UPDATE", C_YELLOW, 2)
    tft.draw_text(40, 130, "PREPARING RAM...", C_WHITE, 1)

    # 2. ปิด MQTT และล้าง RAM (สำคัญมากเพื่อแก้ Error -2)
    try:
        if client:
            client.publish(config.TOPIC_AVAIL, "UPDATING", retain=True)
            utime.sleep_ms(200)
            client.disconnect()
            client = None
    except: pass
    
    mqtt_connected = False
    gc.collect() # ล้างขยะใน Memory
    utime.sleep(1)

    # 3. เริ่มกระบวนการ Senko OTA
    tft.fill_rect(0, 125, 320, 40, C_BLACK)
    tft.draw_text(50, 130, "DOWNLOADING FILES...", C_WHITE, 1)
    
    try:
        import senko        
        gc.collect() # บังคับ gc อีกรอบก่อนเริ่ม Senko

        OTA = senko.Senko(user=config.OTA_USER, repo=config.OTA_REPO, 
                         working_dir=config.OTA_DIR, files=config.OTA_FILES)
        
        if OTA.update():
            # 1. เคลียร์จอเป็นสีเขียว
            tft.fill_rect(0, 0, 320, 240, COLOR_BTN_ON)
            utime.sleep_ms(300) # ให้เวลา Controller นิ่งหลังถมสีเขียวเต็มจอ
            
            # 2. Dummy Write ล้างหัวเข็ม SPI
            tft.fill_rect(0, 0, 1, 1, COLOR_BTN_ON) 
            
            # 3. แยกวาดข้อความเป็น 2 ส่วน (ลด Buffer)
            tft.draw_text(40, 100, "UPDATE SUCCESS!", C_WHITE, 2)
            utime.sleep_ms(100) # เว้นจังหวะนิดนึง
            tft.draw_text(40, 140, "REBOOTING...", C_WHITE, 2)
            
            utime.sleep(2)
            machine.reset()
        else:
            # กรณีไม่มีตัวอัปเดตใหม่
            tft.fill_rect(0, 150, 320, 40, C_BLACK)
            tft.draw_text(60, 160, "VERSION IS UP TO DATE", C_YELLOW, 1)
            utime.sleep(2)
            machine.reset()
    except Exception as e:
      # กรณี Error
        tft.fill_rect(0, 0, 320, 240, COLOR_BTN_OFF) # จอแดง
        utime.sleep_ms(200)
        tft.draw_text(20, 110, "OTA FAILED!", C_WHITE, 2)
        tft.draw_text(20, 150, "ERROR: " + str(e), C_WHITE, 1)
        utime.sleep(3)
        machine.reset()
        
# --- on_message ให้รองรับคำสั่งจาก Node.js ---
def on_message(topic, msg):
    global needs_to_send_status
    t = topic.decode()
    m = msg.decode().upper()
    
    # ตรวจสอบ Topic จาก Node.js (deviceId/system/update)
    if t.endswith(config.TOPIC_UPDATE) and m == "UPDATE":
        trigger_ota()
        return # ออกจากฟังก์ชันทันที
    
    # คำสั่งควบคุม Relay เดิม
    if t == config.TOPIC_S1_ACTION:
        btn1["state"] = (m == "ON")
        relay1.value(0 if btn1["state"] else 1)
        draw_btn(btn1)
        
    elif t == config.TOPIC_S2_ACTION:
        btn2["state"] = (m == "ON")
        relay2.value(0 if btn2["state"] else 1)
        draw_btn(btn2)
    
    needs_to_send_status = True

def try_mqtt_connect():
    global client, mqtt_connected
    try:
        client = MQTTClient(config.CLIENT_ID, config.MQTT_BROKER, keepalive=60)
        client.set_callback(on_message)
        client.set_last_will(config.TOPIC_AVAIL, "OFFLINE", retain=True, qos=1)
        client.connect()
        # sub
        client.subscribe(config.TOPIC_S1_ACTION)
        client.subscribe(config.TOPIC_S2_ACTION)
        client.subscribe(config.TOPIC_QUERY)
        client.subscribe(config.TOPIC_UPDATE)
        # pub
        client.publish(config.TOPIC_AVAIL, "ONLINE", retain=True, qos=1)
        
        mqtt_connected = True
        return True
    except:
        mqtt_connected = False
        return False

def update_info():
    global old_t, old_h, old_time
    try:
        t_now = utime.localtime(utime.time() + 7 * 3600)
        time_str = "{:02d}:{:02d}:{:02d}".format(t_now[3], t_now[4], t_now[5])
        if time_str != old_time:
            if old_time != "": tft.draw_text(80, 10, old_time, C_BLACK, 3)
            tft.draw_text(80, 10, time_str, C_WHITE, 3)
            old_time = time_str
            
        sensor.measure()
        new_t, new_h = "T:{}C".format(sensor.temperature()), "H:{}%".format(sensor.humidity())
        if new_t != old_t:
            if old_t != "": tft.draw_text(30, 50, old_t, C_BLACK, 2)
            tft.draw_text(30, 50, new_t, COLOR_TEMP, 2)
            old_t = new_t
        if new_h != old_h:
            if old_h != "": tft.draw_text(180, 50, old_h, C_BLACK, 2)
            tft.draw_text(180, 50, new_h, COLOR_HUMID, 2)
            old_h = new_h
    except: pass

def send_dht_data(mqtt_client):
    try:
        msg = '{{"t": "{}", "h": "{}"}}'.format(sensor.temperature(), sensor.humidity())
        mqtt_client.publish(config.TOPIC_SENSOR_DHT, msg)
    except: pass


# --- 4. Startup Sequence (แบบละเอียด เช็คสถานะได้) ---
tft.fill_rect(0, 0, 320, 240, C_BLACK)
# แถวที่ 1: ชื่อระบบ (Size 2) และ เวอร์ชั่น (Size 1 เพื่อลดขนาดและกันทับ)
tft.draw_text(20, 30, sysname, C_YELLOW, 1)
# ขยับไปทางขวา (X=210) และใช้ขนาดเล็ก (Size 1) เพื่อเว้นช่องไฟให้สวยงาม
tft.draw_text(210, 30, "v" + version, C_WHITE, 1)

# แถวที่ 2: สถานะเริ่มเชื่อมต่อ Wi-Fi
tft.draw_text(20, 70, "CONNECTING WIFI...", C_WHITE, 2)

if wifi_manager.connect_wifi(config.WIFI_CONFIGS):
    # แถวที่ 3: ยืนยัน Wi-Fi (วาดบรรทัดใหม่ ไม่ทับบรรทัดเดิม)
    tft.draw_text(20, 100, "WIFI: CONNECTED", COLOR_BTN_ON, 2)
    
    try: ntptime.settime()
    except: pass
    
    # แถวที่ 4: สถานะเริ่มเชื่อมต่อ MQTT
    tft.draw_text(20, 140, "CONNECTING MQTT...", C_WHITE, 2)
    
    if try_mqtt_connect():
        # แถวที่ 5: ยืนยัน MQTT
        tft.draw_text(20, 170, "MQTT: CONNECTED", COLOR_BTN_ON, 2)
    else:
        tft.draw_text(20, 170, "MQTT: FAILED", COLOR_BTN_OFF, 2)
else:
    tft.draw_text(20, 100, "WIFI: FAILED", COLOR_BTN_OFF, 2)

# หน่วงเวลาให้เห็นสถานะครบทุกแถว
utime.sleep(2)
tft.fill_rect(0, 0, 320, 240, C_BLACK)
draw_btn(btn1); draw_btn(btn2)

# --- 5. Main Loop ---
last_tick = 0
last_press = 0
last_dht_send = 0

while True:
    now = utime.ticks_ms()
    
    # 5.1 MQTT Loop
    if mqtt_connected:
        try:
            client.check_msg()
        except:
            mqtt_connected = False
    elif utime.ticks_diff(now, last_mqtt_reconnect) > 15000:
        try_mqtt_connect()
        last_mqtt_reconnect = now

    if needs_to_send_status and mqtt_connected:
      send_all_status(client)

    # 5.2 Touch Control (เน้นแค่ปุ่ม ON/OFF)
    pos = tft.get_touch()
    if pos:
        tx, ty = pos
        if utime.ticks_diff(now, last_press) > 350:
            for btn in [btn1, btn2]:
                if btn["x"] <= tx <= btn["x"]+btn["w"] and btn["y"] <= ty <= btn["y"]+btn["h"]:
                    btn["state"] = not btn["state"]
                    btn["relay"].value(0 if btn["state"] else 1)
                    draw_btn(btn)
                    needs_to_send_status = True
                    last_press = now

    # 5.3 Auto Update (ทำงานเฉพาะตอนไม่ได้กดจอ)
    if not pos:
        if utime.ticks_diff(now, last_tick) > 1000:
            update_info()
            last_tick = now
            
        if utime.ticks_diff(now, last_dht_send) > 10000:
            if mqtt_connected:
                send_dht_data(client)
                last_dht_send = now
                
    utime.sleep_ms(50)