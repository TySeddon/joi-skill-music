# allow using modules in parent 
# in order for this work you would need to 
# C:\Users\tysed\Source\Repos\Joi\joi-skill-music> python .\scripts\spotify_auth.py
import os
import sys
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))

from spotipy.oauth2 import SpotifyClientCredentials
import spotipy
from pprint import pprint
import enviro

SPOTIPY_CLIENT_ID = enviro.get_setting('spotipy_client_id')
SPOTIPY_CLIENT_SECRET = enviro.get_setting('spotipy_client_secret')
SPOTIPY_REDIRECT_URI = enviro.get_setting('spotipy_redirect_uri')
SPOTIPY_SCOPES = enviro.get_setting('spotipy_scopes')

client_credentials_manager = SpotifyClientCredentials(client_id=SPOTIPY_CLIENT_ID, client_secret=SPOTIPY_CLIENT_SECRET)
sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)

search_str = 'Muse'
result = sp.search(search_str)
pprint(result)

res = sp.devices()
pprint(res)
