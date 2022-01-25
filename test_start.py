import pprint
from spotify import Spotify
import random
import uuid
import webbrowser
from time import sleep
from pprint import pprint

# login to Spotify
sp = Spotify()

# get list of playlists
playlists = sp.get_playlists()

# choose a playlist
playlist = random.choice(playlists)
tracks = sp.get_playlist_tracks(playlist.id)

# create a random set of tracks for this session
session_tracks = random.sample(tracks,3)

# launch music player
player_name = "Joi-%s" % (uuid.uuid4())
webbrowser.open("http://127.0.0.1:8000/joi/spotify?name=%s&token=%s" % (player_name, sp.access_token))

def get_next_track():
    if len(session_tracks) > 0:
        track = session_tracks.pop(0)
        return track
    else:
        return None

track = get_next_track()
sp.start_playback(player_name, track.uri)

