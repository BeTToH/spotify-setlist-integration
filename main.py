from dotenv import dotenv_values
import requests
from bs4 import BeautifulSoup
from spotipy import Spotify
import spotipy.util as util

def get_html(url):
    res = requests.get(url)    
    html = res.text
    return html

def get_setlist_info(artist: str, pos: int):
    artist = artist.replace(" ", "+")

    url = f"https://www.setlist.fm/search?query={artist}"
    html = get_html(url)

    search_page = BeautifulSoup(html)
    div_setlist_preview = search_page.find_all('div', {'class': 'setlistPreview'})[pos-1]
    div_concerts = div_setlist_preview.find_all('div', recursive=False)[1]
    last_concert = div_concerts.find_all('a')[0]

    return last_concert.text, last_concert['href']

def get_setlist(artist: str):
    setlist = []
    pos = 1
    while len(setlist) < 6:
        setlist = []
        last_concert_title, last_concert_link = get_setlist_info(artist, pos)
        last_concert_link = "https://www.setlist.fm/" + last_concert_link
        setlist_page_html = get_html(last_concert_link)
        setlist_page = BeautifulSoup(setlist_page_html)
        setlist_div = setlist_page.find_all('div', {'class': 'setlistList'})[0]
        setlist_html = setlist_div.find_all('li', {'class': 'setlistParts song'})
        for li in setlist_html:
            song = li.find_all('a')[0].text
            setlist.append(song)
        pos += 1

    return last_concert_title, setlist

if __name__ == "__main__":
    # get setlist songs
    artists = ['travis scott', 'drake', 'lil nas x']

    playlist_name = ""
    songs = []
    for artist in artists:
        title, setlist = get_setlist(artist)
        songs.extend(setlist)
        playlist_name += title + " \ "

    playlist_name = playlist_name[:-3]
    # create playlist on soptify    
    config = dotenv_values()
    CLIENT_ID = config["CLIENT_ID"]
    CLIENT_SECRET= config["CLIENT_SECRET"]
    REDIRECT_URI = config["REDIRECT_URI"]
    scope = "user-library-read"
    token = util.prompt_for_user_token(client_id=CLIENT_ID, client_secret=CLIENT_SECRET, 
    redirect_uri=REDIRECT_URI, scope="user-library-read playlist-modify-private playlist-modify-public")
    sp = Spotify(token)
    CURRENT_USER_ID = sp.current_user()['id']    
    playlist = sp.user_playlist_create(CURRENT_USER_ID, playlist_name)
    
    # add setlist songs to that playlist
    song_ids = []
    
    for song in songs:
        print(f"Trying to find song: {song}")
        results = sp.search(q=song, limit=1)
        try:            
            song_id = results['tracks']['items'][0]['id']
            song_ids.append(song_id)
            print(f"{song} was found")
        except:
            print(f"{song} wasn't found")            

    sp.playlist_add_items(playlist['id'], song_ids)
    print(f"Created playlist {playlist_name} with songs:")
    print('\n'.join([f"\t--{song}" for song in songs]))
