# Python
from picamera2 import Picamera2
import time
# 1. เริ่มต้นใช้งานกล้อง
picam2 = Picamera2()
# 2. ตั้งค่า (เหมือนที่คุณต้องการคือ 640x480 เพื่อให้เบา)
config = picam2.create_video_configuration(main={"format": "YUV420", "size": (640, 480)})
picam2.configure(config)
picam2.start()

# 3. ลองถ่ายภาพนิ่ง
picam2.capture_file("test_v3.jpg")

print("บันทึกภาพสำเร็จ! ตรวจสอบไฟล์ test_v3.jpg ได้เลย")
picam2.stop()
