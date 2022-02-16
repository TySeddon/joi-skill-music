from amcrest import AmcrestCamera
import socket
from contextlib import closing
from typing import List, Optional
import threading

class CameraFinder():

    amcrest_ips: List[str] = []
    __RTSP_PORT = 554
    __PWGPSI_PORT = 3800
    __HTTP_PORT = 80

    def __init__(self, camera_name, username, password) -> None:
        self.camera_name = camera_name
        self.username = username
        self.password = password

    def __raw_scan(self, ipaddr: str, timeout: Optional[float] = None) -> None:
        if timeout:
            socket.setdefaulttimeout(timeout)
        else:
            # If devices not found, try increasing timeout
            socket.setdefaulttimeout(0.2)

            try:
                with closing(socket.socket()) as sock:
                    sock.connect((ipaddr, self.__RTSP_PORT))
                #with closing(socket.socket()) as sock:
                    #sock.connect((ipaddr, self.__PWGPSI_PORT))
                with closing(socket.socket()) as sock:
                    sock.connect((ipaddr, self.__HTTP_PORT))
                print(f"Found possible camera at {ipaddr}")                    
                camera = AmcrestCamera(ipaddr, self.__HTTP_PORT, self.username, self.password).camera
                if camera:
                    print(f"Found '{camera.machine_name}' at {ipaddr}")
                    if camera.machine_name == self.camera_name:
                        self.amcrest_ips.append(ipaddr)

            # pylint: disable=bare-except
            except:
                pass

    def scan_devices(
        self, subnet: str, timeout: Optional[float] = None
    ) -> List[str]:
        """
        Scan cameras in a range of ips

        Params:
        subnet - subnet, i.e: 192.168.1.0/24
                    if mask not used, assuming mask 24

        timeout - timeout in sec

        Returns:
        """

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

