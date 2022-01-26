from os import stat
import pprint
from spotify import Spotify
import random
import uuid
import webbrowser
from time import sleep
from pprint import pprint
import asyncio
from globals import *

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
webbrowser.open("%s/joi/spotify?name=%s&token=%s" % (JOI_SERVER_URL, player_name, sp.access_token))

def get_next_track():
    if len(session_tracks) > 0:
        track = session_tracks.pop(0)
        return track
    else:
        return None

# def play_next_track():
#     track = get_next_track()
#     if track is not None:
#         sp.start_playback(player_name, track.uri)
#         return True
#     else:
#         return False        

async def poll_for_done():
    while True:
        play_state = sp.get_playback_state()
        print('%.2f %%' % (play_state.progress_pct * 100))
        if play_state.progress_pct > 0.02:
            return "All Done"
        last_progress = play_state.progress_pct
        sleep(1)

# def handle_song_done():
#     playing_next = play_next_track()
#     if playing_next:
#         asyncio.run(wait_for_done())
#     else:
#         print("That was the last song")

# async def wait_for_done():
#     task = asyncio.create_task(poll_for_done())
#     task.add_done_callback(lambda x: handle_song_done())

def song_intro():
    print("Song intro")

def song_followup():
    print("Follow-up")

track = get_next_track()
while track:
    song_intro()
    sp.start_playback(player_name, track.uri)
    asyncio.run(poll_for_done())
    song_followup()
    track = get_next_track()

