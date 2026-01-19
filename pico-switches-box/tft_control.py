# tft_control.pyfrom machine import Pin, SPI
import framebuf
import utime

# --- Configuration & Calibration ---
X_MIN, X_MAX = 340, 3820
Y_MIN, Y_MAX = 710, 3300

# Colors
C_BLACK  = 0x0000
C_WHITE  = 0xFFFF
C_YELLOW = 0xFFE0
COLOR_BTN_ON  = 0x07E0 # เขียว 
COLOR_BTN_OFF = 0x001F # แดง (รหัสน้ำเงิน)
COLOR_TEMP    = 0xFC00
COLOR_HUMID   = 0x07FF # ฟ้าสว่าง - จริงเหลือง

class TFTDisplay:
    def __init__(self, spi, lcd_cs, dc, rst, touch_cs):
        self.spi = spi
        self.lcd_cs = lcd_cs
        self.dc = dc
        self.rst = rst
        self.touch_cs = touch_cs
        self.init_display()

    def write_cmd(self, cmd, data=None):
        self.spi.init(baudrate=10000000, polarity=0, phase=0)
        self.dc.value(0); self.lcd_cs.value(0)
        self.spi.write(bytearray([cmd])); self.lcd_cs.value(1)
        if data:
            self.dc.value(1); self.lcd_cs.value(0)
            self.spi.write(bytearray(data)); self.lcd_cs.value(1)

    def init_display(self):
        self.rst.value(0); utime.sleep_ms(200); self.rst.value(1); utime.sleep_ms(200)
        for cmd, data in [(0x01, None), (0x11, None), (0x36, [0x68]), (0x3A, [0x55]), (0x29, None)]:
            self.write_cmd(cmd, data); utime.sleep_ms(150)

    def fill_rect(self, x, y, w, h, color):
        self.write_cmd(0x2A, [x >> 8, x & 0xFF, (x+w-1) >> 8, (x+w-1) & 0xFF])
        self.write_cmd(0x2B, [y >> 8, y & 0xFF, (y+h-1) >> 8, (y+h-1) & 0xFF])
        self.write_cmd(0x2C); self.dc.value(1); self.lcd_cs.value(0)
        row = bytearray([color >> 8, color & 0xFF] * w)
        for _ in range(h): self.spi.write(row)
        self.lcd_cs.value(1)

    def draw_text(self, x, y, text, color, size=2):
        f_w, f_h = 8, 8
        fb_w, fb_h = len(text) * f_w, f_h
        buf = bytearray(fb_w * fb_h * 2)
        fb = framebuf.FrameBuffer(buf, fb_w, fb_h, framebuf.RGB565)
        fb.text(text, 0, 0, ((color & 0xFF) << 8) | (color >> 8))
        self.write_cmd(0x2A, [x >> 8, x & 0xFF, (x + fb_w*size - 1) >> 8, (x + fb_w*size - 1) & 0xFF])
        self.write_cmd(0x2B, [y >> 8, y & 0xFF, (y + fb_h*size - 1) >> 8, (y + fb_h*size - 1) & 0xFF])
        self.write_cmd(0x2C); self.dc.value(1); self.lcd_cs.value(0)
        for row in range(f_h):
            line = bytearray()
            for col in range(fb_w):
                p = buf[(row * fb_w + col) * 2 : (row * fb_w + col) * 2 + 2]
                for _ in range(size): line.extend(p)
            for _ in range(size): self.spi.write(line)
        self.lcd_cs.value(1)

    def get_touch(self):
        self.spi.init(baudrate=1000000, polarity=0, phase=0)
        self.touch_cs.value(0)
        self.spi.write(bytearray([0xD0])); rx_raw = ((self.spi.read(2)[0]<<8)|self.spi.read(2)[1])>>3
        self.spi.write(bytearray([0x90])); ry_raw = ((self.spi.read(2)[0]<<8)|self.spi.read(2)[1])>>3
        self.touch_cs.value(1)
        if rx_raw < 100 or ry_raw < 100: return None
        sx = int((rx_raw - X_MIN) * 320 / (X_MAX - X_MIN))
        sy = 239 - int((ry_raw - Y_MIN) * 240 / (Y_MAX - Y_MIN))
        return max(0, min(319, sx)), max(0, min(239, sy))
