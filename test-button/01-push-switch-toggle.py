import machine
import time
from machine import Pin

led = Pin("LED", Pin.OUT)
button = Pin(15, Pin.IN, Pin.PULL_UP)

# ตัวแปรเก็บสถานะ "ก่อนหน้านี้" (Default ของ Pull-up คือ 1)
last_button_state = 1 

print("System Ready: กด 1 ครั้งเพื่อเปิดค้าง, กดอีกครั้งเพื่อปิด")

while True:
    current_state = button.value() # อ่านค่าปุ่มตอนนี้

    # ตรวจสอบ: "สถานะเปลี่ยน" และ "ตอนนี้เป็น 0 (ถูกกด)"
    if current_state != last_button_state and current_state == 0:
        
        # --- จังหวะสลับไฟ (Toggle) ---
        new_value = not led.value() # ถ้า 1 กลายเป็น 0, ถ้า 0 กลายเป็น 1
        led.value(new_value)
        
        print("LED is now:", "ON" if new_value else "OFF")
        
        # รอให้นิ้วเราปล่อย หรือให้สัญญาณนิ่ง (Debounce)
        time.sleep(0.2) 

    # อัปเดตสถานะล่าสุดไว้เปรียบเทียบในรอบถัดไป
    last_button_state = current_state
    
    # หน่วงเวลาสั้นๆ เพื่อให้ Loop ทำงานนิ่งๆ
    time.sleep(0.1)