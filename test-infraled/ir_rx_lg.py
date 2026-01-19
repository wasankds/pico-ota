# ir_rx_lg.py (Save ไฟล์ชื่อนี้ไว้ในโฟลเดอร์ lib บน Pico)
import machine
import utime

class IR_RX:
    def __init__(self, pin):
        self.pin = pin
        self.pin.irq(handler=self.callback, trigger=machine.Pin.IRQ_FALLING | machine.Pin.IRQ_RISING)
        self.last_tick = utime.ticks_us()
        self.pulses = []

    def callback(self, pin):
        current_tick = utime.ticks_us()
        duration = utime.ticks_diff(current_tick, self.last_tick)
        self.last_tick = current_tick
        if duration > 10000: # สิ้นสุดชุดข้อมูล
            if len(self.pulses) > 50: # ถ้ามีข้อมูลมากพอ (แอร์)
                print("Captured pulses:", len(self.pulses))
                self.decode_lg(self.pulses)
            self.pulses = []
        else:
            self.pulses.append(duration)

    def decode_lg(self, pulses):
        # แอร์ LG มักจะส่งสัญญาณแบบยาว ให้พิมพ์ออกมาดูความต่าง
        print("Raw Pulses Data:", pulses)

# --- ส่วนของการเรียกใช้งาน ---
pin_ir = machine.Pin(15, machine.Pin.IN) # สมมติว่าต่อขา 15
receiver = IR_RX(pin_ir)

print("พร้อมรับสัญญาณจากรีโมท LG แล้ว...")
while True:
    utime.sleep(1)