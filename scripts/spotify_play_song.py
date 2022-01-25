import spotipy
from spotipy.oauth2 import SpotifyOAuth
from pprint import pprint
from time import sleep
from globals import *

# define scopes required by Joi and web playback
# https://github.com/spotify/web-playback-sdk/issues/11
scope = "user-read-playback-state,user-modify-playback-state,streaming,user-read-email,user-read-private"

client_credentials_manager=SpotifyOAuth(
    client_id=SPOTIPY_CLIENT_ID, 
    client_secret=SPOTIPY_CLIENT_SECRET,
    redirect_uri=SPOTIPY_REDIRECT_URI,
    show_dialog=True,
    scope=scope)
sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)

# get the access token.  Can share this with the web client
token = client_credentials_manager.get_access_token()
pprint(token)

def get_joi_device(sp):
    result = sp.devices()
    devices = result['devices']
    joi_devices = list(filter(lambda o: (o['name']=='Joi Web Player'), devices))
    return joi_devices[0]

# Shows playing devices
joi_device = get_joi_device(sp)
device_id = joi_device['id']
pprint(device_id)

# Change track
sp.start_playback(device_id=device_id, 
                  uris=['spotify:track:6gdLoMygLsgktydTQ71b15'])

# Change volume
# sp.volume(100)
# sleep(2)
# sp.volume(50)
# sleep(2)
# sp.volume(100)

