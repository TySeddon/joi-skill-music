from datetime import datetime, timedelta
from time import sleep
from xmlrpc.client import DateTime
from amcrest import AmcrestCamera
from amcrest.exceptions import CommError
from munch import munchify

PASSWORD = 'Smarthome#1'

camera = AmcrestCamera('192.168.1.26', 80, 'admin', PASSWORD).camera

#Check software information
print(camera.software_information)

print(camera.is_motion_detector_on())

print(camera.is_record_on_motion_detection())

#print(camera.storage_device_info())
print(camera.event_channels_happened("VideoMotion"))

#camera.snapshot(channel=0, path_file="snapshot00.jpeg")
camera.ptz_control_command(action="start", code="PositionABS", arg1=180, arg2=0, arg3=0)
camera.ptz_control_command(action="start", code="PositionABS", arg1=180, arg2=30, arg3=0)
#camera.ptz_control_command(action="start", code="AutoScanOn", arg1=0, arg2=0, arg3=0)
#quit()

""" motion_observations = []
for i in range(30):
    is_hit = bool(camera.is_motion_detected)
    dt = datetime.utcnow()
    print(f"{is_hit}, {dt}")
    motion_observations.append((is_hit, dt))
    sleep(1)

motion_hits = list(filter(lambda o: o[0] == True, motion_observations))
motion_percent = len(motion_hits)/len(motion_observations)
print(motion_percent) """

# for i in range(10):
#     print(camera.event_stream("VideoMotion"))
#     sleep(1)

# for i in range(20):
#     e = next(camera.event_stream("VideoMotion"))
#     print(e)

def build_motion_event(event_name):
    return munchify({
        'Event':event_name,
        'DateTime':datetime.utcnow()
    })

def build_event_obj(event_str):
    if "Code=VideoMotion" in event_str:
        if "action=Start" in event_str:
            return build_motion_event('MotionStart')
        elif "action=Stop" in event_str:
            return build_motion_event('MotionStop')
        else:
            return None
    else:
        return None


seconds_length = 30
end_time = datetime.utcnow() + timedelta(days=0,seconds=seconds_length)
motion_events = []
motion_event_pairs = []
last_event = None
if bool(camera.is_motion_detected):
    starting_event = build_motion_event('MotionStart')
    motion_events.append(starting_event)
    last_event = starting_event
try:
    for event_str in camera.event_stream("VideoMotion", timeout_cmd=float(seconds_length)):
        current_event = build_event_obj(event_str)
        print(current_event)
        motion_events.append(current_event)
        if last_event and last_event.Event == "MotionStart" and current_event.Event == "MotionStop":
            motion_event_pairs.append((last_event, current_event))
        if last_event and last_event.Event == current_event.Event:
            pass # ignore this duplicate event
        else:
            last_event = current_event            
        if datetime.utcnow() > end_time:
            break
except CommError as error:
    pass
finally:
    ending_event=build_motion_event('End')
    if last_event and last_event.Event == "MotionStart":
        motion_event_pairs.append((last_event, ending_event))
#motion_events.sort(key=lambda o: o.DateTime)

print("==============")
print(motion_events)
print("==============")
for p in motion_event_pairs:
    print(f"{p[0].DateTime} to {p[1].DateTime}")
print("==============")

# sort in place

first_event = motion_events[0]
last_event = motion_events[-1]
num_of_seconds = (last_event.DateTime-first_event.DateTime).seconds

for current_time in (first_event.DateTime + timedelta(seconds=n) for n in range(num_of_seconds)):
    is_motion = bool([p for p in motion_event_pairs if p[0].DateTime <= current_time <= p[1].DateTime])
    print(f"{'m' if is_motion else '-'}", end='')

# todo: write a routine to find camera
