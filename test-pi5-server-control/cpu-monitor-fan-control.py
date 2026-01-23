from luma.core.interface.serial import i2c
from luma.core.render import canvas
from luma.oled.device import ssd1306
from gpiozero import PWMOutputDevice
import time
import subprocess
import os

# 1. ตั้งค่าจอ OLED
serial = i2c(port=1, address=0x3C)
device = ssd1306(serial, width=128, height=64)

# 2. ตั้งค่าพัดลม (GPIO 17)
# frequency=100 คือความถี่สัญญาณ PWM (ปรับได้ตามรุ่นพัดลม)
fan = PWMOutputDevice(17, active_high=True, frequency=100)


def get_cpu_temp_float():
    """ดึงอุณหภูมิเป็นตัวเลข float เพื่อใช้คำนวณพัดลม"""
    try:
        temp = os.popen('vcgencmd measure_temp').readline()
        return float(temp.replace("temp=", "").replace("'C\n", ""))
    except:
        return 40.0


def get_cpu_clock():
    cmd = "vcgencmd measure_clock arm | awk -F'=' '{printf \"%.0f MHz\", $2/1000000}'"
    return subprocess.check_output(cmd, shell=True).decode("utf-8").strip()


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

# ฟังก์ชันคำนวณความเร็วพัดลม (Smart Fan)


# เพิ่มตัวแปรเก็บประวัติอุณหภูมิไว้บนสุดของไฟล์ (นอก loop)
# นำค่าอุณหภูมิ 5 ครั้งล่าสุดมาหาค่าเฉลี่ย เพื่อไม่ให้พัดลมตกใจเวลา CPU ดีดตัวขึ้นชั่วคราว(Spike)
# บังคับให้มันขยับทีละ 5% หรือ 10% เท่านั้น พัดลมจะนิ่งขึ้นมาก
temp_history = []


def control_fan(temp):
    global temp_history

    # 1. เก็บค่าอุณหภูมิลงใน List (เก็บไว้ 5 ค่าล่าสุด)
    temp_history.append(temp)
    if len(temp_history) > 5:
        temp_history.pop(0)

    # 2. หาค่าเฉลี่ยอุณหภูมิ เพื่อความนิ่ง
    avg_temp = sum(temp_history) / len(temp_history)

    # 3. คำนวณความเร็วตามช่วง
    if avg_temp < 45:
        speed = 0.4
    elif avg_temp < 65:
        speed = 0.4 + (0.6 * (avg_temp - 45) / (65 - 45))
        # เช่น 55C = 0.4 + 0.6*(10/20) = 0.7 (70%)
    else:
        speed = 1.0

    # 4. ปัดเศษให้ขยับทีละ 5% (0.05) เพื่อไม่ให้ความถี่เสียงเปลี่ยนบ่อยเกินไป
    stable_speed = round(speed * 20) / 20

    fan.value = stable_speed
    return int(stable_speed * 100)


try:
    get_cores_load()
    time.sleep(0.5)

    while True:
        # อ่านค่าอุณหภูมิ
        current_temp = get_cpu_temp_float()

        # ควบคุมพัดลมและรับค่า % ความเร็วมาโชว์บนจอ
        fan_speed = control_fan(current_temp)

        # อ่านค่าอื่นๆ
        f = get_cpu_clock()  # 1500 MHz - คงที่
        c = get_cores_load()
        r = get_ram_usage()
        u = get_uptime()

        with canvas(device) as draw:
            # บรรทัดที่ 1: อุณหภูมิ + % พัดลม
            draw.text(
                (5, 2),  f"Temp: {current_temp}C  Fan:{fan_speed}%", fill="white")
            # บรรทัดที่ 2: ความเร็วคล็อก คือ
            draw.text((5, 14), f"Clock: {f}", fill="white")
            # บรรทัดที่ 3: CPU 4 Cores
            draw.text((5, 26), f"{c}", fill="white")
            # บรรทัดที่ 4: RAM
            draw.text((5, 38), f"RAM Used:  {r}", fill="white")
            # บรรทัดที่ 5: Uptime
            draw.text((5, 50), f"Up: {u}", fill="white")

        time.sleep(1)

except KeyboardInterrupt:
    fan.off()  # ปิดพัดลมเมื่อเลิกใช้
    device.clear()
