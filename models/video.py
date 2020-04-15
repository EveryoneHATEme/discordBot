import youtube_dl
import asyncio

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


class Video:
    def __init__(self, url: str = None, name: str = None):
        self.url = url
        self.name = name

    async def get_music_url(self):
        if self.url is not None:
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url=self.url, download=False))
            return data['url']
        elif self.name is not None:
            # надо как-то научиться искать по названию
            pass
