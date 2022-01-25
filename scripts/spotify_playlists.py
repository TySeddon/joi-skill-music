# Shows a user's playlists

import spotipy
from spotipy.oauth2 import SpotifyOAuth
from pprint import pprint
from time import sleep
from globals import *
import json
import random
from munch import munchify

client_credentials_manager=SpotifyOAuth(
    client_id=SPOTIPY_CLIENT_ID, 
    client_secret=SPOTIPY_CLIENT_SECRET,
    redirect_uri=SPOTIPY_REDIRECT_URI,
    show_dialog=True,
    scope=SPOTIPY_SCOPES)
sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)

# get the access token.  Can share this with the web client
token = client_credentials_manager.get_access_token()
pprint(token)

access_token = token['access_token']
print(access_token)

#####################################

# get playlist
def get_playlists():
    results = sp.current_user_playlists(limit=50)
    return [munchify(o) for o in list(results['items'])]

playlists = get_playlists()

# list of playlists
for i, item in enumerate(playlists):
    print("%d | %s | %s" % (i, item.name, item.uri))

# tracks in each playlist
for playlist in list(playlists):
    if playlist.name == 'Joi 1963':
        results = sp.playlist_items(playlist.id,
                        fields='items.track.name,items.track.uri,items.track.artists.name,items.track.artists.uri')
        print(json.dumps(results, indent=4))

def get_playlist_tracks(playlist_id):
    results = sp.playlist_items(playlist_id,
                    fields='items.track.name,items.track.uri,items.track.artists.name,items.track.artists.uri')
    return [munchify(item['track']) for item in list(results['items'])]

def shuffle_tracks(tracks):
    return random.sample(tracks,3)

print('============================')
tracks = get_playlist_tracks('2LjLbyEEw9aRqMZo5qpK4O')    
pprint(tracks)
print(type(tracks))

for track in tracks:
    print("%s | %s | %s" % (track.name, track.artists[0].name, track.uri))

# shuffled playlist
print('============================')
for track in shuffle_tracks(tracks):
    print("%s | %s | %s" % (track.name, track.artists[0].name, track.uri))
