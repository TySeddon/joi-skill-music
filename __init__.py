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
import asyncio
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

    # def get_playlist(self):
    #     """ Get the songs and associated artists in a play list """
    #     # todo: hardcode
    #     return [("Bobby Darin","You're the Reason I'm Living"),
    #             ("Elvis Presley", "Slowly But Surely"),
    #             ("Lesley Gore","It's My Party")]

    # def choose_song(self,playlist):
    #     """ Choose a song from the playlist """
    #     # todo: hardcode
    #     return random.choice(playlist)    

    def get_next_track(self):
        if len(self.session_tracks) > 0:
            track = self.session_tracks.pop(0)
            return track
        else:
            return None

    async def poll_for_done(self):
        while True:
            self.play_state = self.spotify.get_playback_state()
            print('%.2f %%' % (self.play_state.progress_pct * 100))
            if self.play_state.progress_pct > 0.05:
                return "All Done"
            sleep(1)       

    def _poll_for_spotify_update(self):
        self.play_state = self.spotify.get_playback_state()

    # def start_next_song(self):
    #     # get song and artist name from first song in playlist
    #     track = self.get_next_track()
    #     if track is not None:
    #         # introduce the next song
    #         self.speak_dialog("Song_Intro",
    #                         {"artist_name": track.artists[0].name,
    #                         "song_name": track.name})
    #         # play the song
    #         self.spotify.start_playback(self.player_name, track.uri)
    #         return True
    #     else:
    #         return False

    def session_end(self):
        self.speak_dialog(key="Session_End")

    def song_intro(self, track):
        self.speak_dialog(key="Song_Intro",
                          data={"artist_name": track.artists[0].name,
                                "song_name": track.name,
                                "resident_name": self.resident_name,
                                },
                          wait=True)

    def song_followup(self, track):
        self.speak_dialog(key="Song_Followup",
                          data={"artist_name": track.artists[0].name,
                                "song_name": track.name,
                                "resident_name": self.resident_name,
                                },
                          wait=True)

    def play_songs(self):
        track = self.get_next_track()
        while track:
            self.song_intro(track)
            self.spotify.max_volume()
            self.spotify.start_playback(self.player_name, track.uri)
            asyncio.run(self.poll_for_done())
            self.spotify.reduce_volume()
            self.spotify.pause_playback(self.player_name)
            self.song_followup(track)
            track = self.get_next_track()
        self.session_end()

    def start_playing(self):
        track = self.get_next_track()
        if track:
            self.song_intro(track)
            self.spotify.max_volume()
            self.spotify.start_playback(self.player_name, track.uri)
            self.start_monitor()

    @intent_handler(IntentBuilder('PlayMusicIntent').require('Music').optionally("Play"))
    def handle_play_music_intent(self, message):
        """ This is an Adapt intent handler, it is triggered by a keyword."""

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

        self.start_playing()

    def start_monitor(self):
        # Clear any existing event
        self.stop_monitor()

        # Schedule a new one every second to monitor/update display
        self.schedule_repeating_event(
            self._poll_for_spotify_update, None, 1, name="MonitorSpotify"
        )
        self.add_event("recognizer_loop:record_begin", self.handle_listener_started)

    def stop_monitor(self):
        # Clear any existing event
        self.cancel_scheduled_event("MonitorSpotify")

    def handle_pause(self, message=None):
        self.spotify.pause_playback(self.player_name)
        self.stop_monitor()        

    def handle_listener_started(self, message):
        if self.play_state.is_playing:
            self.handle_pause()
            self.play_state.is_playing = False

            # Start idle check
            self.idle_count = 0
            self.cancel_scheduled_event("IdleCheck")
            self.schedule_repeating_event(
                self.check_for_idle, None, 1, name="IdleCheck"
            )       

    def handle_resume_song(self):
        self.spotify.resume_playback(self.player_name)
        self.play_state.is_playing = True
        self.start_monitor()

    def check_for_idle(self):
        if not self.play_state.is_playing == False:
            self.cancel_scheduled_event("IdleCheck")
            return

        self.idle_count += 1

        if self.idle_count >= 2:
            # Resume playback after 2 seconds of being idle
            self.cancel_scheduled_event("IdleCheck")
            self.handle_resume_song()

    # def CPS_match_query_phrase(self, msg: str) -> tuple((str, float, dict)):
    #     search_term = urllib.parse.quote_plus(msg)
    #     match_level = CPSMatchLevel.EXACT
    #     return ('found', match_level, {'original_utterance':search_term})

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
        #self.cancel_scheduled_event('my_event')
        #self.stop_my_subprocess()    
        pass


def create_skill():
    return JoiMusicSkill()