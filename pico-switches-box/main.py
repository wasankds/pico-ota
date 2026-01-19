from machine import Pin, SPI
import machine
import senko
import utime
import dht
import ntptime
import config
import wifi_manager
from umqtt.simple import MQTTClient
from tft_control import TFTDisplay, C_BLACK, C_WHITE, C_YELLOW, COLOR_BTN_ON, COLOR_BTN_OFF, COLOR_TEMP, COLOR_HUMID

# --- 1. Hardware Setup ---
relay1 = Pin(14, Pin.OUT, value=1)
relay2 = Pin(15, Pin.OUT, value=1)
sensor = dht.DHT11(Pin(22))

spi = SPI(0, baudrate=10000000, polarity=0, phase=0, sck=Pin(18), mosi=Pin(19), miso=Pin(16, Pin.IN, Pin.PULL_UP))
lcd_pins = {"lcd_cs": Pin(17, Pin.OUT, value=1), "dc": Pin(20, Pin.OUT, value=0), "rst": Pin(21, Pin.OUT, value=1), "touch_cs": Pin(2, Pin.OUT, value=1)}
tft = TFTDisplay(spi, **lcd_pins)

# --- 2. System Variables ---
client = None
mqtt_connected = False
last_mqtt_reconnect = 0
needs_to_send_status = False # สำหรับแจ้งเตือนการส่งสถานะ
old_t, old_h, old_time = "", "", ""

# เพิ่มข้อมูล topic เข้าไปใน dict เพื่อให้จัดการง่ายขึ้น
btn1 = {"x": 20, "y": 95, "w": 120, "h": 110, "state": False, "label": "#1", "relay": relay1, "topic": config.TOPIC_S1_STATUS}
btn2 = {"x": 180, "y": 95, "w": 120, "h": 110, "state": False, "label": "#2", "relay": relay2, "topic": config.TOPIC_S2_STATUS}

# --- 3. Functions ---

def draw_btn(btn):
    color = COLOR_BTN_ON if btn["state"] else COLOR_BTN_OFF
    tft.fill_rect(btn["x"], btn["y"], btn["w"], btn["h"], color)
    tft.draw_text(btn["x"] + 40, btn["y"] + 30, btn["label"], C_WHITE, 3)
    tft.draw_text(btn["x"] + 30, btn["y"] + 70, "ON" if btn["state"] else "OFF", C_WHITE, 3)

# ฟังก์ชันส่งสถานะทั้งหมด (S1 และ S2) เพื่อ Sync กับหน้าเว็บ
def send_all_status(mqtt_client):
    global needs_to_send_status
    try:
        # ส่งสถานะ S1
        s1_val = "ON" if btn1["state"] else "OFF"
        mqtt_client.publish(config.TOPIC_S1_STATUS, s1_val, retain=True, qos=1)
        print(f"Sent S1 Status: {s1_val}")
        
        # ส่งสถานะ S2
        s2_val = "ON" if btn2["state"] else "OFF"
        mqtt_client.publish(config.TOPIC_S2_STATUS, s2_val, retain=True, qos=1)
        print(f"Sent S2 Status: {s2_val}")
        
        # ส่ง DHT ไปพร้อมกันเลยตอนที่มีการ Query
        send_dht_data(mqtt_client)
        
        needs_to_send_status = False
        print(f"Sync Status to Web: S1={s1_val}, S2={s2_val}, DHT Sent")
    except Exception as e:
        print("Failed to sync status:", e)

def on_message(topic, msg):
  global needs_to_send_status
  t = topic.decode() 
  m = msg.decode().upper()
  
  if t == config.TOPIC_S1_ACTION:
      btn1["state"] = (m == "ON") 
      relay1.value(0 if btn1["state"] else 1)
      draw_btn(btn1)
      needs_to_send_status = True
  elif t == config.TOPIC_S2_ACTION:
      btn2["state"] = (m == "ON") 
      relay2.value(0 if btn2["state"] else 1)
      draw_btn(btn2)
      needs_to_send_status = True
  elif t == config.TOPIC_QUERY:  
      print(f'Query Received: {m}')  
      needs_to_send_status = True

def try_mqtt_connect():
    global client, mqtt_connected
    try:
        client = MQTTClient(config.CLIENT_ID, config.MQTT_BROKER, keepalive=60)
        client.set_callback(on_message)
        client.set_last_will(config.TOPIC_AVAIL, "OFFLINE", retain=True, qos=1)
        client.connect()
        
        client.subscribe(config.TOPIC_S1_ACTION, qos=1)
        client.subscribe(config.TOPIC_S2_ACTION, qos=1)
        client.subscribe(config.TOPIC_QUERY, qos=1) # รองรับการ Query จากระบบ
        
        client.publish(config.TOPIC_AVAIL, "ONLINE", retain=True, qos=1)
        
        # 6.4 จัดการการส่งสถานะเมื่อมีการเปลี่ยนแปลง (Flag check)
        if needs_to_send_status and mqtt_connected:
          send_all_status(client) # ฟังก์ชันนี้จะเปลี่ยน needs_to_send_status = False ให้เอง
        
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
    except: pass

    try:
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

# ฟังก์ชันส่งข้อมูล DHT ไปยังเว็บ
def send_dht_data(mqtt_client):
    try:
      # ส่งแบบ JSON เพื่อให้หน้าเว็บนำไปใช้ง่าย
      msg = '{{"t": "{}", "h": "{}"}}'.format(sensor.temperature(), sensor.humidity())
      mqtt_client.publish(config.TOPIC_SENSOR_DHT, msg)
      print("Sent DHT:", msg)
    except:
      print("DHT Publish failed")


def run_ota():
    tft.fill_rect(0, 0, 320, 240, C_BLACK)
    tft.draw_text(60, 100, "CHECKING UPDATE...", C_WHITE, 2)
    
    try:
        OTA = senko.Senko(
          user=config.OTA_USER, 
          repo=config.OTA_REPO,
          working_dir=config.OTA_DIR, 
          files=config.OTA_FILES
        )
        
        if OTA.update():
          tft.fill_rect(0, 0, 320, 240, COLOR_BTN_ON) # จอเขียวแจ้งว่าสำเร็จ
          tft.draw_text(40, 110, "UPDATED! REBOOTING...", C_WHITE, 2)
          utime.sleep(2)
          machine.reset() # Restart เครื่องทันที
        else:
          tft.draw_text(60, 140, "ALREADY UP TO DATE", C_YELLOW, 2)
          utime.sleep(2)
          
        # ก่อนออกจากฟังก์ชัน ให้วาดทุกอย่างใหม่ ---
        tft.fill_rect(0, 0, 320, 240, C_BLACK)
        draw_btn(btn1)
        draw_btn(btn2)
        # รีเซ็ตตัวแปรหน้าจอเพื่อให้ update_info() วาดค่าใหม่ทันที
        global old_t, old_h, old_time
        old_t, old_h, old_time = "", "", ""
            
    except Exception as e:
        tft.fill_rect(0, 0, 320, 240, COLOR_BTN_OFF) # จอแดงแจ้งว่าพลาด
        tft.draw_text(20, 110, "OTA FAILED!", C_WHITE, 2)
        print("OTA Error:", e)
        utime.sleep(2)
    
    # วาดหน้าจอหลักกลับมาถ้าไม่มีการอัปเดต
    tft.fill_rect(0, 0, 320, 240, C_BLACK)
    draw_btn(btn1); draw_btn(btn2)
    
    
# --- 4. Startup Sequence ---
tft.fill_rect(0, 0, 320, 240, C_BLACK)
tft.draw_text(20, 80, "CONNECTING WIFI...", C_WHITE, 2)

if wifi_manager.connect_wifi(config.WIFI_CONFIGS):
    tft.draw_text(20, 110, "WIFI: OK", COLOR_BTN_ON, 2)
    try: ntptime.settime()
    except: pass
    
    if try_mqtt_connect():
        tft.draw_text(20, 140, "MQTT: OK", COLOR_BTN_ON, 2)
    else:
        tft.draw_text(20, 140, "MQTT: OFFLINE", C_YELLOW, 2)
else:
    tft.draw_text(20, 110, "WIFI: FAILED", COLOR_BTN_OFF, 2)

utime.sleep(1)
tft.fill_rect(0, 0, 320, 240, C_BLACK)
draw_btn(btn1); draw_btn(btn2)


# --- 6. Main Loop ---
last_tick = 0
last_press = 0
last_dht_send = 0

# สำหรับ OTA
ota_touch_start_time = 0
ota_is_pressing = False

while True:
    now = utime.ticks_ms()
    
    # 6.1 MQTT Sync & Reconnect
    if mqtt_connected:
        try:
            client.check_msg()
        except:
            mqtt_connected = False
    else:
        if utime.ticks_diff(now, last_mqtt_reconnect) > 30000:
            if try_mqtt_connect():
                print("MQTT Reconnected and Status Synced")
            last_mqtt_reconnect = now

    # 6.2 >>> เพิ่มตรงนี้ครับ! (หัวใจสำคัญของ Flag) <<<
    if needs_to_send_status and mqtt_connected:
        send_all_status(client) # ส่งเสร็จฟังก์ชันนี้จะแก้ Flag เป็น False ให้เอง
        
    # 6.3 Touch Control
    pos = tft.get_touch()
    if pos:
      tx, ty = pos
      
      # ก. จัดการการกดปุ่มปกติ
      if utime.ticks_diff(now, last_press) > 300:
        for btn in [btn1, btn2]:
          if btn["x"] <= tx <= btn["x"]+btn["w"] and btn["y"] <= ty <= btn["y"]+btn["h"]:
            btn["state"] = not btn["state"]
            btn["relay"].value(0 if btn["state"] else 1)
            draw_btn(btn)
            
            # ส่งสถานะเมื่อมีการกดปุ่ม
            if mqtt_connected:
              try:
                client.publish(btn["topic"], "ON" if btn["state"] else "OFF", retain=True, qos=1)
              except:
                mqtt_connected = False
                    
            # แทนที่จะ publish ตรงนี้ ให้ตั้ง Flag แทน
            needs_to_send_status = True
            last_press = now
            
      # ข. จัดการ OTA (ค้าง 10 วินาที)
      if not ota_is_pressing:
          ota_touch_start_time = now
          ota_is_pressing = True
      else:
        duration = utime.ticks_diff(now, ota_touch_start_time)
        if duration > 10000:
          ota_is_pressing = False 
          run_ota()
        elif duration > 1000:
          # แสดงวินาทีที่เหลือ (คำนวณถอยหลัง)
          sec = 10 - (duration // 1000)
          # ล้างพื้นที่เฉพาะจุดที่จะเขียนตัวเลข (ล้างก่อนเขียนทุกครั้ง)
          tft.fill_rect(80, 210, 220, 30, C_BLACK) 
          tft.draw_text(100, 210, "OTA IN {} SEC".format(sec), C_YELLOW, 2)
    else:
      # ถ้านิ้วปล่อย ให้เคลียร์ Countdown
      if ota_is_pressing:
        tft.fill_rect(80, 210, 220, 30, C_BLACK)
        ota_is_pressing = False

    # 6.4 อัปเดตข้อมูลบนจอ (ทุก 1 วินาที)
    if utime.ticks_diff(now, last_tick) > 1000:
      update_info() # อัปเดตนาฬิกาและตัวเลขบนจอ
      
      # ส่งค่าไปที่เว็บทุก 10 วินาที
      if utime.ticks_diff(now, last_dht_send) > 10000:
        if mqtt_connected:
          send_dht_data(client)
          last_dht_send = now
            
      last_tick = now
        
    utime.sleep_ms(100)
