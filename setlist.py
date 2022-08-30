import requests
from typing import Tuple
from bs4 import BeautifulSoup


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

    search_page = BeautifulSoup(html, features="html.parser")
    div_setlist_preview = search_page.find_all('div', {'class': 'setlistPreview'})[pos-1]
    div_concerts = div_setlist_preview.find_all('div', recursive=False)[1]
    last_concert = div_concerts.find_all('a')[0]
    details_div = div_setlist_preview.find_all('div', {'class': 'details'})[0]
    artist = details_div.find_all('span')[1]

    return last_concert.text, last_concert['href'], artist.text


def get_setlist_by_url(concert_url: str):
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
        setlist_page = BeautifulSoup(setlist_page_html, features="html.parser")
        setlist_div = setlist_page.find_all('div', {'class': 'setlistList'})[0]
        setlist_html = setlist_div.find_all('li', {'class': 'setlistParts song'})
        for li in setlist_html:
            song = li.find_all('a')[0].text
            setlist.append(song)
    except Exception:
        pass
    # TODO - get concert name

    return setlist


def get_setlist_by_artist(artist: str, songs_min: int = 6) -> Tuple[str, list]:
    """
        Gets the last setlist with at least {songs_min} songs of an artist.

        Args:
            - artist (str): artist name to search
            - songs_min (int):
                min amount of songs for the concert to be considered.
                Defaults to 6.

        Returns:
            tuple[str, list[str]]:
                tuple which the first element is the concert's title and
                the second element is a list of songs - setlist.
    """
    print(f"Searching for {artist} setlist...")
    pos = 1
    setlist = []
    while len(setlist) < songs_min:
        concert_title, concert_link, artist_name = search_for_setlist(artist, pos)
        if artist_name.lower() != artist.lower():
            correct_artist = ''
            while correct_artist != 'y' and correct_artist != 'n':
                correct_artist = input(
                    f"Did you mean {artist_name} - instead of {artist}? (y/n)").lower()

            if correct_artist == 'n':
                pos += 1
                continue
            else:
                artist = artist_name
        concert_link = "https://www.setlist.fm/" + concert_link
        setlist = get_setlist_by_url(concert_link)
        pos += 1

    return concert_title, setlist, artist_name
