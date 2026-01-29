import machine
import utime
import dht
import config
import wifi_manager
import gc
from umqtt.simple import MQTTClient

# --- Hardware Setup ---
LED = machine.Pin("LED", machine.Pin.OUT)
IR_LED = machine.PWM(machine.Pin(15))
IR_LED.freq(38000) 
IR_LED.duty_u16(0)

# ปุ่มกด (ใช้ Pin.IN เพราะต่อ Pull-up 10k ภายนอกแล้ว)
BTN_ON    = machine.Pin(14, machine.Pin.IN)
BTN_OFF   = machine.Pin(13, machine.Pin.IN)
BTN_LIGHT = machine.Pin(12, machine.Pin.IN)

# เซนเซอร์ DHT11 ต่อที่ขา 16
SENSOR = dht.DHT11(machine.Pin(16))

# --- ข้อมูลดิบจาก config.py ---
RAW_ON = config.RAW_ON
RAW_OFF = config.RAW_OFF
RAW_LIGHT = config.RAW_LIGHT

# --- MQTT Variables ---
client = None
mqtt_connected = False
last_mqtt_reconnect = 0
last_dht_send = 0

# --- 1. ฟังก์ชันส่งสัญญาณ IR (ยิง 1 รอบ) ---
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

# --- 2. ฟังก์ชัน MQTT Callback ---
def on_message(topic, msg):
    t = topic.decode()
    m = msg.decode().upper()
    print(f"\n[MQTT] Incoming CMD: {t} -> {m}")
    
    if t == config.TOPIC_AC_ON:
        send_ir(RAW_ON, "POWER ON")
    elif t == config.TOPIC_AC_OFF:
        send_ir(RAW_OFF, "POWER OFF")
    elif t == config.TOPIC_AC_LED:
        send_ir(RAW_LIGHT, "LIGHT")
    elif t == config.TOPIC_QUERY:
        send_dht_data()

# --- 3. ฟังก์ชันเชื่อมต่อ MQTT ---
def try_mqtt_connect():
    global client, mqtt_connected
    try:
        print("Connecting to MQTT Broker...")
        client = MQTTClient(config.CLIENT_ID, config.MQTT_BROKER, keepalive=60)
        client.set_callback(on_message)
        client.set_last_will(config.TOPIC_AVAIL, "OFFLINE", retain=True, qos=1)
        client.connect()
        
        # Subscribe หัวข้อต่างๆ
        client.subscribe(config.TOPIC_AC_ON)
        client.subscribe(config.TOPIC_AC_OFF)
        client.subscribe(config.TOPIC_AC_LED)
        client.subscribe(config.TOPIC_QUERY)
        
        client.publish(config.TOPIC_AVAIL, "ONLINE", retain=True, qos=1)
        mqtt_connected = True
        print("MQTT Connected")
        return True
    except Exception as e:
        print(f"MQTT Error: {e}")
        mqtt_connected = False
        return False

# --- 4. ฟังก์ชันอ่านและส่งค่า DHT (ทำเมื่อถึงเวลาส่งเท่านั้น) ---
def send_dht_data():
    try:
        SENSOR.measure()
        t = SENSOR.temperature()
        h = SENSOR.humidity()
        msg = '{{"t": "{}", "h": "{}"}}'.format(t, h)
        client.publish(config.TOPIC_SENSOR_DHT, msg)
        print(f"[MQTT] DHT Data Sent: {t}C, {h}%")
        gc.collect() # เคลียร์แรมหลังส่ง
    except Exception as e:
        print(f"[ERROR] DHT Measure/Send Failed: {e}")

# --- 5. ฟังก์ชันตรวจสอบปุ่มกด ---
def is_pressed(pin):
    if pin.value() == 0:
        utime.sleep_ms(80) # ยืนยันว่ากดจริง 80ms
        if pin.value() == 0:
            return True
    return False

# --- Start Up ---
for _ in range(3): LED.on(); utime.sleep(0.1); LED.off(); utime.sleep(0.1)
print("\nSystem Starting...")

if wifi_manager.connect_wifi(config.WIFI_CONFIGS):
    try_mqtt_connect()

# --- Main Loop ---
while True:
    now = utime.ticks_ms()
    
    # 1. จัดการ MQTT
    if mqtt_connected:
        try:
            client.check_msg()
        except:
            mqtt_connected = False
    elif utime.ticks_diff(now, last_mqtt_reconnect) > 15000:
        try_mqtt_connect()
        last_mqtt_reconnect = now

    # 2. ส่งข้อมูล DHT ไป MQTT ทุก 10 วินาที (อ่านเฉพาะตอนนี้)
    if mqtt_connected and utime.ticks_diff(now, last_dht_send) > 10000:
        send_dht_data()
        last_dht_send = now

    # 3. ตรวจสอบปุ่มกดหน้าเครื่อง
    if is_pressed(BTN_ON):
        print("[BUTTON] ON Clicked")
        send_ir(RAW_ON, "POWER ON")
        while BTN_ON.value() == 0: utime.sleep_ms(50)

    if is_pressed(BTN_OFF):
        print("[BUTTON] OFF Clicked")
        send_ir(RAW_OFF, "POWER OFF")
        while BTN_OFF.value() == 0: utime.sleep_ms(50)
            
    if is_pressed(BTN_LIGHT):
        print("[BUTTON] LIGHT Clicked")
        send_ir(RAW_LIGHT, "LIGHT")
        while BTN_LIGHT.value() == 0: utime.sleep_ms(50)

    utime.sleep_ms(20)
