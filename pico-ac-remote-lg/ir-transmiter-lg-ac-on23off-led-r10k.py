import machine
import utime
import dht

# --- 1. Hardware Setup ---
ir_led = machine.PWM(machine.Pin(15))
ir_led.freq(38000) 
ir_led.duty_u16(0)

# เซนเซอร์ DHT11 ต่อที่ขา 16
sensor = dht.DHT11(machine.Pin(16))

# ปุ่มกด (ใช้งานได้ครบทุกขาแล้ว)
btn_on    = machine.Pin(14, machine.Pin.IN)
btn_off   = machine.Pin(13, machine.Pin.IN)
btn_light = machine.Pin(12, machine.Pin.IN)

led = machine.Pin("LED", machine.Pin.OUT)
last_dht_read = 0

# --- 2. ข้อมูลดิบ (Raw Data) ---
RAW_ON = [563, 1528, 549, 491, 550, 485, 550, 494, 549, 1528, 549, 485, 550, 497, 550, 491, 537, 498, 549, 485, 548, 486, 549, 497, 550, 485, 549, 485, 550, 486, 549, 499, 550, 1527, 549, 498, 548, 499, 550, 486, 549, 485, 549, 498, 536, 499, 550, 485, 549, 1541, 536, 500, 549, 499, 548, 511, 549]
RAW_OFF = [589, 1516, 562, 490, 550, 498, 549, 480, 551, 1528, 548, 486, 561, 485, 549, 480, 561, 1515, 561, 1528, 561, 487, 562, 473, 562, 486, 548, 499, 549, 485, 549, 486, 549, 486, 562, 486, 549, 485, 548, 486, 549, 485, 563, 1529, 561, 487, 562, 1528, 562, 485, 550, 487, 548, 486, 549, 1529, 561]
RAW_LIGHT = [600, 1490, 576, 476, 562, 485, 562, 481, 549, 1528, 549, 485, 549, 486, 561, 480, 550, 1528, 549, 1540, 549, 473, 573, 473, 575, 486, 548, 485, 562, 485, 548, 485, 574, 473, 561, 484, 549, 486, 549, 485, 563, 1514, 561, 485, 548, 1528, 549, 472, 574, 485, 548, 1527, 563, 1527, 549, 485, 563]

# --- 3. ฟังก์ชันส่งสัญญาณ IR (ยิง 1 รอบ) ---
def send_ir(raw_data, name):
    led.on()
    print(f"[IR] Sending {name} (1 shot)...")
    ir_led.duty_u16(21845); utime.sleep_us(9000); ir_led.duty_u16(0); utime.sleep_us(4500)
    for i in range(0, len(raw_data)-1, 2):
        ir_led.duty_u16(21845); utime.sleep_us(560); ir_led.duty_u16(0)
        utime.sleep_us(1690 if raw_data[i+1] > 1000 else 560)
    ir_led.duty_u16(21845); utime.sleep_us(560); ir_led.duty_u16(0)
    led.off()
    print(f"[IR] {name} Sent.")

# --- 4. ฟังก์ชันตรวจสอบปุ่ม (Debounce) ---
def is_pressed(pin):
    if pin.value() == 0:
        utime.sleep_ms(80) # ยืนยันว่ากดจริง 80ms
        if pin.value() == 0:
            return True
    return False

# --- Main Loop ---
print("\n" + "="*35)
print("  SYSTEM READY: HARDWARE FIXED")
print("  Monitoring: ON, OFF, LIGHT, DHT11")
print("="*35 + "\n")

for _ in range(3): led.on(); utime.sleep(0.1); led.off(); utime.sleep(0.1)

while True:
    now = utime.ticks_ms()
    
    # 1. อ่านค่า DHT11 ทุกๆ 3 วินาที
    if utime.ticks_diff(now, last_dht_read) > 3000:
        try:
            sensor.measure()
            print(f"[SENSOR] Temp: {sensor.temperature()}C | Hum: {sensor.humidity()}%")
        except:
            print("[SENSOR] DHT Error - Still some noise?")
        last_dht_read = now
        utime.sleep_ms(100) # พักเล็กน้อยหลังอ่าน

    # 2. เช็กปุ่ม ON
    if is_pressed(btn_on):
        print("[BUTTON] ON Pressed")
        send_ir(RAW_ON, "POWER ON")
        while btn_on.value() == 0: utime.sleep_ms(50)

    # 3. เช็กปุ่ม OFF (กลับมาใช้งานได้แล้ว!)
    if is_pressed(btn_off):
        print("[BUTTON] OFF Pressed")
        send_ir(RAW_OFF, "POWER OFF")
        while btn_off.value() == 0: utime.sleep_ms(50)
            
    # 4. เช็กปุ่ม LIGHT
    if is_pressed(btn_light):
        print("[BUTTON] LIGHT Pressed")
        send_ir(RAW_LIGHT, "LIGHT")
        while btn_light.value() == 0: utime.sleep_ms(50)

    utime.sleep_ms(20)
