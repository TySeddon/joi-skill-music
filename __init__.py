from ast import Return
from operator import truediv
import random
from adapt.intent import IntentBuilder
from mycroft import MycroftSkill, intent_handler
from mycroft.skills.common_play_skill import CommonPlaySkill, CPSMatchLevel
from mycroft.messagebus import Message
from mycroft.audio import wait_while_speaking
from .spotify import Spotify
from .globals import *
import webbrowser
from time import sleep
import uuid
import urllib.parse
import os

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

    def initialize(self):
        """ Perform any final setup needed for the skill here.
        This function is invoked after the skill is fully constructed and
        registered with the system. Intents will be registered and Skill
        settings will be available."""
        my_setting = self.settings.get('my_setting')
        #self.add_event("mycroft.stop", self.stop)
        self.add_event("recognizer_loop:record_begin", self.handle_listener_started)

    ###########################################

    @intent_handler(IntentBuilder('PlayMusicIntent').require('Music').optionally("Play"))
    def handle_play_music_intent(self, message):
        """ This is an Adapt intent handler, it is triggered by a keyword."""
        self.log.info("handle_play_music_intent")
        self.stopped = False

        self.resident_name = "Ruth"

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

    def open_browser(self):
        self.player_name = "Joi-%s" % (uuid.uuid4())
        url = "%s/joi/spotify?name=%s&token=%s" % (globals.JOI_SERVER_URL, self.player_name, self.spotify.access_token)
        webbrowser.open(url=url, autoraise=True)

    def close_browser(self):
        os.system("killall chromium-browser")

    def session_end(self):
        self.log.info("session_end")
        if self.stopped: return 
        self.speak_dialog(key="Session_End",
                          data={"resident_name": self.resident_name})
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
                                },
                          wait=True)

    def song_followup(self, track):
        self.log.info("song_followup")
        if self.stopped: return 
        self.speak_dialog(key="Song_Followup",
                          data={"artist_name": track.artists[0].name,
                                "song_name": track.name,
                                "resident_name": self.resident_name,
                                },
                          wait=True)

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
            self.log.info("Starting song %s" % (self.track.name))
            self.song_intro(self.track)
            wait_while_speaking()
            self.spotify.start_playback(self.player_name, self.track.uri)
            self.spotify.max_volume()
            self.start_monitor()
            return True
        else:
            self.log.info("No more songs in queue")
            return False

    def is_song_done(self):
        if self.play_state.progress_pct > 0.05:
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

            self.spotify.fade_volume()
            self.spotify.pause_playback(self.player_name)
            self.song_followup(self.track)
            wait_while_speaking()

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

    def stop(self):
        """ The stop method is called anytime a User says "Stop" or a similar command. 
        It is useful for stopping any output or process that a User might want to end 
        without needing to issue a Skill specific utterance such as media playback 
        or an expired alarm notification.
        """
        self.log.info("mycroft.stop")
        self.stopped = True

        self.stop_monitor()
        self.stop_idle_check()
        if self.spotify:
            self.spotify.pause_playback(self.player_name)
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