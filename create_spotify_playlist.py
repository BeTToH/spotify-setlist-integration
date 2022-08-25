import requests
from typing import Tuple
from dotenv import dotenv_values
from bs4 import BeautifulSoup
from argparse import ArgumentParser

from spotipy import Spotify
import spotipy.util as util


def get_html(url: str):
    """
        Get the html of a page

        Args:
            url (str): url of the page

        Returns:
            str: the html of the page
    """
    res = requests.get(url)
    html = res.text
    return html


def search_for_setlist(artist: str, pos: int = 1) -> Tuple[str, str, str]:
    """
        Searches for an artist setlist on setlist.fm

        Args:
            - artist (str): artist name to search
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


def get_setlist_by_artist(artist: str) -> Tuple[str, list]:
    """
        Gets the last setlist with at least 7 songs of an artist.

        Args:
            - artist (str): artist name to search

        Returns:
            tuple[str, list[str]]:
                tuple which the first element is the concert's title and
                the second element is a list of songs - setlist.
    """
    pos = 1
    setlist = []
    while len(setlist) < 6:
        concert_title, concert_link, artist_name = search_for_setlist(artist, pos)
        if artist_name.lower() != artist.lower():
            pos += 1
            continue
        concert_link = "https://www.setlist.fm/" + concert_link
        setlist = get_setlist(concert_link)
        pos += 1

    return concert_title, setlist


def get_setlist(concert_url: str):
    """
        Gets a setlist by the url

        Args:
            - concert_url (str): url of the concert to get the setlist from

        Returns:
            list: the setlist - a list of songs
    """
    # TODO - add better exception treatment
    try:
        setlist = []
        setlist_page_html = get_html(concert_url)
        setlist_page = BeautifulSoup(setlist_page_html)
        setlist_div = setlist_page.find_all('div', {'class': 'setlistList'})[0]
        setlist_html = setlist_div.find_all('li', {'class': 'setlistParts song'})
        for li in setlist_html:
            song = li.find_all('a')[0].text
            setlist.append(song)
    except Exception:
        pass
    # TODO - get concert name

    return setlist


def rmv_special_chars(string: str):
    return ''.join(e for e in string if e.isalnum())


def main(args):
    ARTISTS = args.artists
    SEARCH_LIMIT = 5

    print(f"Creating playlist with the artists: {','.join(ARTISTS)}")

    # env vars
    config = dotenv_values()
    CLIENT_ID = config["CLIENT_ID"]
    CLIENT_SECRET = config["CLIENT_SECRET"]
    REDIRECT_URI = config["REDIRECT_URI"]

    SCOPE = "user-library-read playlist-modify-private playlist-modify-public"
    token = util.prompt_for_user_token(client_id=CLIENT_ID, client_secret=CLIENT_SECRET,
                                       redirect_uri=REDIRECT_URI, scope=SCOPE)
    sp = Spotify(token)
    CURRENT_USER_ID = sp.current_user()['id']

    playlist_name = ""
    songs_found = {}

    for artist in ARTISTS:
        title, setlist = get_setlist_by_artist(artist)
        playlist_name += title + " \\ "

        for song in setlist:
            first_song = sp.search(q=f"{song} {artist}", limit=SEARCH_LIMIT)
            returned_songs = first_song['tracks']['items']

            # Try to find song with the exact same name
            was_found = False
            for current_song in returned_songs:
                current_song_name = rmv_special_chars(current_song['name']).lower()
                formatted_song = rmv_special_chars(song).lower()
                if current_song_name == formatted_song:
                    if any(c['name'].lower() == artist.lower()
                           for c in current_song['artists']):
                        songs_found[song] = current_song['id']
                        was_found = True
                        print(f"{song} was found")
                        break

            # If song with the exact same name wasn't found,
            # gets the first one on spotify search
            if not was_found:
                first_song = sp.search(q=f"{song} {artist}", limit=1)['tracks']['items'][0]
                first_song_artists = [artist['name'] for artist in first_song['artists']]
                first_song_name = (f"{first_song['name']} from "
                                   f"{', '.join(first_song_artists)}")
                songs_found[first_song_name] = first_song['id']
                print(f"{song} from {artist} wasn't found. "
                      f"Instead, added {first_song_name}")

    # TODO - remove duplicates of the 'songs_found'
    playlist_name = playlist_name[:-3]  # Remove the " \ " on the final of the string

    playlist = sp.user_playlist_create(CURRENT_USER_ID, playlist_name)

    sp.playlist_add_items(playlist['id'], songs_found.values())
    print(f"Created playlist {playlist_name} with songs:")
    print('\n'.join([f"\t--{song}" for song in songs_found.keys()]))


if __name__ == "__main__":
    argparse = ArgumentParser()
    artists = argparse.add_argument(
        'artists', nargs="*", type=str, help="The artists to be included in the playlist")
    main(argparse.parse_args())
