from ast import Return
from operator import truediv
import random
from adapt.intent import IntentBuilder
from mycroft import MycroftSkill, intent_handler
from mycroft.skills.common_play_skill import CommonPlaySkill, CPSMatchLevel
from mycroft.messagebus import Message
from .spotify import Spotify
from .globals import *
import webbrowser
from time import sleep
import uuid
import urllib.parse

class JoiMusicSkill(MycroftSkill):
    def __init__(self):
        """ The __init__ method is called when the Skill is first constructed.
        It is often used to declare variables or perform setup actions, however
        it cannot utilise MycroftSkill methods as the class does not yet exist.
        """
        super().__init__()
        self.learning = True

    def initialize(self):
        """ Perform any final setup needed for the skill here.
        This function is invoked after the skill is fully constructed and
        registered with the system. Intents will be registered and Skill
        settings will be available."""
        my_setting = self.settings.get('my_setting')
        self.add_event("mycroft.stop", self.stop)

###########################################

    @intent_handler(IntentBuilder('ThankYouIntent').require('ThankYouKeyword'))
    def handle_thank_you_intent(self, message):
        """ This is an Adapt intent handler, it is triggered by a keyword."""
        self.speak_dialog("welcome")

    @intent_handler('HowAreYou.intent')
    def handle_how_are_you_intent(self, message):
        """ This is a Padatious intent handler.
        It is triggered using a list of sample phrases."""
        self.speak_dialog("how.are.you")

    @intent_handler(IntentBuilder('HelloWorldIntent')
                    .require('HelloWorldKeyword'))
    def handle_hello_world_intent(self, message):
        """ Skills can log useful information. These will appear in the CLI and
        the skills.log file."""
        self.log.info("There are five types of log messages: "
                      "info, debug, warning, error, and exception.")
        self.speak_dialog("hello.world")

###########################################

    def shuffle_tracks(self, tracks):
         return random.sample(tracks,5)

    def get_next_track(self):
        if len(self.session_tracks) > 0:
            track = self.session_tracks.pop(0)
            return track
        else:
            return None

    def start_next_song(self):
        self.track = self.get_next_track()
        if self.track:
            self.log.info("Starting song %s" % (self.track.name))
            self.song_intro(self.track)
            self.spotify.max_volume()
            self.spotify.start_playback(self.player_name, self.track.uri)
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

    # async def poll_for_done(self):
    #     while True:
    #         self.play_state = self.spotify.get_playback_state()
    #         print('%.2f %%' % (self.play_state.progress_pct * 100))
    #         if self.play_state.progress_pct > 0.05:
    #             return "All Done"
    #         sleep(1)       

    def poll_for_spotify_update(self):
        self.play_state = self.spotify.get_playback_state()
        self.log.info('%.2f %% - Playing = %s - %s' % (self.play_state.progress_pct * 100, self.play_state.is_playing, self.track.name))

        if not self.play_state.is_playing:
            # if no longer playing, abandon polling after 60 seconds
            self.not_playing_count += 1
            if self.not_playing_count > 60:
                self.stop_monitor()

        if self.is_song_done():
            self.stop_monitor()

            self.spotify.reduce_volume()
            self.spotify.pause_playback(self.player_name)
            self.song_followup(self.track)

            sleep(5)
            started = self.start_next_song()
            if not started:
                self.session_end()

    def session_end(self):
        self.log.info("session_end")
        self.speak_dialog(key="Session_End")

    def song_intro(self, track):
        self.log.info("song_intro")
        self.speak_dialog(key="Song_Intro",
                          data={"artist_name": track.artists[0].name,
                                "song_name": track.name,
                                "resident_name": self.resident_name,
                                },
                          wait=True)

    def song_followup(self, track):
        self.log.info("song_followup")
        self.speak_dialog(key="Song_Followup",
                          data={"artist_name": track.artists[0].name,
                                "song_name": track.name,
                                "resident_name": self.resident_name,
                                },
                          wait=True)

    # def play_songs(self):
    #     track = self.get_next_track()
    #     while track:
    #         self.song_intro(track)
    #         self.spotify.max_volume()
    #         self.spotify.start_playback(self.player_name, track.uri)
    #         asyncio.run(self.poll_for_done())
    #         self.spotify.reduce_volume()
    #         self.spotify.pause_playback(self.player_name)
    #         self.song_followup(track)
    #         track = self.get_next_track()
    #     self.session_end()

    @intent_handler(IntentBuilder('PlayMusicIntent').require('Music').optionally("Play"))
    def handle_play_music_intent(self, message):
        """ This is an Adapt intent handler, it is triggered by a keyword."""
        self.log.info("handle_play_music_intent")

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
        self.player_name = "Joi-%s" % (uuid.uuid4())
        webbrowser.open("%s/joi/spotify?name=%s&token=%s" % (globals.JOI_SERVER_URL, self.player_name, self.spotify.access_token))

        self.start_next_song()

    def start_monitor(self):
        self.log.info("start_monitor")

        # Clear any existing event
        self.stop_monitor()

        # Schedule a new one every second to monitor/update display
        self.schedule_repeating_event(
            self.poll_for_spotify_update, None, 1, name="MonitorSpotify"
        )
        self.add_event("recognizer_loop:record_begin", self.handle_listener_started)

    def stop_monitor(self):
        self.log.info("stop_monitor")
        self.not_playing_count = 0
        self.cancel_scheduled_event("MonitorSpotify")

    def handle_pause(self, message=None):
        self.log.info("handle_pause")
        self.spotify.pause_playback(self.player_name)
        self.play_state.is_playing = False
        self.stop_monitor()        

    def handle_listener_started(self, message):
        self.log.info("handle_listener_started")

        if self.play_state.is_playing:
            self.handle_pause()

            # Start idle check
            self.idle_count = 0
            self.cancel_scheduled_event("IdleCheck")
            self.schedule_repeating_event(
                self.check_for_idle, None, 1, name="IdleCheck"
            )       

    def handle_resume(self):
        self.log.info("handle_resume")
        self.spotify.resume_playback(self.player_name)
        self.play_state.is_playing = True
        self.start_monitor()

    def check_for_idle(self):
        self.log.info("check_for_idle")
        if self.play_state.is_playing:
            self.cancel_scheduled_event("IdleCheck")
            return
        self.idle_count += 1
        if self.idle_count >= 2:
            # Resume playback after 2 seconds of being idle
            self.cancel_scheduled_event("IdleCheck")
            self.handle_resume()

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
        self.spotify.pause_playback(self.player_name)
        return self.shutdown()

    def shutdown(self):
        """ The shutdown method is called during the Skill process termination. 
        It is used to perform any final actions to ensure all processes and operations 
        in execution are stopped safely. This might be particularly useful for Skills 
        that have scheduled future events, may be writing to a file or database, 
        or that have initiated new processes.
        """
        self.stop_monitor()


def create_skill():
    return JoiMusicSkill()