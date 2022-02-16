from camera.motion import MotionDetection
from camera.operator import CameraOperator
from camera.finder import CameraFinder
from amcrest import AmcrestCamera
import asyncio
from asyncio import Event
import pandas as pd
import threading
from enviro import get_setting
import socket

CAMERA_NAME = get_setting('camera_name')
CAMERA_PASSWORD = get_setting('camera_password')
MY_IP_ADDRESS = socket.gethostbyname(socket.gethostname())

seconds_length = 20

finder = CameraFinder(CAMERA_NAME, 'admin', CAMERA_PASSWORD)
found_devices = finder.scan_devices(f"{MY_IP_ADDRESS}/24")
if found_devices:
    camera_ip_address = found_devices[0]
else:
    print(f"Camera '{CAMERA_NAME}' not found on network")
    quit()    

camera = AmcrestCamera(camera_ip_address, 80, 'admin', CAMERA_PASSWORD).camera
#Check software information
print(camera.software_information)

operator = CameraOperator(camera)
motion = MotionDetection(camera)

# position camera
operator.set_privacy_mode(False)
operator.set_absolute_position(180,0,0)
operator.set_absolute_position(180,30,0)

# setup real-time report thread (optional)
def loop_in_thread(loop, motion):
    asyncio.set_event_loop(loop)
    loop.run_until_complete(motion.report_loop())
loop = asyncio.new_event_loop()
report_thread = threading.Thread(target=loop_in_thread, args=(loop,motion))
report_thread.start()

# start detecting motion
start_time, end_time, motion_event_pairs = asyncio.run(motion.read_camera_motion_async(seconds_length))
# stop motion detection
motion.stop()

# put camera in privacy mode
operator.set_privacy_mode(True)


###################################
# report motion history
history = motion.build_motion_history(start_time, end_time, motion_event_pairs)
print(history)

movement_percent = sum(history)/len(history)
print(f"{movement_percent * 100}%")

# calculate aggregate motion every N seconds (resampling)
def chunk(lst, n):
    for i in range(0,len(lst), n):
        yield lst[i:i+n]
period_length = 20
resampling = [sum(c)/len(c) for c in chunk(history, period_length)]
print(resampling)    

# rolling 
s = pd.Series(history)
window_size = 5
print(s.rolling(window_size).sum().apply(lambda o: o/window_size).tolist())


