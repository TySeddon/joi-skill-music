from time import sleep
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from .enviro import get_setting
from munch import munchify

class Spotify():

    def __init__(self):
        SPOTIPY_CLIENT_ID = get_setting('spotipy_client_id')
        SPOTIPY_CLIENT_SECRET = get_setting('spotipy_client_secret')
        SPOTIPY_REDIRECT_URI = get_setting('spotipy_redirect_uri')
        SPOTIPY_SCOPES = get_setting('spotipy_scopes')

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
                        fields='items.track.name,items.track.uri,items.track.artists.name,items.track.artists.uri,items.track.duration_ms,items.track.explicit')
        return [munchify(item['track']) for item in list(results['items'])]

    def get_device_by_name(self, player_name):
        found = False
        count = 0
        while not found and count < 20:
            result = self.spotify_client.devices()
            devices = [munchify(device) for device in result['devices']]
            joi_devices = list(filter(lambda o: (o['name']==player_name), devices))
            if (len(joi_devices) > 0):
                return munchify(joi_devices[0])
            else:
                count += 1  
                #print("Device %s not found yet. Trying again." % (player_name))
                sleep(1)   
        print(f"Device {player_name} not found after {count} tries") 
        return None                          

    def start_playback(self, player_name, track_uri):
        device = self.get_device_by_name(player_name)
        if device:
            self.spotify_client.start_playback(device_id=device.id, uris=[track_uri])

    def pause_playback(self, player_name):
        device = self.get_device_by_name(player_name)
        if device and device.id and self.spotify_client:
            self.spotify_client.pause_playback(device_id=device.id)

    def resume_playback(self, player_name):
        device = self.get_device_by_name(player_name)
        if device and device.id and self.spotify_client:
            self.spotify_client.start_playback(device_id=device.id)

    def get_playback_state(self):
        result = self.spotify_client.current_playback()
        state = munchify(result)
        if state:
            return munchify({
                'is_playing' : state.is_playing,
                'progress_ms' : state.progress_ms,
                'duration_ms' : state.item.duration_ms,
                'remaining_ms' : state.item.duration_ms - state.progress_ms,
                'progress_pct' : state.progress_ms / state.item.duration_ms,
                'volume_pct': state.device.volume_percent
            })
        else:
            return munchify({
                'is_playing' : False,
                'progress_ms' : None,
                'duration_ms' : None,
                'remaining_ms' : None,
                'progress_pct' : None,
                'volume_pct': None
            })

    def fade_volume(self):
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

    def set_volume(self, volume_pct):
        try:
            self.spotify_client.volume(volume_pct)
        except Exception:
            pass            