from os import stat
import pprint
from spotify import Spotify
import random
import uuid
import webbrowser
from time import sleep
from pprint import pprint
import asyncio

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

def play_next_track():
    track = get_next_track()
    if track is not None:
        sp.start_playback(player_name, track.uri)
        return True
    else:
        return False        

async def poll_for_done():
    while True:
        play_state = sp.get_playback_state()
        pprint(play_state)
        if play_state.progress_pct > 0.02:
            return "All Done"
        last_progress = play_state.progress_pct
        sleep(1)

def handle_song_done():
    playing_next = play_next_track()
    if playing_next:
        asyncio.run(wait_for_done())
    else:
        print("That was the last song")

async def wait_for_done():
    task = asyncio.create_task(poll_for_done())
    task.add_done_callback(lambda x: handle_song_done())

play_next_track()
asyncio.run(wait_for_done())

