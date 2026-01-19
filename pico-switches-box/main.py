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

# ลด Baudrate ลงเล็กน้อยเหลือ 9MHz เพื่อความเสถียรของสัญญาณ SPI ในสายไฟ
spi = SPI(0, baudrate=9000000, polarity=0, phase=0, sck=Pin(18), mosi=Pin(19), miso=Pin(16, Pin.IN, Pin.PULL_UP))
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
    except: pass

def on_message(topic, msg):
    global needs_to_send_status
    t, m = topic.decode(), msg.decode().upper()
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
        for tp in [config.TOPIC_S1_ACTION, config.TOPIC_S2_ACTION, config.TOPIC_QUERY]:
            client.subscribe(tp, qos=1)
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

def run_ota():
    global old_t, old_h, old_time
    print("Starting OTA process...")
    # 1. ล้างสถานะวาดเดิม
    old_t, old_h, old_time = "", "", "" 
    # 2. ปิดกั้น SPI สักครู่เพื่อให้ Hardware เคลียร์สถานะ Touch
    utime.sleep_ms(300) 
    
    try:
        tft.fill_rect(0, 0, 320, 240, C_BLACK)
        tft.draw_text(60, 110, "CHECKING UPDATE...", C_WHITE, 2)
        utime.sleep_ms(500) # ให้เวลาจอวาดข้อความให้เสร็จก่อนเริ่มใช้เน็ตหนักๆ

        OTA = senko.Senko(user=config.OTA_USER, repo=config.OTA_REPO, working_dir=config.OTA_DIR, files=config.OTA_FILES)
        if OTA.update():
            tft.fill_rect(0, 0, 320, 240, COLOR_BTN_ON)
            tft.draw_text(40, 110, "UPDATED! REBOOTING...", C_WHITE, 2)
            utime.sleep(2)
            machine.reset()
        else:
            tft.fill_rect(0, 100, 320, 60, C_BLACK)
            tft.draw_text(60, 110, "ALREADY UP TO DATE", C_YELLOW, 2)
            utime.sleep(2)
    except Exception as e:
        tft.fill_rect(0, 0, 320, 240, COLOR_BTN_OFF)
        tft.draw_text(20, 110, "OTA ERROR!", C_WHITE, 2)
        print("OTA Error:", e)
        utime.sleep(2)
    
    # วาดหน้าหลักกลับมา
    tft.fill_rect(0, 0, 320, 240, C_BLACK)
    draw_btn(btn1); draw_btn(btn2)

# --- 4. Startup Sequence ---
tft.fill_rect(0, 0, 320, 240, C_BLACK)
tft.draw_text(20, 80, "CONNECTING WIFI...", C_WHITE, 2)

# ใช้ Wi-Fi Network ที่คุณบันทึกไว้ (WK_AIS_2.4G)
if wifi_manager.connect_wifi(config.WIFI_CONFIGS):
    tft.draw_text(20, 110, "WIFI: OK", COLOR_BTN_ON, 2)
    try: ntptime.settime()
    except: pass
    try_mqtt_connect()
else:
    tft.draw_text(20, 110, "WIFI: FAILED", COLOR_BTN_OFF, 2)

utime.sleep(1)
tft.fill_rect(0, 0, 320, 240, C_BLACK)
draw_btn(btn1); draw_btn(btn2)

# --- 5. Main Loop ---
last_tick, last_press, last_dht_send = 0, 0, 0
ota_touch_start_time = 0
ota_is_pressing = False



while True:
    now = utime.ticks_ms()
    
    # 5.1 MQTT Sync
    if mqtt_connected:
        try: client.check_msg()
        except: mqtt_connected = False
    elif utime.ticks_diff(now, last_mqtt_reconnect) > 20000:
        try_mqtt_connect()
        last_mqtt_reconnect = now

    if needs_to_send_status and mqtt_connected:
        send_all_status(client)

    # 5.2 Touch & OTA Logic
    # อ่านค่า Touch เฉพาะเมื่อไม่ได้อยู่ในโหมด OTA นับถอยหลัง เพื่อลด SPI Conflict
    pos = tft.get_touch() if not ota_is_pressing else None
    
    if pos:
        tx, ty = pos
        if utime.ticks_diff(now, last_press) > 300:
            hit = False
            for btn in [btn1, btn2]:
                if btn["x"] <= tx <= btn["x"]+btn["w"] and btn["y"] <= ty <= btn["y"]+btn["h"]:
                    btn["state"] = not btn["state"]
                    btn["relay"].value(0 if btn["state"] else 1)
                    draw_btn(btn)
                    needs_to_send_status, last_press, hit = True, now, True
            
            if not hit: # เริ่มกดค้างที่พื้นที่ว่างเพื่อ OTA
                ota_touch_start_time, ota_is_pressing = now, True

    # แยกส่วนจัดการ OTA ออกมา (เช็คว่ายังกดค้างอยู่หรือไม่)
    if ota_is_pressing:
        duration = utime.ticks_diff(now, ota_touch_start_time)
        # ตรวจสอบแรงกด (ห้ามอ่านพิกัด tx,ty เพราะจะทำให้ SPI รวนจังหวะวาดเลข)
        if tft.get_touch(): 
            if duration > 10000:
                ota_is_pressing = False
                run_ota()
            elif duration > 1000:
                sec = 10 - (duration // 1000)
                if 'last_sec' not in locals() or last_sec != sec:
                    tft.fill_rect(80, 210, 220, 30, C_BLACK)
                    tft.draw_text(100, 210, "OTA IN {} SEC".format(sec), C_YELLOW, 2)
                    last_sec = sec
        else:
            # ปล่อยมือ เคลียร์ข้อความ
            tft.fill_rect(80, 210, 220, 30, C_BLACK)
            ota_is_pressing = False

    # 5.3 อัปเดตข้อมูลบนจอ (ทำเฉพาะตอน "ไม่กดจอ" และ "ไม่รอ OTA")
    if not pos and not ota_is_pressing:
        if utime.ticks_diff(now, last_tick) > 1000:
            update_info()
            if utime.ticks_diff(now, last_dht_send) > 10000 and mqtt_connected:
                send_dht_data(client)
                last_dht_send = now
            last_tick = now
            
    utime.sleep_ms(50) # เพิ่มความไวในการตอบสนองเล็กน้อย