# โค้ดสำหรับก๊อปปี้สัญญาณ (Receiver) - แบบละเอียด
import machine
import utime

# ขา DATA ของตัวรับ IR (เปลี่ยนเลขขาตามที่คุณต่อจริง)
ir_pin = machine.Pin(16, machine.Pin.IN, machine.Pin.PULL_UP)

print("--- รอรับสัญญาณรีโมท (Raw Capture) ---")
print("กดรีโมท 1 ครั้ง...")

# ตัวแปรเก็บข้อมูล
data = []

while True:
    # รอจนกว่าขาจะเป็น 0 (Active Low คือมีสัญญาณเริ่มมา)
    if ir_pin.value() == 0:
        # จับเวลาเริ่มต้น
        start_time = utime.ticks_us()
        
        # วนลูปเก็บข้อมูลจนกว่าจะเงียบไปนานเกิน 20ms (จบคำสั่ง)
        while True:
            # รอเปลี่ยนสถานะ (จาก 0->1 หรือ 1->0)
            current_val = ir_pin.value()
            while ir_pin.value() == current_val:
                # ถ้าค้างสถานะเดิมนานเกิน 20000us (20ms) แสดงว่าจบสัญญาณ
                if utime.ticks_diff(utime.ticks_us(), start_time) > 200000: # Timeout ยาวๆ
                    break
            
            # คำนวณระยะเวลา pulse นี้
            now = utime.ticks_us()
            diff = utime.ticks_diff(now, start_time)
            start_time = now
            
            # ถ้า pulse ยาวเกิน 20ms แปลว่าจบแล้ว ให้ break ออก
            if diff > 20000:
                break
                
            data.append(diff)
        
        # เมื่อหลุดลูป (จบสัญญาณ) ให้แสดงผล
        if len(data) > 10:
            print("\n✅ จับสัญญาณได้!")
            print(f"จำนวน Pulse: {len(data)}")
            print("ก๊อปปี้ตัวเลขในวงเล็บข้างล่างนี้มาครับ:")
            print(data)
            print("-" * 30)
            data = [] # ล้างค่ารอรอบต่อไป
            print("รอรับสัญญาณครั้งถัดไป...")
        else:
            data = [] # สัญญาณขยะ ล้างทิ้ง