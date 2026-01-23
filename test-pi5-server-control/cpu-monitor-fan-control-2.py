from luma.core.interface.serial import i2c
from luma.core.render import canvas
from luma.oled.device import ssd1306
from gpiozero import PWMOutputDevice
import time
import subprocess
import os
import psutil

# 1. ตั้งค่าจอ OLED
serial = i2c(port=1, address=0x3C)
device = ssd1306(serial, width=128, height=64)

# 2. ตั้งค่าพัดลม (GPIO 17)
fan = PWMOutputDevice(17, active_high=True, frequency=100)

# --- ฟังก์ชันดึงข้อมูล ---


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


last_idle = [0] * 4
last_total = [0] * 4


def get_cores_load():
    global last_idle, last_total
    current_loads = []
    try:
        with open('/proc/stat', 'r') as f:
            lines = f.readlines()[1:5]
        for i, line in enumerate(lines):
            fields = [float(column) for column in line.strip().split()[1:]]
            idle, total = fields[3], sum(fields)
            diff_idle, diff_total = idle - last_idle[i], total - last_total[i]
            usage = 100 * (1 - (diff_idle / diff_total)
                           ) if diff_total != 0 else 0
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

# --- ระบบคุมพัดลมอัจฉริยะ ---


temp_history = []


def control_fan(temp):
    global temp_history
    temp_history.append(temp)
    if len(temp_history) > 5:
        temp_history.pop(0)
    avg_temp = sum(temp_history) / len(temp_history)

    if avg_temp < 45:
        speed = 0.4
    elif avg_temp < 65:
        speed = 0.4 + (0.6 * (avg_temp - 45) / (65 - 45))
    else:
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
        c = get_cores_load()
        r = get_ram_usage()
        u = get_uptime()

        with canvas(device) as draw:
            # x_pos ขยับมาที่ 10 เพื่อหลบขอบจอตามที่คุยกันครับ
            x_pos = 10

            # บรรทัดที่ 1: Temp & Fan
            draw.text(
                (x_pos, 0),  f"Temp:{current_temp}C F:{fan_speed}%", fill="white")

            # บรรทัดที่ 2: Download
            draw.text((x_pos, 11), f"Down: {rx_speed:.1f} K/s", fill="white")

            # บรรทัดที่ 3: Upload
            draw.text((x_pos, 22), f"Up:   {tx_speed:.1f} K/s", fill="white")

            # บรรทัดที่ 4: CPU Cores (โชว์แค่ตัวเลข % 4 ตัว)
            draw.text((x_pos, 33), f"{c}", fill="white")

            # บรรทัดที่ 5: RAM
            draw.text((x_pos, 44), f"RAM:  {r}", fill="white")

            # บรรทัดที่ 6: Uptime
            draw.text((x_pos, 54), f"Up:   {u}", fill="white")

        time.sleep(1)

except KeyboardInterrupt:
    fan.off()
    device.clear()
