from amcrest import AmcrestCamera
import socket
from contextlib import closing
from camera.finder import CameraFinder
from enviro import get_setting
from ifaddr import get_adapters

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



def get_ip_addresses():
    result = []
    for iface in get_adapters():
        for addr in iface.ips:
            if addr.is_IPv4:
                result.append(addr.ip)
    return result  

ip_addresses = [o for o in get_ip_addresses() if not o.startswith("169") and not o.startswith("127")]
print(ip_addresses)


CAMERA_NAME = get_setting('camera_name')
CAMERA_USERNAME = get_setting('camera_username')
CAMERA_PASSWORD = get_setting('camera_password')
MY_IP_ADDRESS = socket.gethostbyname(socket.gethostname())
# scan ip range for a given camera name
finder = CameraFinder(CAMERA_NAME, CAMERA_USERNAME, CAMERA_PASSWORD)
found_devices = finder.scan_devices(f"{MY_IP_ADDRESS}/24")
print(found_devices)
