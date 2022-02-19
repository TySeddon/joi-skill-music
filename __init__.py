from importlib import reload
import os
import random
import asyncio
import threading
import webbrowser
import json
from uuid import uuid4
from time import sleep
from adapt.intent import IntentBuilder
from mycroft import MycroftSkill, intent_handler
from mycroft.skills.common_play_skill import CommonPlaySkill, CPSMatchLevel
from mycroft.messagebus import Message
from mycroft.audio import wait_while_speaking
from amcrest import AmcrestCamera
import joi_skill_utils
reload(joi_skill_utils)

from joi_skill_utils.spotify import Spotify
from joi_skill_utils.enviro import get_setting
from joi_skill_utils.camera_motion import MotionDetection
from joi_skill_utils.camera_operator import CameraOperator
from joi_skill_utils.camera_finder import CameraFinder
from joi_skill_utils.joiclient import JoiClient, MUSIC_TYPE

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
        self.camera_motion = None
        self.camera_operator = None
        self.motion_report = None
        self.memorybox_session = None
        self.session_media = None

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
        self.add_event("skill.joi-skill-utils.motion_event", self.handle_motion_event)

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

        # establish connection to Joi server
        joi_device_id = get_setting("device_id")
        self.joi_client = JoiClient(joi_device_id)
        resident = self.joi_client.get_Resident()
        self.resident_name = resident.first_name

        # setup camera
        self.motion_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.motion_loop)
        self.camera = self.setup_camera()
        if self.camera:
            self.camera_operator = CameraOperator(self.camera, self.log)
            self.camera_motion = MotionDetection(self.camera, self.motion_loop, self.log, self.bus)
            self.set_privacy_mode(False)
            self.camera_operator.set_absolute_position(180,0,0)
            self.camera_operator.set_absolute_position(180,30,0)

        # start the session
        self.speak_dialog(key="Session_Start", 
                          data={"resident_name": self.resident_name})


        # get memory boxes. Choose one at random
        memoryboxes = self.joi_client.list_MemoryBoxes()
        self.log.info(f"{len(memoryboxes)} memoryboxes found")
        music_memoryboxes = list(filter(lambda o: o.memorybox_type == MUSIC_TYPE, memoryboxes))
        self.log.info(f"{len(music_memoryboxes)} music_memoryboxes found")
        music_memorybox = random.choice(music_memoryboxes)
        self.log.info(f"Selected memory box '{music_memorybox.name}'")

        # choose a playlist
        playlist_id = music_memorybox.url
        self.log.info(f"playlist_id = {playlist_id}")

        # start the session
        self.start_memorybox_session(music_memorybox, start_method)

        # login to Spotify
        self.spotify = Spotify()
        # get list of playlists
        #playlists = self.spotify.get_playlists()
        # choose a playlist
        #playlist = random.choice(playlists)
        tracks = self.spotify.get_playlist_tracks(playlist_id)
        # create a random set of tracks for this session
        self.session_tracks = self.shuffle_tracks(tracks)

        # launch music player
        self.open_browser()

        wait_while_speaking()

        self.start_next_song(False)

    ##################################

    def setup_camera(self):
        CAMERA_NAME = get_setting('camera_name')
        CAMERA_USERNAME = get_setting('camera_username')
        CAMERA_PASSWORD = get_setting('camera_password')

        finder = CameraFinder(CAMERA_NAME, CAMERA_USERNAME, CAMERA_PASSWORD, self.log)
        found_devices = finder.scan_devices()
        if not found_devices:
            self.log.error(f"Camera '{CAMERA_NAME}' not found on subnet {finder.subnet}")
            return None
        camera_ip_address = found_devices[0]
        self.log.info(f"Found camera at {camera_ip_address}")

        camera = AmcrestCamera(camera_ip_address, 80, CAMERA_USERNAME, CAMERA_PASSWORD).camera
        return camera

    def _run_motion_detection(self, seconds_length):        
        loop = self.motion_loop
        asyncio.set_event_loop(loop)
        self.log.info("Launched motion detection thread")
        # asynchronously run the camera motion detection
        # wait here until stop signal has been received (self.camera_motion.cancel)
        start_time, end_time, motion_event_pairs = loop.run_until_complete(self.camera_motion.read_camera_motion_async(seconds_length))
        self.log.info(f"Motion detection has completed successfully. {len(motion_event_pairs)} motion events occurred")

        # tasks = asyncio.all_tasks(self.motion_loop)
        # for task in tasks:
        #     self.log.info(f"Task {task.get_name()}, {task.done()}")

        self.create_motion_report(start_time, end_time, motion_event_pairs)

    def start_motion_detection(self, seconds_length):
        if self.camera_motion:
            self.log.info(f"starting motion detection. {seconds_length} seconds")
            self.motion_thread = threading.Thread(
                target=self._run_motion_detection, args=[seconds_length]
            )
            self.motion_thread.start()

    def stop_motion_detection(self):
        if self.camera_motion:
            # send a cancelation signal to motion detection.
            # handle_motion_detect_done will be called once it has stopped
            self.log.info('stopping motion detection')
            self.motion_loop.call_soon_threadsafe(self.camera_motion.cancel)

    def create_motion_report(self, start_time, end_time, motion_event_pairs):
        self.log.info('create_motion_report')
        self.log.info('------------------------------------------------------------------------')
        if self.camera_motion:
            history = self.camera_motion.build_motion_history(start_time, end_time, motion_event_pairs)
            pairs = [(p[0].DateTime.isoformat(), p[1].DateTime.isoformat()) for p in motion_event_pairs]
            report = {
                'start_time':start_time.isoformat(),
                'end_time':end_time.isoformat(),
                'num_of_seconds': (end_time-start_time).seconds,
                'motion_event_pairs': pairs,
                'history': history,
                'percent': round(sum(history)/len(history),2) if history else None
            }
            self.log.info(report)
            self.motion_report = report
        self.log.info('------------------------------------------------------------------------')

    def set_privacy_mode(self, mode):
        if self.camera_operator:
            self.camera_operator.set_privacy_mode(mode)

    ##################################

    def open_browser(self):
        self.player_name = f"Joi-{uuid4()}"
        url = f"{self.JOI_SERVER_URL}/joi/spotify?name={self.player_name}&token={self.spotify.access_token}"

        retry_count = 0
        success = False
        while not success and retry_count < 3:
            success = webbrowser.open(url=url, autoraise=True)
            sleep(1)
            retry_count += 1

        return success            

    def close_browser(self):
        try:
            os.system("killall chromium-browser")
        except:
            self.log.warn("Error closing web browser")

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
            self.log.info("==============================================================================")
            self.log.info(f"Starting song {self.track.name}")
            self.song_intro(self.track)
            self.log.info(f"Song duration {self.track.duration_ms}ms")
            self.start_motion_detection(self.track.duration_ms / 1000)
            self.start_memorybox_session_media(self.track)
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

    ###########################################

    def start_monitor(self):
        # Clear any existing event
        self.stop_monitor()
        if self.stopped: return

        self.log.info("start_monitor")
        self.last_motion_event = None
        # Schedule a new one every second to monitor Spotify play status
        self.schedule_repeating_event(
            self.monitor_play_state, None, 1, name="MonitorSpotify"
        )
        #self.add_event("recognizer_loop:record_begin", self.handle_listener_started)

    def stop_monitor(self):
        self.log.info("stop_monitor")
        self.cancel_scheduled_event("MonitorSpotify")
        self.not_playing_count = 0
        self.last_motion_event = None

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
            self.stop_motion_detection() # send signal to stop motion detection

            self.spotify.fade_volume()
            self.spotify.pause_playback(self.player_name)
            self.song_followup(self.track)
            self.end_memorybox_session_media(self.play_state.progress_pct)
            wait_while_speaking()

            if self.camera_motion:
                #let motion detection finish
                retry_count = 0
                while not self.camera_motion.is_done and retry_count < 10:
                    self.log.info("Waiting for motion detection to finish")
                    sleep(1)
                    retry_count += 1

            started = self.start_next_song(True)
            if not started:
                self.end_memorybox_session("normal completion")
                self.session_end()      
                return  

    def handle_motion_event(self, message):
        event_name = message.data.get('event')
        event_datetime = message.data.get('datetime')
        self.log.info(f"{event_name}, {event_datetime}")
        self.add_media_interaction(event=event_name, data=event_datetime)

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

    def start_memorybox_session(self, music_memorybox, start_method):
        self.memorybox_session = self.joi_client.start_MemoryBoxSession(
                                    memorybox_id=music_memorybox.memorybox_id, 
                                    start_method=start_method)

    def end_memorybox_session(self, end_method):
        if self.memorybox_session:
            self.joi_client.end_MemoryBoxSession(
                            self.memorybox_session.memorybox_session_id,
                            session_end_method=end_method, 
                            resident_self_reported_feeling="NA")
            self.memorybox_session = None                        

    def start_memorybox_session_media(self, track):
        if self.memorybox_session:
            self.session_media = self.joi_client.start_MemoryBoxSessionMedia(
                            memorybox_session_id=self.memorybox_session.memorybox_session_id, 
                            media_url=track.uri,
                            media_name=track.name,
                            media_artist=track.artists[0].name,
                            media_tags="NA",
                            media_classification="NA")

    def end_memorybox_session_media(self, progress_pct):
        if self.session_media:
            progress_pct = progress_pct if progress_pct else 0
            self.joi_client.end_MemoryBoxSessionMedia(
                            memorybox_session_media_id=self.session_media.memorybox_session_media_id, 
                            media_percent_completed = round(progress_pct,2),
                            resident_motion=self.motion_report, 
                            resident_utterances="NA", 
                            resident_self_reported_feeling="NA")
            self.session_media = None                        

    def add_media_interaction(self, event, data):
        if self.session_media:
            progress_pct = self.play_state.progress_pct if self.play_state and self.play_state.progress_pct else None
            progress_pct = progress_pct if progress_pct else 0
            media_interaction = self.joi_client.add_MediaInteraction(
                            memorybox_session_media_id=self.session_media.memorybox_session_media_id, 
                            media_percent_completed=round(progress_pct,2),
                            event=event,
                            data=data)

    def stop_memorybox_session(self, end_method):
        progress_pct = self.play_state.progress_pct if self.play_state and self.play_state.progress_pct else None
        self.end_memorybox_session_media(progress_pct)
        self.end_memorybox_session(end_method)

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

    def stop(self):
        """ The stop method is called anytime a User says "Stop" or a similar command. 
        It is useful for stopping any output or process that a User might want to end 
        without needing to issue a Skill specific utterance such as media playback 
        or an expired alarm notification.
        """
        self.log.info("mycroft.stop")
        self.stopped = True
        self.add_media_interaction(event="stop requested", data=None)

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
        self.stop_memorybox_session("stop")
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
        self.add_media_interaction(event="shutdown", data=None)
        self.stop_memorybox_session("shutdown")


def create_skill():
    return JoiMusicSkill()