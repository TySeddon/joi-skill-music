from ast import Return
from operator import truediv
import random
from adapt.intent import IntentBuilder
from mycroft import MycroftSkill, intent_handler
from mycroft.skills.common_play_skill import CommonPlaySkill, CPSMatchLevel
from mycroft.messagebus import Message
from mycroft.audio import wait_while_speaking
from .spotify import Spotify
import webbrowser
from time import sleep
import uuid
import os
from amcrest import AmcrestCamera
import socket
import asyncio
from .enviro import get_setting
from .camera.motion import MotionDetection
from .camera.operator import CameraOperator
from .camera.finder import CameraFinder
from ifaddr import get_adapters
import threading

class JoiMusicSkill(MycroftSkill):

    def __init__(self):
        """ The __init__ method is called when the Skill is first constructed.
        It is often used to declare variables or perform setup actions, however
        it cannot utilise MycroftSkill methods as the class does not yet exist.
        """
        super().__init__()
        self.learning = True
        self.stopped = False
        self.play_state = None
        self.spotify = None
        self.JOI_SERVER_URL = get_setting('joi_server_url')

    def initialize(self):
        """ Perform any final setup needed for the skill here.
        This function is invoked after the skill is fully constructed and
        registered with the system. Intents will be registered and Skill
        settings will be available."""
        my_setting = self.settings.get('my_setting')
        #self.add_event("mycroft.stop", self.stop)
        self.add_event("recognizer_loop:record_begin", self.handle_listener_started)
        self.add_event("skill.joi-skill-music.stop", self.stop)

    ###########################################

    @intent_handler(IntentBuilder('PlayMusicIntent').require('Music').optionally("Play"))
    def handle_play_music_intent(self, message):
        """ This is an Adapt intent handler, it is triggered by a keyword."""
        self.log.info("handle_play_music_intent")
        self.start(start_method=f"User said: {message.data['utterance']}")

    def start(self, start_method):
        self.log.info("start")
        self.stopped = False

        # stop the photo player (in case it is running)
        self.bus.emit(Message("skill.joi-skill-photo.stop"))

        self.resident_name = "Ruth"

        # setup camera
        self.motion_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.motion_loop)
        self.camera = self.setup_camera()
        if self.camera:
            self.camera_operator = CameraOperator(self.camera)
            self.camera_motion = MotionDetection(self.camera, self.motion_loop)
            self.set_privacy_mode(False)
            self.camera_operator.set_absolute_position(180,0,0)
            self.camera_operator.set_absolute_position(180,30,0)

        # start the session
        self.speak_dialog(key="Session_Start", 
                          data={"resident_name": self.resident_name})

        # login to Spotify
        self.spotify = Spotify()

        # get list of playlists
        playlists = self.spotify.get_playlists()

        # choose a playlist
        playlist = random.choice(playlists)
        tracks = self.spotify.get_playlist_tracks(playlist.id)

        # create a random set of tracks for this session
        self.session_tracks = self.shuffle_tracks(tracks)

        # launch music player
        self.open_browser()

        wait_while_speaking()

        self.start_next_song(False)

    ##################################

    def get_ip_addresses(self):
        result = []
        for iface in get_adapters():
            for addr in iface.ips:
                if addr.is_IPv4:
                    result.append(addr.ip)
        return result  

    def setup_camera(self):
        CAMERA_NAME = get_setting('camera_name')
        CAMERA_USERNAME = get_setting('camera_username')
        CAMERA_PASSWORD = get_setting('camera_password')
        ip_addresses = [o for o in self.get_ip_addresses() if not o.startswith("169") and not o.startswith("127")]
        self.log.info(ip_addresses)
        if not ip_addresses:
            self.log.error("Could not determine IP address")
            return None
        MY_IP_ADDRESS = ip_addresses[0]
        subnet = f"{MY_IP_ADDRESS}/24"

        self.log.info(f"Searching for camera '{CAMERA_NAME}' on subnet {subnet}")
        finder = CameraFinder(CAMERA_NAME, CAMERA_USERNAME, CAMERA_PASSWORD)
        found_devices = finder.scan_devices(subnet)
        if not found_devices:
            self.log.error(f"Camera '{CAMERA_NAME}' not found on subnet {subnet}")
            return None
        camera_ip_address = found_devices[0]
        self.log.info(f"Found camera at {camera_ip_address}")
        camera = AmcrestCamera(camera_ip_address, 80, CAMERA_USERNAME, CAMERA_PASSWORD).camera
        return camera

    def _run_motion_detection(self, seconds_length):        
        loop = self.motion_loop
        asyncio.set_event_loop(loop)
        #future = asyncio.run_coroutine_threadsafe(self.camera_motion.read_camera_motion_async(seconds_length, self.log), loop=loop)
        self.log.info("Launched motion detection thread")
        start_time, end_time, motion_event_pairs = loop.run_until_complete(self.camera_motion.read_camera_motion_async(seconds_length, self.log))
        self.log.info(f"Motion detection has completed successfully. {len(motion_event_pairs)} motion events occurred")
        self.create_motion_report(start_time, end_time, motion_event_pairs)
        # shutdown motion loop
        self.shutdown_event_loop(self.motion_loop)

    def start_motion_detection(self, seconds_length):
        if hasattr(self, 'camera_motion') and self.camera_motion:
            self.log.info(f"starting motion detection. {seconds_length} seconds")
            # start detecting motion
            #self.motion_task = self.motion_loop.create_task(self.camera_motion.read_camera_motion_async(seconds_length))
            #self.motion_task.add_done_callback(self.handle_motion_detect_done)

            self.motion_thread = threading.Thread(target=self._run_motion_detection, args=[seconds_length])
            self.motion_thread.start()

            # start_time, end_time, motion_event_pairs = asyncio.run(self.camera_motion.read_camera_motion_async(seconds_length, self.log))
            # self.log.info(f"Motion detection has completed successfully. {len(motion_event_pairs)} motion events occurred")
            # self.create_motion_report(start_time, end_time, motion_event_pairs)

    def stop_motion_detection(self):
        if hasattr(self, 'camera_motion') and self.camera_motion:
            # send a cancelation signal to motion detection.
            # handle_motion_detect_done will be called once it has stopped
            self.log.info('stopping motion detection')
            #self.camera_motion.cancel()
            #sleep(1)
            self.motion_loop.call_later(1, self.camera_motion.cancel)
            # if hasattr(self, 'motion_thread') and self.motion_thread:
            #     self.log.info('Joining thread')
            #     self.motion_thread.join()
            #     self.log.info('Thread joined')

    async def handle_motion_detect_done(self, future):
        self.log.info('handle_motion_detect_done')
        if hasattr(self, 'camera_motion') and self.camera_motion:
            # stop motion detection
            self.camera_motion.stop()
            # get motion data
            start_time, end_time, motion_event_pairs = future.result()
            # create a motion report
            self.create_motion_report(start_time, end_time, motion_event_pairs)
            # shutdown motion loop
            self.shutdown_event_loop(self.motion_loop)

    def shutdown_event_loop(self, loop):
        self.log.info('shutdown_event_loop')
        if loop:
            #self.log.info("Waiting for tasks to complete")
            # Find all running tasks:
            #pending = asyncio.all_tasks()
            # Run loop until tasks done:
            #loop.run_until_complete(asyncio.gather(*pending))

            # stop loop
            #self.log.info("Stopping event loop")
            #loop.stop()

            #self.log.info("Waiting for thread join")
            #self.motion_thread.join()

            #self.log.info("Closing event loop")
            # close loop
            #loop.close()

    def create_motion_report(self, start_time, end_time, motion_event_pairs):
        self.log.info('create_motion_report')
        self.log.info('==================================================================')
        if hasattr(self, 'camera_motion') and self.camera_motion:
            history = self.camera_motion.build_motion_history(start_time, end_time, motion_event_pairs)
            self.log.info(history)
            self.motion_report = ""
        self.log.info('==================================================================')

    ##################################

    def open_browser(self):
        self.player_name = f"Joi-{uuid.uuid4()}"
        url = f"{self.JOI_SERVER_URL}/joi/spotify?name={self.player_name}&token={self.spotify.access_token}"
        webbrowser.open(url=url, autoraise=True)

    def close_browser(self):
        os.system("killall chromium-browser")

    def session_end(self):
        self.log.info("session_end")
        if self.stopped: return 
        self.speak_dialog(key="Session_End",
                          data={"resident_name": self.resident_name})
        self.set_privacy_mode(True)
        wait_while_speaking()
        sleep(5)
        self.close_browser()

    def song_intro(self, track):
        self.log.info("song_intro")
        if self.stopped: return 
        self.speak_dialog(key="Song_Intro",
                          data={"artist_name": track.artists[0].name,
                                "song_name": track.name,
                                "resident_name": self.resident_name,
                                })

    def song_followup(self, track):
        self.log.info("song_followup")
        if self.stopped: return 
        self.speak_dialog(key="Song_Followup",
                          data={"artist_name": track.artists[0].name,
                                "song_name": track.name,
                                "resident_name": self.resident_name,
                                })

    ###########################################

    def shuffle_tracks(self, tracks):
         return random.sample(tracks,5)

    def get_next_track(self):
        if len(self.session_tracks) > 0:
            track = self.session_tracks.pop(0)
            return track
        else:
            return None

    def start_next_song(self, pauseFirst):
        self.track = self.get_next_track()
        if self.track:
            if self.stopped: return False
            if pauseFirst:
                sleep(5)
            if self.stopped: return False
            self.log.info("===========================================================")
            self.log.info("===========================================================")
            self.log.info(f"Starting song {self.track.name}")
            self.song_intro(self.track)
            self.log.info(f"Song duration {self.track.duration_ms}ms")
            self.start_motion_detection(self.track.duration_ms / 1000)
            wait_while_speaking()
            self.spotify.start_playback(self.player_name, self.track.uri)
            self.spotify.max_volume()
            self.start_monitor()
            return True
        else:
            self.log.info("No more songs in queue")
            return False

    def is_song_done(self):
        if not self.play_state.progress_pct:
            return True
        elif self.play_state.progress_pct > 0.05:
            return True
        else:
            return False

    def pause_song(self, message=None):
        self.log.info("pause_song")
        self.spotify.pause_playback(self.player_name)
        self.play_state.is_playing = False
        self.stop_monitor()        

    def resume_song(self):
        self.log.info("resume_song")
        self.spotify.resume_playback(self.player_name)
        self.play_state.is_playing = True
        self.start_monitor()

    def start_monitor(self):
        # Clear any existing event
        self.stop_monitor()
        if self.stopped: return

        self.log.info("start_monitor")
        # Schedule a new one every second to monitor Spotify play status
        self.schedule_repeating_event(
            self.monitor_play_state, None, 1, name="MonitorSpotify"
        )
        #self.add_event("recognizer_loop:record_begin", self.handle_listener_started)

    def stop_monitor(self):
        self.log.info("stop_monitor")
        self.cancel_scheduled_event("MonitorSpotify")
        self.not_playing_count = 0

    def monitor_play_state(self):
        self.play_state = self.spotify.get_playback_state()
        if self.play_state.progress_pct:
            self.log.info('%.2f %% - Playing=%s - %s - Vol=%.0f %%' % (self.play_state.progress_pct * 100, self.play_state.is_playing, self.track.name, self.play_state.volume_pct))

        if not self.play_state.is_playing:
            # if no longer playing, abandon polling after 60 seconds
            self.not_playing_count += 1
            if self.not_playing_count > 60:
                self.stop_monitor()
                return

        if self.is_song_done():
            # song is done, so follow-up with user and start next song
            self.stop_monitor()
            self.stop_motion_detection()

            self.spotify.fade_volume()
            self.spotify.pause_playback(self.player_name)
            self.song_followup(self.track)

            wait_while_speaking()

            #let motion detection finish
            wait_count = 0
            while not self.camera_motion.is_done:
                self.log.info("Waiting for motion detection to finish")
                #self.stop_motion_detection()
                sleep(1)
                wait_count += 1

            started = self.start_next_song(True)
            if not started:
                self.session_end()      
                return  

    def handle_listener_started(self, message):
        self.log.info("handle_listener_started")
        if self.play_state and self.play_state.is_playing:
            self.pause_song()
            self.start_idle_check()

    def start_idle_check(self):
        self.idle_count = 0
        self.stop_idle_check()
        self.schedule_repeating_event(
            self.check_for_idle, None, 1, name="IdleCheck"
        )       

    def stop_idle_check(self):
        self.cancel_scheduled_event("IdleCheck")

    def check_for_idle(self):
        self.log.info("check_for_idle")
        if self.play_state and self.play_state.is_playing:
            self.stop_idle_check()
            return
        self.idle_count += 1
        if self.idle_count >= 5:
            # Resume playback after 5 seconds of being idle
            self.stop_idle_check()
            if self.stopped: return
            self.resume_song()

    ###########################################

    # def converse(self, utterances, lang):
    #     """ The converse method can be used to handle follow up utterances 
    #     prior to the normal intent handling process. It can be useful for handling 
    #     utterances from a User that do not make sense as a standalone intent.
    #     """
    #     if utterances and self.voc_match(utterances[0], 'understood'):
    #         self.speak_dialog('great')
    #         return True
    #     else:
    #         return False        

    def set_privacy_mode(self, mode):
        if hasattr(self, 'camera_operator') and self.camera_operator:
            self.camera_operator.set_privacy_mode(mode)

    def stop(self):
        """ The stop method is called anytime a User says "Stop" or a similar command. 
        It is useful for stopping any output or process that a User might want to end 
        without needing to issue a Skill specific utterance such as media playback 
        or an expired alarm notification.
        """
        self.log.info("mycroft.stop")
        self.stopped = True

        self.set_privacy_mode(True)

        self.stop_monitor()
        self.stop_idle_check()
        if self.spotify:
            try:
                self.spotify.pause_playback(self.player_name)
            except Exception as ex:
                self.log.warn(f"Failed to pause of {self.player_name}")
        if self.play_state:
            self.play_state.is_playing = False
        self.close_browser()
        return True

    def shutdown(self):
        """ The shutdown method is called during the Skill process termination. 
        It is used to perform any final actions to ensure all processes and operations 
        in execution are stopped safely. This might be particularly useful for Skills 
        that have scheduled future events, may be writing to a file or database, 
        or that have initiated new processes.
        """
        self.log.info("shutdown")
        self.stop_monitor()
        self.stop_idle_check()


def create_skill():
    return JoiMusicSkill()