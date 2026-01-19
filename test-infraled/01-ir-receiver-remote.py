import machine
import utime

# ตั้งค่าขาพิน (ตรวจสอบว่าต่อ GP15 จริงไหม ถ้าไม่ใช่ให้แก้เลขครับ)
ir_pin = machine.Pin(16, machine.Pin.IN, machine.Pin.PULL_UP)

# ตัวแปรเก็บค่า
timestamps = []

def callback(pin):
    # บันทึกเวลาที่เกิดการเปลี่ยนแปลงของสัญญาณ (หน่วยเป็น microsecond)
    timestamps.append(utime.ticks_us())

# ตั้งค่าให้ทำงานทันทีที่สัญญาณเปลี่ยน (ทั้งขาขึ้นและขาลง)
ir_pin.irq(handler=callback, trigger=machine.Pin.IRQ_FALLING | machine.Pin.IRQ_RISING)

print("--- เครื่องดักฟังรหัสแอร์ LG พร้อมทำงาน ---")
print("กรุณากดรีโมทจ่อหน้าเซนเซอร์ 1 ครั้ง")

while True:
    if len(timestamps) > 0:
        # รอจนกว่าสัญญาณจะนิ่ง (ไม่มีการกดซ้ำประมาณ 0.5 วินาที)
        start_count = len(timestamps)
        utime.sleep(0.5)
        if len(timestamps) == start_count:
            # คำนวณช่วงเวลาห่างของแต่ละ Pulse (Durations)
            durations = []
            for i in range(1, len(timestamps)):
                durations.append(utime.ticks_diff(timestamps[i], timestamps[i-1]))
            
            print("\nพบสัญญาณ!")
            print(f"จำนวน Pulse ที่ได้รับ: {len(durations)}")
            print("ชุดตัวเลข (Raw Durations):")
            print(durations)
            print("-" * 50)
            
            # ล้างค่าเพื่อรอรับครั้งต่อไป
            timestamps = []
            print("พร้อมรับสัญญาณครั้งถัดไป...")
            
            
            
""" 

**** LG_ON_25_AUTO

พบสัญญาณ!
จำนวน Pulse ที่ได้รับ: 59
ชุดตัวเลข (Raw Durations):
[3359, 9835, 578, 1533, 557, 484, 556, 482, 558, 480, 556, 1536, 555, 491, 557, 490, 558, 494, 556, 483, 555, 482, 555, 484, 555, 489, 556, 483, 555, 483, 555, 484, 576, 469, 555, 486, 552, 483, 554, 1522, 554, 1529, 555, 491, 554, 1522, 554, 484, 554, 484, 554, 492, 555, 1536, 554, 1538, 554, 1522, 553]


**** LG_OFF
พบสัญญาณ!
จำนวน Pulse ที่ได้รับ: 59
ชุดตัวเลข (Raw Durations):
[3180, 9827, 586, 1508, 567, 479, 558, 487, 563, 490, 559, 1518, 558, 482, 556, 480, 559, 479, 557, 1518, 558, 1518, 557, 481, 557, 481, 557, 481, 557, 481, 557, 481, 557, 481, 558, 481, 556, 481, 556, 482, 556, 482, 556, 482, 555, 1521, 556, 488, 557, 1528, 555, 483, 555, 483, 555, 483, 555, 1521, 555]


"""