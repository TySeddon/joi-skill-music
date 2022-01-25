from spotipy.oauth2 import SpotifyClientCredentials
import spotipy
from pprint import pprint
from globals import *

client_credentials_manager = SpotifyClientCredentials(client_id=SPOTIPY_CLIENT_ID, client_secret=SPOTIPY_CLIENT_SECRET)
sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)

search_str = 'Muse'
result = sp.search(search_str)
pprint(result)

res = sp.devices()
pprint(res)
