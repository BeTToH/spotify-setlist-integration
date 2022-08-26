import requests
from typing import Tuple
from dotenv import dotenv_values
from bs4 import BeautifulSoup
from argparse import ArgumentParser

from spotipy import Spotify
import spotipy.util as util
import ipinfo


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
    print(f"Searching for {artist} setlist...")
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
    # TODO - add docstring
    return ''.join(e for e in string if e.isalnum())


def filter_song_in_list(song_name: str, artist: str, songs: list) -> str:
    # TODO - add docstring
    for current_song in songs:
        current_song_name = rmv_special_chars(current_song['name']).lower()
        formatted_song = rmv_special_chars(song_name).lower()
        if (current_song_name == formatted_song
            and any(c['name'].lower() == artist.lower()
                    for c in current_song['artists'])):
            return current_song['id']
    return None


def get_user_country(ipinfo_token: str):
    # TODO - add docstring
    handler = ipinfo.getHandler(ipinfo_token)
    match = handler.getDetails()
    return match.details['country']


def main(args):
    ARTISTS: list[str] = args.artists
    SOURCE = str(args.source).lower()
    SEARCH_LIMIT = 3

    config = dotenv_values()
    CLIENT_ID = config["CLIENT_ID"]
    CLIENT_SECRET = config["CLIENT_SECRET"]
    REDIRECT_URI = config["REDIRECT_URI"]
    SCOPE = "user-library-read playlist-modify-private playlist-modify-public"
    if SOURCE == 'spot':
        IPINFO_TOKEN = config['IPINFO_TOKEN']
        country = get_user_country(IPINFO_TOKEN)
        print(f"User country: {country}")

    print(f"Creating playlist with the artists: {','.join(ARTISTS)}")

    token = util.prompt_for_user_token(client_id=CLIENT_ID, client_secret=CLIENT_SECRET,
                                       redirect_uri=REDIRECT_URI, scope=SCOPE)
    sp = Spotify(token)
    CURRENT_USER_ID = sp.current_user()['id']

    playlist_name = ""
    songs_found = {}
    # TODO - create functions to reduce main size
    for artist in ARTISTS:
        print(f"-- {artist.upper()} --")
        if SOURCE == "spot":
            artist_search = sp.search(q=artist, type='artist', limit=1)
            artist = artist_search['artists']['items'][0]
            artist_id = artist['id']
            artist_top_tracks_search = sp.artist_top_tracks(artist_id, country)
            artist_top_tracks = artist_top_tracks_search['tracks']
            for track in artist_top_tracks:
                songs_found[track['name']] = track['id']
                print(f'"{track["name"]}" was found.')
        else:
            title, setlist = get_setlist_by_artist(artist)
            for song_desc in setlist:
                song_log = ""
                search = sp.search(q=f"{song_desc} {artist}", limit=SEARCH_LIMIT)
                returned_songs = search['tracks']['items']

                # Try to find song with the exact same name
                song_id = filter_song_in_list(song_desc, artist, returned_songs)
                song_log = f'"{song_desc}" was found.'

                # If song with the exact same name wasn't found,
                # gets the first one on spotify search
                if not song_id:
                    search = sp.search(q=f"{song_id} {artist}", limit=1, type='track')
                    song = search['tracks']['items'][0]
                    song_artists = [artist['name'] for artist in song['artists']]
                    song_name = song['name']
                    song_desc = f"{song_name} from {', '.join(song_artists)}"

                    song_id = song['id']
                    song_log = (f'"{song_name}" from {artist} wasn\'t found. '
                                f'Instead, added {song_desc}.')

                if not songs_found.get(song_id):
                    songs_found[song_id] = song_name
                    print(song_log)
        print("")

    if args.playlist_name:
        playlist_name = args.playlist_name
    else:
        playlist_name = playlist_name[:-3]  # Remove the " \ " on the final of the string

    playlist = sp.user_playlist_create(CURRENT_USER_ID, playlist_name)

    sp.playlist_add_items(playlist['id'], songs_found.keys())
    print(f"Created playlist {playlist_name} with songs:")
    print('\n'.join([f"\t--{song}" for song in songs_found.keys()]))


if __name__ == "__main__":
    argparse = ArgumentParser()
    argparse.add_argument(
        'artists', nargs="*", type=str, help="The artists to be included in the playlist")
    argparse.add_argument('-p', '--playlist_name', type=str, default=None,
                          help="Custom name for the playlist.")
    argparse.add_argument('-s', '--source', type=str, default="spot",
                          help="Source of the playlist. Use 'setlist' to create it based "
                               "on the most recent concert setlist - from setlist.fm. "
                               "Or 'spot' to get the top 10 tracks on Spotify. The default "
                               "value is 'spot'.")
    main(argparse.parse_args())
