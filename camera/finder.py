from amcrest import AmcrestCamera
import socket
from contextlib import closing
from typing import List, Optional
import threading
from ifaddr import get_adapters

class CameraFinder():

    __RTSP_PORT = 554
    __PWGPSI_PORT = 3800
    __HTTP_PORT = 80

    def __init__(self, camera_name, username, password, log) -> None:
        self.camera_name = camera_name
        self.username = username
        self.password = password
        self.log = log
        self.amcrest_ips: List[str] = []

    def get_ip_addresses(self):
        result = []
        for iface in get_adapters():
            for addr in iface.ips:
                if addr.is_IPv4:
                    result.append(addr.ip)
        return result  

    def get_my_subnet(self):
        ip_addresses = [o for o in self.get_ip_addresses() if not o.startswith("169") and not o.startswith("127")]
        self.log.info(ip_addresses)
        if not ip_addresses:
            self.log.error("Could not determine IP address")
            return None
        my_ip_address = ip_addresses[0]
        subnet = f"{my_ip_address}/24"
        return subnet

    def __raw_scan(self, ipaddr: str, timeout: Optional[float] = None) -> None:
        if timeout:
            socket.setdefaulttimeout(timeout)
        else:
            # If devices not found, try increasing timeout
            socket.setdefaulttimeout(1.0)

            try:
                with closing(socket.socket()) as sock:
                    sock.connect((ipaddr, self.__RTSP_PORT))
                #with closing(socket.socket()) as sock:
                    #sock.connect((ipaddr, self.__PWGPSI_PORT))
                with closing(socket.socket()) as sock:
                    sock.connect((ipaddr, self.__HTTP_PORT))
                self.log.info(f"Found possible camera at {ipaddr}")                    
                camera = AmcrestCamera(ipaddr, self.__HTTP_PORT, self.username, self.password).camera
                if camera:
                    self.log.info(f"Found '{camera.machine_name}' at {ipaddr}")
                    if camera.machine_name == self.camera_name:
                        self.amcrest_ips.append(ipaddr)

            # pylint: disable=bare-except
            except:
                pass

    def scan_devices(self, timeout: Optional[float] = None) -> List[str]:

        self.amcrest_ips: List[str] = []

        subnet = self.get_my_subnet()
        if not subnet:
            return None
        self.subnet = subnet            

        self.log.info(f"Searching for camera '{self.camera_name}' on subnet {subnet}")

        # Maximum range from mask
        # Format is mask: max_range
        max_range = {
            16: 256,
            24: 256,
            25: 128,
            27: 32,
            28: 16,
            29: 8,
            30: 4,
            31: 2,
        }

        # If user didn't provide mask, use /24
        if "/" not in subnet:
            mask = int(24)
            network = subnet
        else:
            network, mask_str = subnet.split("/")
            mask = int(mask_str)

        if mask not in max_range:
            raise RuntimeError("Cannot determine the subnet mask!")

        # Default logic is remove everything from last "." to the end
        # This logic change in case mask is 16
        network = network.rpartition(".")[0]

        if mask == 16:
            # For mask 16, we must cut the last two
            # entries with .

            # pylint: disable=unused-variable
            for i in range(0, 1):
                network = network.rpartition(".")[0]

        # Trigger the scan
        # For clear coding, let's keep the logic in if/else (mask16)
        # instead of only one if
        threads = []
        if mask == 16:
            for seq1 in range(max_range[mask]):
                for seq2 in range(max_range[mask]):
                    ipaddr = f"{network}.{seq1}.{seq2}"
                    thd = threading.Thread(
                        target=self.__raw_scan, args=(ipaddr, timeout)
                    )
                    threads.append(thd)
                    thd.start()
        else:
            for seq1 in range(max_range[mask]):
                ipaddr = f"{network}.{seq1}"
                thd = threading.Thread(
                    target=self.__raw_scan, args=(ipaddr, timeout)
                )
                threads.append(thd)
                thd.start()

        for t in threads:
            t.join()

        return self.amcrest_ips

