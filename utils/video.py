import asyncio
import os
import re

import youtube_dl
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from settings import YOUTUBE_API_KEY

from pprint import pprint
ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0'
}

ytdl = youtube_dl.YoutubeDL(params=ytdl_format_options)


def youtube_search(query: str):
    youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)

    search_response = youtube.search().list(
        q=query,
        part='id,snippet',
        maxResults=1,
        type='video'
    ).execute()

    for search_result in search_response.get('items', []):
        pprint(search_result)
        return search_result['id']['videoId']


def youtube_playlist(query: str):
    playlist_id = query.split("list=")[1]
    youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)

    response = youtube.playlistItems().list(
        part="snippet",
        playlistId=playlist_id,
        maxResults=50
    ).execute()

    result = []
    for item in response["items"]:
        result.append(item["snippet"]["resourceId"]["videoId"])
    return result


class Video:
    def __init__(self, url: str = None, title: str = None, video_id: str = None):
        self.url = url
        self.title = title
        self.video_id = video_id

    async def get_music_info(self):
        if self.url is not None:
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url=self.url, download=False))
            return data
        elif self.title is not None:
            vid_id = youtube_search(self.title)
            if not vid_id:
                return
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(None, lambda: ytdl.extract_info(
                url="https://www.youtube.com/watch?v=" + vid_id, download=False))
            return data
        elif self.video_id is not None:
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(None, lambda: ytdl.extract_info(
                url="https://www.youtube.com/watch?v=" + self.video_id, download=False))
            return data
