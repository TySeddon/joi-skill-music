from amcrest import AmcrestCamera
import socket
from contextlib import closing
from camera.finder import CameraFinder
from enviro import get_setting

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

CAMERA_NAME = get_setting('camera_name')
CAMERA_PASSWORD = get_setting('camera_password')
MY_IP_ADDRESS = socket.gethostbyname(socket.gethostname())
# scan ip range for a given camera name
finder = CameraFinder(CAMERA_NAME, 'admin', CAMERA_PASSWORD)
found_devices = finder.scan_devices(f"{MY_IP_ADDRESS}/24")
print(found_devices)
