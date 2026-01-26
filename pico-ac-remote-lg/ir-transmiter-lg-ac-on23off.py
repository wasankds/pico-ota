import machine
import utime

# --- Hardware ---
ir_led = machine.PWM(machine.Pin(15))
ir_led.freq(38000) # ความถี่มาตรฐาน
ir_led.duty_u16(0)

btn_on  = machine.Pin(14, machine.Pin.IN, machine.Pin.PULL_UP)
btn_off = machine.Pin(13, machine.Pin.IN, machine.Pin.PULL_UP)
led = machine.Pin("LED", machine.Pin.OUT)

# --- ข้อมูลดิบ (Raw Data) ของคุณ ---
# เราจะใช้ข้อมูลนี้แค่เพื่อดู Pattern (0 หรือ 1) เท่านั้น
# ตัวเลขเวลาในนี้จะไม่ถูกส่งไปตรงๆ (ตัดปัญหาเรื่องเลขเพี้ยน)

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

def send_lg_clean(raw_data):
    led.on()
    print("Sending Perfect LG Signal...")
    
    # ยิง 2 รอบ ตามมาตรฐาน
    for _ in range(2):
        
        # 1. ส่ง Header มาตรฐาน (9000, 4500)
        # ไม่สนว่า Raw Data จะเป็นเท่าไหร่ เราบังคับส่งค่านี้เลย
        ir_led.duty_u16(21845) # 33% duty
        utime.sleep_us(9000)
        ir_led.duty_u16(0)
        utime.sleep_us(4500)
        
        # 2. แปลง Raw Data เป็น Perfect Data
        # วนลูปทีละคู่ (Mark, Space)
        for i in range(0, len(raw_data)-1, 2):
            # --- จังหวะ Mark (ไฟติด) ---
            # บังคับส่ง 560 เสมอ
            ir_led.duty_u16(21845)
            utime.sleep_us(560)
            
            # --- จังหวะ Space (ไฟดับ) ---
            ir_led.duty_u16(0)
            
            # เช็คว่า Space ใน Raw Data มันยาวแค่ไหน?
            original_space = raw_data[i+1]
            
            if original_space > 1000:
                # ถ้าของเดิมยาวเกิน 1000 แปลว่าเป็น "เลข 1"
                # ให้ส่งค่ามาตรฐาน 1690 (แทนที่จะส่ง 1528)
                utime.sleep_us(1690)
            else:
                # ถ้าของเดิมสั้น (400-600) แปลว่าเป็น "เลข 0"
                # ให้ส่งค่ามาตรฐาน 560 (แทนที่จะส่ง 485 ที่สั้นไป)
                utime.sleep_us(560)
        
        # 3. ปิดท้าย (Stop Bit)
        ir_led.duty_u16(21845)
        utime.sleep_us(560)
        ir_led.duty_u16(0)
        
        # พักก่อนยิงซ้ำ
        utime.sleep_ms(40)
        
    led.off()
    print("Done.")

# --- Loop ---
for _ in range(3): led.on(); utime.sleep(0.1); led.off(); utime.sleep(0.1)
print("READY: Perfect Mode")

while True:
    if btn_on.value() == 0:
        utime.sleep(0.05)
        if btn_on.value() == 0:
            send_lg_clean(RAW_ON)
            while btn_on.value() == 0: utime.sleep(0.1)

    if btn_off.value() == 0:
        utime.sleep(0.05)
        if btn_off.value() == 0:
            send_lg_clean(RAW_OFF)
            while btn_off.value() == 0: utime.sleep(0.1)
            
    utime.sleep(0.05)
    
