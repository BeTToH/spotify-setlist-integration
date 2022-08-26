import ipinfo


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
