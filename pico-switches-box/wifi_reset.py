import network
import utime
wlan = network.WLAN(network.STA_IF)
wlan.active(False)
utime.sleep(1)
wlan.active(True)
print("Wi-Fi Reset Done")
