from amcrest import AmcrestCamera
import socket
from contextlib import closing
from camera.finder import CameraFinder

PASSWORD = 'Smarthome#1'

# manual test of single ip
__RTSP_PORT = 554
__PWGPSI_PORT = 3800
__HTTP_PORT = 80
ipaddr = "192.168.1.31"
with closing(socket.socket()) as sock:
    sock.connect((ipaddr, __RTSP_PORT))
with closing(socket.socket()) as sock:
    sock.connect((ipaddr, __HTTP_PORT))
# with closing(socket.socket()) as sock:
#     sock.connect((ipaddr, __PWGPSI_PORT))


# scan ip range for a given camera name
finder = CameraFinder('AMC05740_FF21EB', 'admin', PASSWORD)
found_devices = finder.scan_devices("192.168.1.0/24")
print(found_devices)
