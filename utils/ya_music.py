import asyncio

from yandex_music.client import Client

CLIENT = Client()


async def tracks_in_album(album_id: int, take_first: bool = False) -> list:
    loop = asyncio.get_event_loop()
    info = await loop.run_in_executor(None, lambda: CLIENT.albums_with_tracks(album_id))
    if info["error"]:
        return []
    if take_first:
        result = [{"artist": info["volumes"][0][0]["artists"][0]["name"],
                   "title": info["volumes"][0][0]["title"],
                   "id": info["volumes"][0][0]["real_id"]}]
    else:
        result = [{"artist": track["artists"][0]["name"], "title": track["title"], "id": track["real_id"]}
                  for track in info["volumes"][0]]
    return result


async def tracks_in_playlist(user_id, playlist_id: int) -> list:
    loop = asyncio.get_event_loop()
    info = await loop.run_in_executor(None, lambda: CLIENT.users_playlists(playlist_id, user_id))
    result = []
    tracks = CLIENT.tracks([track.id for track in info[0]["tracks"]])
    for track in tracks:
        result.append({"artist": track.artists[0].name, "title": track.title, "id": track.id})
    return result


async def direct_link(track_id: int) -> str:
    loop = asyncio.get_event_loop()
    try:
        info = await loop.run_in_executor(None, lambda: CLIENT.tracks_download_info(track_id, get_direct_links=True))
        return info[0]["direct_link"]
    except Exception:
        return ""


async def track_info(track_id: int) -> dict:
    loop = asyncio.get_event_loop()
    try:
        info = await loop.run_in_executor(None, lambda: CLIENT.tracks(track_id))
        title = info[0]["title"]
        if not title:
            return dict()
        artist = info[0]["artists"][0]["name"]
        return {"artist": artist, "title": title}
    except Exception:
        return dict()
