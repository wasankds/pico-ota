""" 

การใช้งาน python3 cpu-monitor-fan-control-2.py 1

"""

from luma.core.interface.serial import i2c
from luma.core.render import canvas
from luma.oled.device import ssd1306
from gpiozero import PWMOutputDevice
import time
import subprocess
import os
import psutil
import sys  # เพิ่ม sys เพื่อรับค่าอาร์กิวเมนต์

# --- ส่วนรับค่าจาก Command Line ---
# ตั้งค่าเริ่มต้น (Default) ไว้ที่ 1 วินาที
refresh_interval = 1.0

if len(sys.argv) > 1:
    try:
        # รับค่าจากอาร์กิวเมนต์แรก เช่น python3 file.py 2
        refresh_interval = float(sys.argv[1])
        print(f"Starting monitor with {refresh_interval}s interval")
    except ValueError:
        print("Invalid interval number, using default 1.0s")

# 1. ตั้งค่าจอ OLED
serial = i2c(port=1, address=0x3C)
device = ssd1306(serial, width=128, height=64)

# 2. ตั้งค่าพัดลม (GPIO 17)
fan = PWMOutputDevice(17, active_high=True, frequency=100)

# --- ฟังก์ชันดึงข้อมูล (เหมือนเดิม) ---


def get_cpu_temp_float():
    try:
        temp = os.popen('vcgencmd measure_temp').readline()
        return float(temp.replace("temp=", "").replace("'C\n", ""))
    except:
        return 40.0


last_net_io = psutil.net_io_counters()


def get_network_usage():
    global last_net_io
    curr_net_io = psutil.net_io_counters()
    rx = (curr_net_io.bytes_recv - last_net_io.bytes_recv) / 1024
    tx = (curr_net_io.bytes_sent - last_net_io.bytes_sent) / 1024
    last_net_io = curr_net_io
    return rx, tx


last_idle, last_total = [0]*4, [0]*4


def get_cores_load():
    global last_idle, last_total
    current_loads = []
    try:
        with open('/proc/stat', 'r') as f:
            lines = f.readlines()[1:5]
        for i, line in enumerate(lines):
            fields = [float(column) for column in line.strip().split()[1:]]
            idle, total = fields[3], sum(fields)
            diff_i, diff_t = idle - last_idle[i], total - last_total[i]
            usage = 100 * (1 - (diff_i / diff_t)) if diff_t != 0 else 0
            last_idle[i], last_total[i] = idle, total
            current_loads.append(f"{int(usage)}%")
        return "  ".join(current_loads)
    except:
        return "Err Err Err Err"


def get_ram_usage():
    cmd = "free -m | awk 'NR==2{printf \"%.1f%%\", $3*100/$2 }'"
    return subprocess.check_output(cmd, shell=True).decode("utf-8").strip()


def get_uptime():
    cmd = "uptime -p | sed 's/up //; s/ hours/h/; s/ minutes/m/; s/ hour/h/; s/ minute/m/'"
    return subprocess.check_output(cmd, shell=True).decode("utf-8").strip()


temp_history = []


def control_fan(temp):
    global temp_history
    temp_history.append(temp)
    if len(temp_history) > 5:
        temp_history.pop(0)
    avg_temp = sum(temp_history) / len(temp_history)
    speed = 0.4
    if avg_temp >= 45 and avg_temp < 65:
        speed = 0.4 + (0.6 * (avg_temp - 45) / (65 - 45))
    elif avg_temp >= 65:
        speed = 1.0
    stable_speed = round(speed * 20) / 20
    fan.value = stable_speed
    return int(stable_speed * 100)


# --- ส่วนการแสดงผล ---
try:
    get_cores_load()
    time.sleep(0.5)

    while True:
        current_temp = get_cpu_temp_float()
        fan_speed = control_fan(current_temp)
        rx_speed, tx_speed = get_network_usage()
        c, r, u = get_cores_load(), get_ram_usage(), get_uptime()

        with canvas(device) as draw:
            x_pos = 10
            draw.text(
                (x_pos, 0),  f"Temp:{current_temp}C F:{fan_speed}%", fill="white")
            draw.text(
                (x_pos, 11), f"Down: {rx_speed/refresh_interval:.1f} K/s", fill="white")
            draw.text(
                (x_pos, 22), f"Up:   {tx_speed/refresh_interval:.1f} K/s", fill="white")
            draw.text((x_pos, 33), f"{c}", fill="white")
            draw.text((x_pos, 44), f"RAM:  {r}", fill="white")
            draw.text((x_pos, 54), f"Up:   {u}", fill="white")

        # ใช้ค่าที่กรอกมาหน่วงเวลา
        time.sleep(refresh_interval)

except KeyboardInterrupt:
    fan.off()
    device.clear()
