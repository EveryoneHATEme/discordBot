from yandex_music.client import Client


def tracks_in_album(album_id: int) -> list:
    """
    :param album_id:
    :return: list of dicts
    """
    client = Client()
    info = client.albums_with_tracks(album_id)
    if info["error"]:
        return []
    result = []
    for track in info["volumes"][0]:
        result.append({"artist": track["artists"][0]["name"], "title": track["title"], "id": track["real_id"]})
    return result


def tracks_in_playlist(user_id, playlist_id: int) -> list:
    client = Client()
    info = client.users_playlists(playlist_id, user_id)
    result = []
    for track in info[0]["tracks"]:
        trk_info = track_info(track.id)
        result.append({"artist": trk_info["artist"], "title": trk_info["title"], "id": track.id})
    return result


def direct_link(track_id: int) -> str:
    client = Client()
    try:
        info = client.tracks_download_info(track_id, get_direct_links=True)
        return info[0]["direct_link"]
    except BaseException:
        return ""


def track_info(track_id: int) -> dict:
    client = Client()
    try:
        info = client.tracks(track_id)
        title = info[0]["title"]
        if not title:
            return dict()
        artist = info[0]["artists"][0]["name"]
        return {"artist": artist, "title": title}
    except BaseException:
        return dict()
