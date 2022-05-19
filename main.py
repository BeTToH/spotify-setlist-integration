from typing import Tuple
from dotenv import dotenv_values
import requests
from bs4 import BeautifulSoup
from spotipy import Spotify
import spotipy.util as util

def get_html(url):
    res = requests.get(url)    
    html = res.text
    return html

def search_for_setlist(artist: str, pos: int = 1) -> Tuple[str, str, str]:
    """
        Searches for an artist setlist on setlist.fm

        Args:
            - artist (str): artist name to be searched
            - pos (int): position on list returned from search

        Returns:
            Tuple[str, str, str]:
                first element is the concert name,
                second is the link to the setlist, and
                third is the artist name on the setlist web page            
    """
    artist = artist.replace(" ", "+")

    url = f"https://www.setlist.fm/search?query=artist:{artist}"
    html = get_html(url)

    search_page = BeautifulSoup(html)
    div_setlist_preview = search_page.find_all('div', {'class': 'setlistPreview'})[pos-1]
    div_concerts = div_setlist_preview.find_all('div', recursive=False)[1]
    last_concert = div_concerts.find_all('a')[0]
    details_div = div_setlist_preview.find_all('div', {'class': 'details'})[0]
    artist = details_div.find_all('span')[1]

    return last_concert.text, last_concert['href'], artist.text

def get_setlist(artist: str):
    setlist = []
    pos = 1
    while len(setlist) < 6:
        setlist = []
        last_concert_title, last_concert_link, artist_name = search_for_setlist(artist, pos)
        if artist_name.lower() != artist.lower():
            pos += 1
            continue
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


def rmv_special_chars(string: str):
    return ''.join(e for e in string if e.isalnum())


if __name__ == "__main__":    
    # get setlist songs
    artists = ['drake'] 
   
    config = dotenv_values()
    CLIENT_ID = config["CLIENT_ID"]
    CLIENT_SECRET= config["CLIENT_SECRET"]
    REDIRECT_URI = config["REDIRECT_URI"]
    scope = "user-library-read"
    token = util.prompt_for_user_token(client_id=CLIENT_ID, client_secret=CLIENT_SECRET, 
    redirect_uri=REDIRECT_URI, scope="user-library-read playlist-modify-private playlist-modify-public")
    sp = Spotify(token)
    CURRENT_USER_ID = sp.current_user()['id']  
    LIMIT = 5

    playlist_name = ""
    songs = []
    songs_found = []
    songs_not_found = []
    
    for artist in artists:
        title, setlist = get_setlist(artist)
        songs.extend(setlist)
        playlist_name += title + " \ "

        # add setlist songs to that playlist
        song_ids = []
        
        for song in songs:
            print(f"Trying to find song: {song} from {artist}")
            results = sp.search(q=f"{song} {artist}", limit=LIMIT)
                        
            returned_songs = results['tracks']['items']

            was_found = False
            for current_song in returned_songs:
                current_song_name = rmv_special_chars(current_song['name']).lower()
                formatted_song = rmv_special_chars(song).lower()
                if current_song_name == formatted_song:
                    if any(c['name'].lower() == artist.lower() for c in current_song['artists']):
                        song_ids.append(current_song['id'])
                        print(f"{song} was found")
                        songs_found.append(song)
                        was_found = True
                        break

            if not was_found:
                results = sp.search(q=f"{song} {artist}", limit=1)['tracks']['items']
                first_song_artists = [artist['name'] for artist in results[0]['artists']]
                first_song_name = f"{results[0]['name']} from {', '.join(first_song_artists)}"
                print(f"{song} wasn't found. "
                      f"Instead, added {first_song_name}")
                songs_found.append(first_song_name)

    playlist_name = playlist_name[:-3]
      
    playlist = sp.user_playlist_create(CURRENT_USER_ID, playlist_name)

    sp.playlist_add_items(playlist['id'], song_ids)
    print(f"Created playlist {playlist_name} with songs:")
    print('\n'.join([f"\t--{song}" for song in songs_found]))

    print(f"Songs not found: {', '.join(songs_not_found)}")
