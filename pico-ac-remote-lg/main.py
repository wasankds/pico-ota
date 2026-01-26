import machine
import utime

# --- Hardware ---
ir_led = machine.PWM(machine.Pin(15))
ir_led.freq(38000) 
ir_led.duty_u16(0)

# ปุ่มกด
btn_on    = machine.Pin(14, machine.Pin.IN, machine.Pin.PULL_UP)
btn_off   = machine.Pin(13, machine.Pin.IN, machine.Pin.PULL_UP)
btn_light = machine.Pin(12, machine.Pin.IN, machine.Pin.PULL_UP)

led = machine.Pin("LED", machine.Pin.OUT)

# --- ข้อมูลดิบ (Raw Data) ---
RAW_ON = [
    563, 1528, 549, 491, 550, 485, 550, 494, 549, 1528, 
    549, 485, 550, 497, 550, 491, 537, 498, 549, 485, 
    548, 486, 549, 497, 550, 485, 549, 485, 550, 486, 
    549, 499, 550, 1527, 549, 498, 548, 499, 550, 486, 
    549, 485, 549, 498, 536, 499, 550, 485, 549, 1541, 
    536, 500, 549, 499, 548, 511, 549
]

RAW_OFF = [
    589, 1516, 562, 490, 550, 498, 549, 480, 551, 1528, 
    548, 486, 561, 485, 549, 480, 561, 1515, 561, 1528, 
    561, 487, 562, 473, 562, 486, 548, 499, 549, 485, 
    549, 486, 549, 486, 562, 486, 549, 485, 548, 486, 
    549, 485, 563, 1529, 561, 487, 562, 1528, 562, 485, 
    550, 487, 548, 486, 549, 1529, 561
]

RAW_LIGHT = [
    600, 1490, 576, 476, 562, 485, 562, 481, 549, 1528, 
    549, 485, 549, 486, 561, 480, 550, 1528, 549, 1540, 
    549, 473, 573, 473, 575, 486, 548, 485, 562, 485, 
    548, 485, 574, 473, 561, 484, 549, 486, 549, 485, 
    563, 1514, 561, 485, 548, 1528, 549, 472, 574, 485, 
    548, 1527, 563, 1527, 549, 485, 563
]

# เพิ่มตัวแปร repeats เพื่อกำหนดจำนวนรอบ
def send_lg_clean(raw_data, repeats=2):
    if not raw_data: return
    
    led.on()
    print(f"Sending IR ({repeats} shots)...")
    
    # วนลูปตามจำนวนรอบที่กำหนด
    for _ in range(repeats):
        # 1. Header
        ir_led.duty_u16(21845) 
        utime.sleep_us(9000)
        ir_led.duty_u16(0)
        utime.sleep_us(4500)
        
        # 2. Data
        for i in range(0, len(raw_data)-1, 2):
            ir_led.duty_u16(21845)
            utime.sleep_us(560) 
            
            ir_led.duty_u16(0)
            if raw_data[i+1] > 1000:
                utime.sleep_us(1690)
            else:
                utime.sleep_us(560)
        
        # 3. Stop Bit
        ir_led.duty_u16(21845)
        utime.sleep_us(560)
        ir_led.duty_u16(0)
        
        utime.sleep_ms(40)
        
    led.off()
    print("Sent.")

# --- Loop ---
for _ in range(3): led.on(); utime.sleep(0.1); led.off(); utime.sleep(0.1)
print("READY: 3 Buttons Fixed")

while True:
    # ON -> ยิง 2 รอบ (ชัวร์ไว้ก่อน)
    if btn_on.value() == 0:
        utime.sleep(0.05)
        if btn_on.value() == 0:
            print(">> ON")
            send_lg_clean(RAW_ON, repeats=2)
            while btn_on.value() == 0: utime.sleep(0.1)

    # OFF -> ยิง 2 รอบ (ชัวร์ไว้ก่อน)
    if btn_off.value() == 0:
        utime.sleep(0.05)
        if btn_off.value() == 0:
            print(">> OFF")
            send_lg_clean(RAW_OFF, repeats=2)
            while btn_off.value() == 0: utime.sleep(0.1)
            
    # LIGHT -> ยิง 1 รอบพอ! (ห้ามเบิ้ล เดี๋ยวสลับคืน)
    if btn_light.value() == 0:
        utime.sleep(0.05)
        if btn_light.value() == 0:
            print(">> LIGHT")
            send_lg_clean(RAW_LIGHT, repeats=1) # << จุดสำคัญแก้ตรงนี้
            while btn_light.value() == 0: utime.sleep(0.1)
            
    utime.sleep(0.05)
