from time import sleep
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from .globals import *
from munch import munchify

class Spotify():

    def __init__(self):
        # setup credentials
        self.client_credentials_manager=SpotifyOAuth(
            client_id=SPOTIPY_CLIENT_ID, 
            client_secret=SPOTIPY_CLIENT_SECRET,
            redirect_uri=SPOTIPY_REDIRECT_URI,
            scope=SPOTIPY_SCOPES)

        # create SpotifyClient
        self.spotify_client = spotipy.Spotify(client_credentials_manager=self.client_credentials_manager)

        # get access token
        token = self.client_credentials_manager.get_access_token()
        self.access_token = token['access_token']

    def get_playlists(self):
        results = self.spotify_client.current_user_playlists(limit=50)
        playlists = [munchify(o) for o in list(results['items'])]
        joi_playlists = list(filter(lambda o: o.name.startswith("Joi "),playlists))
        return joi_playlists

    def get_playlist_tracks(self, playlist_id):
        results = self.spotify_client.playlist_items(playlist_id,
                        fields='items.track.name,items.track.uri,items.track.artists.name,items.track.artists.uri')
        return [munchify(item['track']) for item in list(results['items'])]

    def get_device_by_name(self, player_name):
        found = False
        count = 0
        while not found and count < 10:
            result = self.spotify_client.devices()
            devices = [munchify(device) for device in result['devices']]
            joi_devices = list(filter(lambda o: (o['name']==player_name), devices))
            if (len(joi_devices) > 0):
                return munchify(joi_devices[0])
            else:
                count += 1  
                print("Device %s not found yet. Trying again." % (player_name))
                sleep(1)               

    def start_playback(self, player_name, track_uri):
        device = self.get_device_by_name(player_name)
        self.spotify_client.start_playback(device_id=device.id, 
                  uris=[track_uri])

    def pause_playback(self, player_name):
        device = self.get_device_by_name(player_name)
        self.spotify_client.pause_playback(device_id=device.id)

    def get_playback_state(self):
        result = self.spotify_client.current_playback()
        state = munchify(result)
        return munchify({
            'is_playing' : state.is_playing,
            'progress_ms' : state.progress_ms,
            'duration_ms' : state.item.duration_ms,
            'remaining_ms' : state.item.duration_ms - state.progress_ms,
            'progress_pct' : state.progress_ms / state.item.duration_ms,
        })

    def reduce_volume(self):
        try:
            self.spotify_client.volume(50)
            sleep(1)
            self.spotify_client.volume(20)
            sleep(1)
        except Exception:
            pass
        
    def max_volume(self):
        try:
            self.spotify_client.volume(100)
        except Exception:
            pass