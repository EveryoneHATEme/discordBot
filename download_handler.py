import os
import youtube_dl

ydl_options = {
    'format': 'bestaudio/best',
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    }]
}


class Downloader:
    def __init__(self, folder: str = 'saved_audio'):
        self.folder = folder
        if not os.path.exists(self.folder):
            os.mkdir(self.folder)

    def download_audio(self, url: str):
        print(f'start download {url}')
        with youtube_dl.YoutubeDL(ydl_options) as yt_downloader:
            yt_downloader.download([url])
        print('got it!')
