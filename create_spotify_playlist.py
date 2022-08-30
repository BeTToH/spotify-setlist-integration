from dotenv import dotenv_values
from argparse import ArgumentParser

from spotipy import Spotify
import spotipy.util as util

from setlist import get_setlist_by_artist
from utils import get_user_country, filter_song_in_list


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
    for index, artist in enumerate(ARTISTS):
        print(f"-- {artist.upper()} --")
        if SOURCE == "spot":
            artist_search = sp.search(q=artist, type='artist', limit=1)
            artist = artist_search['artists']['items'][0]
            artist_id = artist['id']
            artist_top_tracks_search = sp.artist_top_tracks(artist_id, country)
            artist_top_tracks = artist_top_tracks_search['tracks']
            for track in artist_top_tracks:
                songs_found[track['id']] = track['name']
                print(f'"{track["name"]}" was found.')
        else:
            title, setlist, artist = get_setlist_by_artist(artist)
            ARTISTS[index] = artist
            for song_desc in setlist:
                song_log = ""
                search = sp.search(q=f"{song_desc} {artist}", limit=SEARCH_LIMIT)
                returned_songs = search['tracks']['items']

                # Try to find song with the exact same name
                song_id = filter_song_in_list(song_desc, artist, returned_songs)
                song_log = f'"{song_desc}" was found.'
                song_name = song_desc
                # If song with the exact same name wasn't found,
                # gets the first one on spotify search
                if not song_id:
                    search = sp.search(q=f"{song_name} {artist}", limit=1, type='track')
                    song = search['tracks']['items'][0]
                    song_artists = [artist['name'] for artist in song['artists']]
                    song_name = song['name']
                    song_desc = f"{song_name} from {', '.join(song_artists)}"

                    song_id = song['id']
                    song_log = (f'"{song_name}" from {artist} wasn\'t found. '
                                f'Instead, added "{song_desc}".')

                if not songs_found.get(song_id):
                    songs_found[song_id] = song_name
                    print(song_log)
        print("")

    if args.playlist_name:
        playlist_name = args.playlist_name
    elif not playlist_name:
        playlist_name = ' \\ '.join([artist.capitalize() for artist in ARTISTS])
    else:
        playlist_name = playlist_name[:-3]  # Remove the " \ " on the final of the string

    playlist = sp.user_playlist_create(CURRENT_USER_ID, playlist_name)

    sp.playlist_add_items(playlist['id'], songs_found.keys())
    print(f"Created playlist {playlist_name} with songs:")
    print('\n'.join([f"\t--{song}" for song in songs_found.values()]))


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
