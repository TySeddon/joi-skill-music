from datetime import datetime, timedelta
from time import sleep
from xmlrpc.client import DateTime
from amcrest import AmcrestCamera
from amcrest.exceptions import CommError
from munch import munchify
import sys
import asyncio
from asyncio import Event
from typing import AsyncIterator
import pandas as pd

PASSWORD = 'Smarthome#1'

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

# async def async_time_ticker(delay: float) -> AsyncIterator[datetime]:
#     while True:
#         await asyncio.sleep(delay)
#         yield datetime.now()  

async def cancellable_aiter(async_iterator: AsyncIterator, cancellation_event: Event) -> AsyncIterator:
    cancellation_task = asyncio.create_task(cancellation_event.wait())
    result_iter = async_iterator.__aiter__()
    while not cancellation_event.is_set():
        next_result_task = asyncio.create_task(result_iter.__anext__())
        done, pending = await asyncio.wait(
            [cancellation_task, next_result_task],
            return_when=asyncio.FIRST_COMPLETED
        )
        for done_task in done:
            if done_task == cancellation_task:
                # clean up the async iterator
                print("cleaning up")
                next_result_task.cancel()
                try:
                    await result_iter.aclose()
                except Exception as error:
                    pass                        
                print("cleaned up")

                break
            else:
                yield done_task.result()
           
def cancel(cancellation_event):
    print("Canceling")
    cancellation_event.set()

async def read_camera_motion_async(camera, seconds_length):
    global is_motion

    # setup cancellation after specified number of seconds
    cancellation_event = asyncio.Event()
    loop = asyncio.get_event_loop()
    loop.call_later(seconds_length, cancel, cancellation_event)

    # initialize event collection
    start_time = datetime.utcnow()
    motion_events = []
    motion_event_pairs = []
    last_event = None
    if bool(camera.is_motion_detected):
        starting_event = build_motion_event('MotionStart')
        motion_events.append(starting_event)
        last_event = starting_event
    else:        
        starting_event = build_motion_event('MotionStop')
        motion_events.append(starting_event)
        last_event = starting_event

    is_motion = last_event.Event == "MotionStart"

    # get events until number of seconds expire
    async_iter = camera.async_event_stream("VideoMotion")
    async for event_str in cancellable_aiter(async_iter, cancellation_event):
        current_event = build_event_obj(event_str)
        #print(current_event)
        motion_events.append(current_event)
        if last_event and last_event.Event == "MotionStart" and current_event.Event == "MotionStop":
            motion_event_pairs.append((last_event, current_event))
        if last_event and last_event.Event == current_event.Event:
            pass # ignore this duplicate event
        else:
            last_event = current_event   

        is_motion = last_event.Event == "MotionStart"

    # end event collection
    ending_event=build_motion_event('End')
    if last_event and last_event.Event == "MotionStart":
        motion_event_pairs.append((last_event, ending_event))
    end_time = datetime.utcnow()

    print("Done")
    return (start_time, end_time, motion_event_pairs)


def build_motion_history(start_time, end_time, motion_event_pairs):
    num_of_seconds = (end_time-start_time).seconds
    print(f"{start_time} to {end_time}.  {num_of_seconds} seconds.")

    history = []
    for current_time in (start_time + timedelta(seconds=n) for n in range(num_of_seconds)):
        is_motion = bool([p for p in motion_event_pairs if p[0].DateTime <= current_time <= p[1].DateTime])
        print(f"{'X' if is_motion else '-'}", end='')
        history.append(int(is_motion))
    sys.stdout.flush()        
    return history

async def report():
    while True:
        global is_motion        
        global is_done
        print(f"{'X' if is_motion else '-'}", end='')
        sys.stdout.flush()
        await asyncio.sleep(1)
        if is_done:
            break

def loop_in_thread(loop):
    asyncio.set_event_loop(loop)
    loop.run_until_complete(report())

def chunk(lst, n):
    for i in range(0,len(lst), n):
        yield lst[i:i+n]

def set_privacy_mode(camera, mode):
    #camera.set_privacy(False)
    camera.command(f"configManager.cgi?action=setConfig&LeLensMask[0].Enable={str(mode).lower()}")

############################

seconds_length = 20
camera = AmcrestCamera('192.168.1.27', 80, 'admin', PASSWORD).camera

#Check software information
print(camera.software_information)


set_privacy_mode(camera, False)
camera.ptz_control_command(action="start", code="PositionABS", arg1=180, arg2=0, arg3=0)
camera.ptz_control_command(action="start", code="PositionABS", arg1=180, arg2=30, arg3=0)

is_done = False
is_motion = False

# real-time report thread
loop = asyncio.new_event_loop()
import threading
t = threading.Thread(target=loop_in_thread, args=(loop,))
t.start()

start_time, end_time, motion_event_pairs = asyncio.run(read_camera_motion_async(camera, seconds_length))
# stop real-time report thread
is_done = True

set_privacy_mode(camera, True)

history = build_motion_history(start_time, end_time, motion_event_pairs)
print(history)

movement_percent = sum(history)/len(history)
print(f"{movement_percent}%")

# calculate aggregate motion every N seconds (resampling)
period_length = 20
resampling = [sum(c)/len(c) for c in chunk(history, period_length)]
print(resampling)    

# rolling 
s = pd.Series(history)
window_size = 5
print(s.rolling(window_size).sum().apply(lambda o: o/window_size).tolist())


