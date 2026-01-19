import network
import time
import machine

def connect_wifi(configs):
    """
    รับค่า configs เป็น list ของ tuple เช่น [('SSID', 'PWD'), ...]
    """
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    
    for ssid, pwd in configs:
        print(f'\nConnecting to {ssid}...')
        wlan.connect(ssid, pwd)

        # รอเชื่อมต่อ 10 วินาทีต่อหนึ่งจุด
        for _ in range(10):
            if wlan.isconnected():
                print(f'Connected! IP: {wlan.ifconfig()[0]}')
                return True
            time.sleep(1)
            print('.', end='')
        print(f'\nFailed to connect to {ssid}')
        
    return False