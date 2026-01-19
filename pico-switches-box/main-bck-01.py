from machine import Pin, SPI
import utime
import framebuf
import dht
import network
import ntptime

# --- 1. Settings ---
WIFI_SSID = "WK_AIS_2.4G"
WIFI_PASS = "0813996766"

# --- 2. Hardware Setup ---
relay1 = Pin(14, Pin.OUT, value=1)
relay2 = Pin(15, Pin.OUT, value=1)
sensor = dht.DHT11(Pin(22))

miso = Pin(16, Pin.IN, Pin.PULL_UP)
spi = SPI(0, baudrate=10000000, polarity=0, phase=0, sck=Pin(18), mosi=Pin(19), miso=miso)
lcd_cs, dc, rst, touch_cs = Pin(17, Pin.OUT, value=1), Pin(20, Pin.OUT, value=0), Pin(21, Pin.OUT, value=1), Pin(2, Pin.OUT, value=1)

X_MIN, X_MAX = 340, 3820   
Y_MIN, Y_MAX = 710, 3300   

# --- [ ส่วนแยกสีอิสระ ] ---
C_BLACK  = 0x0000
C_WHITE  = 0xFFFF
C_YELLOW = 0xFFE0

# ปรับสีตามอาการจอ (ส่งน้ำเงินได้แดง)
COLOR_BTN_ON  = 0x07E0 # เขียว
COLOR_BTN_OFF = 0x001F # แดง (รหัสน้ำเงิน)
COLOR_TEMP    = 0xF800 # ลองใช้รหัสแดงตรงๆ ถ้ายังเป็นน้ำเงินให้เปลี่ยนเป็น 0x001F
COLOR_HUMID   = 0x07FF # ฟ้าสว่าง
# -----------------------

def write_cmd(cmd, data=None):
    spi.init(baudrate=10000000, polarity=0, phase=0) 
    dc.value(0); lcd_cs.value(0); spi.write(bytearray([cmd])); lcd_cs.value(1)
    if data: dc.value(1); lcd_cs.value(0); spi.write(bytearray(data)); lcd_cs.value(1)

def fill_rect(x, y, w, h, color):
    write_cmd(0x2A, [x >> 8, x & 0xFF, (x+w-1) >> 8, (x+w-1) & 0xFF])
    write_cmd(0x2B, [y >> 8, y & 0xFF, (y+h-1) >> 8, (y+h-1) & 0xFF])
    write_cmd(0x2C); dc.value(1); lcd_cs.value(0)
    row = bytearray([color >> 8, color & 0xFF] * w)
    for _ in range(h): spi.write(row)
    lcd_cs.value(1)

def draw_text(x, y, text, color, size=2):
    f_w, f_h = 8, 8
    fb_w, fb_h = len(text) * f_w, f_h
    buf = bytearray(fb_w * fb_h * 2)
    fb = framebuf.FrameBuffer(buf, fb_w, fb_h, framebuf.RGB565)
    fb.text(text, 0, 0, ((color & 0xFF) << 8) | (color >> 8))
    write_cmd(0x2A, [x >> 8, x & 0xFF, (x + fb_w*size - 1) >> 8, (x + fb_w*size - 1) & 0xFF])
    write_cmd(0x2B, [y >> 8, y & 0xFF, (y + fb_h*size - 1) >> 8, (y + fb_h*size - 1) & 0xFF])
    write_cmd(0x2C); dc.value(1); lcd_cs.value(0)
    for row in range(f_h):
        line = bytearray()
        for col in range(fb_w):
            p = buf[(row * fb_w + col) * 2 : (row * fb_w + col) * 2 + 2]
            for _ in range(size): line.extend(p)
        for _ in range(size): spi.write(line)
    lcd_cs.value(1)

def get_touch():
    spi.init(baudrate=1000000, polarity=0, phase=0)
    touch_cs.value(0)
    spi.write(bytearray([0xD0])); rx_raw = ((spi.read(2)[0]<<8)|spi.read(2)[1])>>3
    spi.write(bytearray([0x90])); ry_raw = ((spi.read(2)[0]<<8)|spi.read(2)[1])>>3
    touch_cs.value(1)
    if rx_raw < 100 or ry_raw < 100: return None
    sx = int((rx_raw - X_MIN) * 320 / (X_MAX - X_MIN))
    sy = 239 - int((ry_raw - Y_MIN) * 240 / (Y_MAX - Y_MIN))
    return max(0, min(319, sx)), max(0, min(239, sy))

def connect_wifi_and_sync():
    fill_rect(0, 0, 320, 240, C_BLACK)
    draw_text(20, 80, "SYSTEM STARTING...", C_WHITE, 2)
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(WIFI_SSID, WIFI_PASS)
    draw_text(20, 110, "WIFI: CONNECTING", COLOR_HUMID, 2)
    retry = 0
    while not wlan.isconnected() and retry < 15:
        draw_text(160 + (retry*8), 110, ".", COLOR_HUMID, 2)
        utime.sleep(0.5); retry += 1
    if wlan.isconnected():
        draw_text(20, 140, "TIME: SYNCING...", C_YELLOW, 2)
        try:
            ntptime.settime()
            draw_text(20, 170, "STATUS: READY!", COLOR_BTN_ON, 2)
        except:
            draw_text(20, 170, "TIME ERROR", COLOR_BTN_OFF, 2)
    else:
        draw_text(20, 140, "WIFI: FAILED", COLOR_BTN_OFF, 2)
    utime.sleep(1)
    fill_rect(0, 0, 320, 240, C_BLACK)

old_t, old_h, old_time = "", "", ""

def update_info():
    global old_t, old_h, old_time
    t_now = utime.localtime(utime.time() + 7 * 3600)
    time_str = "{:02d}:{:02d}:{:02d}".format(t_now[3], t_now[4], t_now[5])
    if time_str != old_time:
        if old_time != "": draw_text(80, 10, old_time, C_BLACK, 3)
        draw_text(80, 10, time_str, C_WHITE, 3); old_time = time_str
    try:
        sensor.measure()
        new_t, new_h = "T:{}C".format(sensor.temperature()), "H:{}%".format(sensor.humidity())
        if new_t != old_t:
            if old_t != "": draw_text(30, 50, old_t, C_BLACK, 2)
            draw_text(30, 50, new_t, COLOR_TEMP, 2); old_t = new_t
        if new_h != old_h:
            if old_h != "": draw_text(180, 50, old_h, C_BLACK, 2)
            draw_text(180, 50, new_h, COLOR_HUMID, 2); old_h = new_h
    except: pass

btn1 = {"x": 20, "y": 95, "w": 120, "h": 110, "state": False, "label": "#1"}
btn2 = {"x": 180, "y": 95, "w": 120, "h": 110, "state": False, "label": "#2"}

def draw_btn(btn):
    color = COLOR_BTN_ON if btn["state"] else COLOR_BTN_OFF
    fill_rect(btn["x"], btn["y"], btn["w"], btn["h"], color)
    draw_text(btn["x"] + 40, btn["y"] + 30, btn["label"], C_WHITE, 3)
    draw_text(btn["x"] + 30, btn["y"] + 70, "ON" if btn["state"] else "OFF", C_WHITE, 3)

def init_display():
    rst.value(0); utime.sleep_ms(200); rst.value(1); utime.sleep_ms(200)
    for cmd, data in [(0x01, None), (0x11, None), (0x36, [0x68]), (0x3A, [0x55]), (0x29, None)]:
        write_cmd(cmd, data); utime.sleep_ms(150)

init_display()
connect_wifi_and_sync()
draw_btn(btn1); draw_btn(btn2)

last_tick, last_press = 0, 0
while True:
    now = utime.ticks_ms()
    pos = get_touch()
    if pos:
        tx, ty = pos
        if utime.ticks_diff(now, last_press) > 300:
            if btn1["x"] <= tx <= btn1["x"]+btn1["w"] and btn1["y"] <= ty <= btn1["y"]+btn1["h"]:
                btn1["state"] = not btn1["state"]; draw_btn(btn1)
                relay1.value(0 if btn1["state"] else 1); last_press = now
            elif btn2["x"] <= tx <= btn2["x"]+btn2["w"] and btn2["y"] <= ty <= btn2["y"]+btn2["h"]:
                btn2["state"] = not btn2["state"]; draw_btn(btn2)
                relay2.value(0 if btn2["state"] else 1); last_press = now
    if utime.ticks_diff(now, last_tick) > 1000:
        update_info(); last_tick = now
    utime.sleep_ms(10)
