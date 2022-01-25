import spotipy
from spotipy.oauth2 import SpotifyOAuth
from pprint import pprint
from time import sleep
from globals import *
import json

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

# Shows playing devices
result = sp.devices()
devices = result['devices']
pprint(type(devices))
pprint(devices)
pprint(len(devices))

joi_devices = list(filter(lambda o: (o['name']=='Joi Web Player'), devices))


joi_device = joi_devices[0]
pprint(joi_device)

#joi_devices = {k:v for (k,v) in devices.items()}
#pprint(joi_devices)

