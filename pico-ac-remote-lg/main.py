import machine
from machine import Pin, PWM
import utime
import dht
import config
import wifi_manager
import gc
from umqtt.simple import MQTTClient

# --- 0. System Info ---
SYSNAME1 = "Eagle Eye Legion"
SYSNAME2 = "AC Remote"
SYSVER  = "1.0.0"

# --- 1. Hardware Setup ---
LED = Pin("LED", Pin.OUT)
IR_LED = PWM(Pin(15))
IR_LED.freq(38000) 
IR_LED.duty_u16(0)

# ปุ่มกด (Pull-up 10k ภายนอก)
BTN_ON    = Pin(14, Pin.IN)
BTN_OFF   = Pin(13, Pin.IN)
BTN_LIGHT = Pin(12, Pin.IN)
SENSOR    = dht.DHT11(Pin(16))

# --- 2. System Variables ---
CLIENT = None
MQTT_CONNECTED = False
LAST_MQTT_RECONNECT = 0
LAST_DHT_SEND = 0

# --- 3. Functions ---
def send_ir(raw_data, name):
  LED.on()
  print(f"[IR] Sending {name}...")
  IR_LED.duty_u16(21845); utime.sleep_us(9000); IR_LED.duty_u16(0); utime.sleep_us(4500)
  for i in range(0, len(raw_data)-1, 2):
      IR_LED.duty_u16(21845); utime.sleep_us(560); IR_LED.duty_u16(0)
      utime.sleep_us(1690 if raw_data[i+1] > 1000 else 560)
  IR_LED.duty_u16(21845); utime.sleep_us(560); IR_LED.duty_u16(0)
  LED.off()
  print(f"[IR] {name} Sent.")

def trigger_ota():
  global CLIENT, MQTT_CONNECTED
  print("\n[OTA] Preparing for Update...")
  try:
    if CLIENT:
      CLIENT.publish(config.TOPIC_AVAIL, "UPDATING", retain=True)
      utime.sleep_ms(500)
      CLIENT.disconnect()
  except: pass
  
  CLIENT = None
  MQTT_CONNECTED = False
  gc.collect() 
  utime.sleep(1)

  try:
    import senko
    gc.collect()
    OTA = senko.Senko(user=config.OTA_USER, repo=config.OTA_REPO, working_dir=config.OTA_DIR, files=config.OTA_FILES)
    if OTA.update():
      print("[OTA] Update Success! Rebooting...")
      utime.sleep(2)
      machine.reset()
    else:
      print("[OTA] No New Version.")
      utime.sleep(1)
      machine.reset()
  except Exception as e:
    print(f"[OTA] Failed: {e}")
    utime.sleep(2)
    machine.reset()

def send_dht_data():
    for i in range(3): 
        try:
            utime.sleep_ms(200)
            SENSOR.measure()
            t, h = SENSOR.temperature(), SENSOR.humidity()
            msg = '{{"t": "{}", "h": "{}"}}'.format(t, h)
            CLIENT.publish(config.TOPIC_SENSOR_DHT, msg)
            
            print(f"[DATA] Sent DHT: {t}C / {h}% (Try {i+1})")
            gc.collect()
            return 
        except Exception as e:
            print(f"[DATA] DHT Try {i+1} Failed: {e}")
            utime.sleep_ms(500)
    print("[DATA] DHT Final Error: Give up after 3 tries")

 

def on_message(topic, msg):
    t = topic.decode()
    m = msg.decode().upper()
    print(f"\n[MQTT] Incoming: {t} -> {m}")
    # [MQTT] Incoming: pico-003/system/query -> GET_STATUS
    
    if t.endswith(config.TOPIC_UPDATE) and m == "UPDATE":
        trigger_ota()
        return

    if t == config.TOPIC_AC_ON: send_ir(config.RAW_ON, "POWER ON")
    elif t == config.TOPIC_AC_OFF: send_ir(config.RAW_OFF, "POWER OFF")
    elif t == config.TOPIC_AC_LED: send_ir(config.RAW_LIGHT, "LIGHT")
    elif t == config.TOPIC_QUERY: 
        print("[QUERY] Status Requested")

        # 1. ส่งสถานะยืนยันว่าเครื่องยังออนไลน์อยู่
        try:
          CLIENT.publish(config.TOPIC_AVAIL, "ONLINE", retain=True, qos=1)
        except: 
          pass
            
        # 2. ส่งค่าอุณหภูมิและความชื้นจาก DHT
        send_dht_data()

def try_mqtt_connect():
    global CLIENT, MQTT_CONNECTED
    try:
        CLIENT = MQTTClient(config.CLIENT_ID, config.MQTT_BROKER, keepalive=60)
        CLIENT.set_callback(on_message)
        CLIENT.set_last_will(config.TOPIC_AVAIL, "OFFLINE", retain=True, qos=1)
        CLIENT.connect()
        
        CLIENT.subscribe(config.TOPIC_AC_ON, qos=1)
        CLIENT.subscribe(config.TOPIC_AC_OFF, qos=1)
        CLIENT.subscribe(config.TOPIC_AC_LED, qos=1)
        CLIENT.subscribe(config.TOPIC_QUERY)
        CLIENT.subscribe(config.TOPIC_UPDATE, qos=1)
        
        CLIENT.publish(config.TOPIC_AVAIL, "ONLINE", retain=True, qos=1)
        MQTT_CONNECTED = True
        print("MQTT Status: Connected")
        return True
    except Exception as e:
        print(f"MQTT Failed: {e}")
        MQTT_CONNECTED = False
        return False

def is_pressed(pin):
    if pin.value() == 0:
        utime.sleep_ms(80) 
        return pin.value() == 0
    return False

# --- Start Up ---
print(f"\n{SYSNAME1} v{SYSVER} (WDT Disabled)")
for _ in range(3): LED.on(); utime.sleep(0.05); LED.off(); utime.sleep(0.05)
# เริ่มต่อ WiFi
print("Connecting to WiFi...")
LED.on() # เปิดไฟค้างไว้ระหว่างรอเชื่อมต่อ

if wifi_manager.connect_wifi(config.WIFI_CONFIGS):
    LED.off()
    utime.sleep(0.2)
    # ต่อ WiFi สำเร็จ: กะพริบ 2 ครั้งสั้นๆ
    for _ in range(2): LED.on(); utime.sleep(0.1); LED.off(); utime.sleep(0.1)
    
    # 3. เริ่มต่อ MQTT
    print("Connecting to MQTT...")
    LED.on() # เปิดไฟค้างไว้ระหว่างรอ MQTT
    if try_mqtt_connect():
        LED.off()
        utime.sleep(0.2)
        # ต่อสำเร็จทุกอย่าง: ไฟติดค้างยาว 1.5 วินาที แล้วดับ
        LED.on(); utime.sleep(1.5); LED.off()
        print("SYSTEM READY: All systems go!")
    else:
        # กรณี MQTT ล้มเหลว: กะพริบแบบ Strobe (รัวๆ) เพื่อแจ้งเตือน
        for _ in range(10): LED.on(); utime.sleep(0.05); LED.off(); utime.sleep(0.05)
else:
    # กรณี WiFi ล้มเหลว: ไฟกะพริบช้าๆ 3 ครั้ง
    LED.off()
    for _ in range(3): LED.on(); utime.sleep(0.5); LED.off(); utime.sleep(0.5)

# --- Main Loop ---
while True:
    now = utime.ticks_ms()
    
    # # กะพริบแวบเดียว (10ms) ทุกๆ 5 วินาที ให้รู้ว่าระบบยังรันอยู่
    # if now % 5000 < 20: 
    #   LED.on(); utime.sleep_ms(10); LED.off()
    
    if MQTT_CONNECTED:
      try:
        CLIENT.check_msg()
      except:
        MQTT_CONNECTED = False
    elif utime.ticks_diff(now, LAST_MQTT_RECONNECT) > 15000:
        try_mqtt_connect()
        LAST_MQTT_RECONNECT = now

    if MQTT_CONNECTED and utime.ticks_diff(now, LAST_DHT_SEND) > 10000:
        send_dht_data()
        LAST_DHT_SEND = now

    if is_pressed(BTN_ON):
        send_ir(config.RAW_ON, "ON")
        while BTN_ON.value() == 0: utime.sleep_ms(20)

    if is_pressed(BTN_OFF):
        send_ir(config.RAW_OFF, "OFF")
        while BTN_OFF.value() == 0: utime.sleep_ms(20)
            
    if is_pressed(BTN_LIGHT):
        send_ir(config.RAW_LIGHT, "LIGHT")
        while BTN_LIGHT.value() == 0: utime.sleep_ms(20)

    utime.sleep_ms(20)
