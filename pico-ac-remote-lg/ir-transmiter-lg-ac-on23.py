import machine
import utime

# --- ตั้งค่า Hardware ---
# หลอด IR ต่อขา 15
ir_led = machine.PWM(machine.Pin(15))
ir_led.freq(38000) # ความถี่มาตรฐานแอร์ LG
ir_led.duty_u16(0)

# ปุ่มกด ต่อขา 14 (แบบ Pull-up)
button = machine.Pin(14, machine.Pin.IN, machine.Pin.PULL_UP)

# ไฟบนบอร์ด
led_onboard = machine.Pin("LED", machine.Pin.OUT)

# --- ข้อมูลรีโมท (ผ่าตัดใส่ Gap 4500 ให้แล้ว) ---
# นี่คือข้อมูลที่คุณจับมาได้ + การแก้ไข Header
CMD_OPEN_23 = [
  9000, 4500, # << นี่คือส่วนที่ผมเติมให้ (Header Mark, Header Space)
  563, 1528, 538, 515, 536, 498, 537, 497, 536, 1540, 
  535, 515, 536, 511, 536, 502, 539, 498, 537, 511, 
  538, 498, 536, 510, 536, 498, 537, 499, 536, 498, 
  549, 510, 537, 1553, 538, 511, 536, 510, 536, 1540, 
  536, 511, 536, 497, 536, 498, 549, 498, 536, 1539, 
  549, 498, 548, 498, 549, 1542, 560
]

def send_ir(data):
    led_onboard.on()
    print("Sending IR Signal...")
    
    # เทคนิค: ส่งสัญญาณซ้ำ 1 รอบ (แอร์บางรุ่นรับไม่ทันในชุดแรก)
    # แต่ต้องเว้นระยะห่างให้พอดี
    
    # --- รอบที่ 1 ---
    for i, duration in enumerate(data):
        if i % 2 == 0:
            ir_led.duty_u16(32768) # Mark (เปิดแสง 50%)
        else:
            ir_led.duty_u16(0)     # Space (ปิดแสง)
        utime.sleep_us(duration)
    ir_led.duty_u16(0) # ปิดแสงจบชุด
    
    # --- พักหายใจ 28 มิลลิวินาที (มาตรฐาน LG ซ้ำคำสั่ง) ---
    utime.sleep_ms(28)
    
    # --- รอบที่ 2 (ส่งซ้ำเพื่อความชัวร์) ---
    for i, duration in enumerate(data):
        if i % 2 == 0:
            ir_led.duty_u16(32768)
        else:
            ir_led.duty_u16(0)
        utime.sleep_us(duration)
    ir_led.duty_u16(0)
    
    led_onboard.off()
    print("Done.")

# --- เริ่มต้น ---
# กระพริบไฟบอกว่าพร้อม
for _ in range(3):
    led_onboard.on(); utime.sleep(0.1)
    led_onboard.off(); utime.sleep(0.1)

print("READY: Press button to send 'OPEN 23C'")

while True:
    # กดปุ่ม (ค่าเป็น 0)
    if button.value() == 0:
        utime.sleep(0.05) # กันเบิ้ล
        if button.value() == 0:
            
            send_ir(CMD_OPEN_23)
            
            # รอจนกว่าจะปล่อยปุ่ม
            while button.value() == 0:
                utime.sleep(0.1)
        utime.sleep(0.1)
