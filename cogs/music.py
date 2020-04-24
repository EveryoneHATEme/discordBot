import re
import asyncio

import discord
from discord.ext import commands

from utils import Video
from utils.video import youtube_playlist
from utils import ya_music
from gtts import gTTS

from db.models.guilds_to_urls import GuildsToUrls
from db import db_session


ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn -nostats -loglevel 0'
}


class Music(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command('play')
    async def play(self, context: commands.context.Context, *args):
        already_play = False
        query = " ".join(args).strip()
        if not query:
            await context.send(f'Empty request')
            return
        if not self.voice_client(context):
            self.clear_playlist(context)
        if self.is_yt_video(query):
            music_info: dict = await Video(url=query).get_music_info()
            self.add_to_playlist(context, music_info['title'], music_info['url'])
        elif self.is_yt_playlist(query):
            video_ids = await youtube_playlist(query)
            music_info: dict = await Video(video_id=video_ids[0]).get_music_info()
            self.add_to_playlist(context, music_info['title'], music_info['url'])
            already_play = True
            await asyncio.gather(self.add_to_playlist_from_album_yt(context, video_ids[1:]),
                                 self.__play(context))
        elif self.is_yamusic_playlist(query):
            query = query.split("/")
            track = await ya_music.tracks_in_album(int(query[-1]), take_first=True)
            link = await ya_music.direct_link(track[0]['id'])
            if link and track:
                self.add_to_playlist(context, track[0]["artist"] + ' - ' + track[0]["title"], link)
            already_play = True
            await asyncio.gather(self.add_to_playlist_from_album_ya_music(context, int(query[-1])),
                                 self.__play(context))
        elif self.is_yamusic_user_playlist(query):
            query = query.split("/")
            user_id = query[-3] if query[-1] else query[-4]
            playlist_id = int(query[-1]) if query[-1] else int(query[-2])
            tracks = ya_music.tracks_in_playlist(user_id, playlist_id)
            for track in tracks:
                link = ya_music.direct_link(track["id"])
                if link:
                    self.add_to_playlist(context, track["artist"] + ' - ' + track["title"], link)
        elif self.is_yamusic_track(query):
            query = query.split("/")
            track_id = int(query[-1]) if query[-1] else int(query[-2])
            track = await ya_music.track_info(track_id)
            link = await ya_music.direct_link(track_id)
            if link and track:
                self.add_to_playlist(context, track["artist"] + ' - ' + track["title"], link)
        else:
            music_info: dict = await Video(title=query).get_music_info()
            self.add_to_playlist(context, music_info['title'], music_info['url'])
        if not already_play:
            await self.__play(context)

    @commands.command('speak')
    async def speak(self, context: commands.context.Context, *args):
        already_play = False
        text = " ".join(args).strip()
        print(text)
        tts = gTTS(text, lang="ru")
        urls = tts.get_urls()
        if not self.voice_client(context):
            self.clear_playlist(context)
        for i in range(len(urls)):
            self.add_to_playlist(context, f"{text[:30]} part {i+1}", urls[i])
        if not already_play:
            await self.__play(context)

    async def add_to_playlist_from_album_ya_music(self, context: commands.context.Context, album_id: int):
        tracks = await ya_music.tracks_in_album(int(album_id))
        for track in tracks[1:]:
            link = await ya_music.direct_link(track["id"])
            if link:
                self.add_to_playlist(context, track["artist"] + ' - ' + track["title"], link)

    async def add_to_playlist_from_album_yt(self, context: commands.context.Context, video_ids: list):
        for vid_id in video_ids:
            music_info: dict = await Video(video_id=vid_id).get_music_info()
            self.add_to_playlist(context, music_info['title'], music_info['url'])

    async def __play(self, context: commands.context.Context):
        voice_channel = self.voice_channel(context)
        session = db_session.create_session()
        result = session.query(GuildsToUrls).filter(GuildsToUrls.guild == voice_channel.guild.id).all()
        if not result:
            await context.send(f'Playlist is empty')
            voice_client = self.voice_client(context)
            if voice_client:
                await self.disconnect(context)
            return
        voice_client = self.voice_client(context)
        if not voice_client:
            voice_client: discord.voice_client.VoiceClient = await voice_channel.connect()
        if not voice_client.is_playing() and not voice_client.is_paused():
            voice_client.play(discord.FFmpegPCMAudio(result[0].url, **ffmpeg_options))
            await context.send(f'Playing {result[0].title}')
            await asyncio.sleep(5)
            while voice_client.is_playing() or voice_client.is_paused():
                await asyncio.sleep(1)
            await self.play_next(context)

    @commands.command(aliases=['next', 'skip'])
    async def play_next(self, context: commands.context.Context):
        voice_client = self.voice_client(context)
        if not voice_client:
            return
        voice_channel = self.voice_channel(context)
        session = db_session.create_session()
        result = session.query(GuildsToUrls).filter(GuildsToUrls.guild == voice_channel.guild.id).all()
        if result:
            session.delete(result[0])
            session.commit()
            voice_client.stop()
            await self.__play(context)
        else:
            await self.disconnect(context)

    @commands.command('list')
    async def songs_list(self, context: commands.context.Context):
        voice_client = self.voice_client(context)
        if not voice_client:
            return
        voice_channel = self.voice_channel(context)
        session = db_session.create_session()
        result_list = []
        result = session.query(GuildsToUrls).filter(GuildsToUrls.guild == voice_channel.guild.id).all()
        if result:
            for i in range(len(result)):
                result_list.append(f'{i + 1}: {result[i].title}')
            res_str = "\n".join(result_list)
            for str in [res_str[y - 1998:y] for y in range(1998, len(res_str) + 1998, 1998)]:
                await context.send(str)
        else:
            await context.send(f'Playlist is empty')
            await self.disconnect(context)

    @commands.command('p_clear')
    async def p_clear(self, context: commands.context.Context):
        voice_client = self.voice_client(context)
        if not voice_client:
            return
        voice_channel = self.voice_channel(context)
        session = db_session.create_session()
        result = session.query(GuildsToUrls).filter(GuildsToUrls.guild == voice_channel.guild.id).all()
        if result:
            for i in range(len(result)):
                session.delete(result[i])
            session.commit()
            await context.send(f'Playlist is clear now')
            voice_client.stop()
        else:
            await self.disconnect(context)

    @commands.command('pause')
    async def pause(self, context: commands.context.Context):
        voice_client = self.voice_client(context)
        if voice_client and voice_client.is_playing():
            voice_client.pause()

    @commands.command('resume')
    async def resume(self, context: commands.context.Context):
        voice_client = self.voice_client(context)
        if voice_client and voice_client.is_paused():
            voice_client.resume()

    @commands.command(aliases=['stop', 'leave', 'dc'])
    async def disconnect(self, context: commands.context.Context):
        voice_client = self.voice_client(context)
        if voice_client:
            await voice_client.disconnect()
            self.clear_playlist(context)

    def voice_client(self, context: commands.context.Context) -> discord.voice_client.VoiceClient:
        """
        :param context:
        :return: voice_client if exists otherwise None
        """
        voice_channel = self.voice_channel(context)
        if self.bot.user in voice_channel.members:
            return voice_channel.guild.voice_client

    @staticmethod
    def voice_channel(context: commands.context.Context) -> discord.VoiceChannel:
        return context.message.author.voice.channel

    @commands.command('playing')
    async def is_playing(self, context: commands.context.Context):
        voice_channel = self.voice_channel(context)
        voice_client = self.voice_client(context)
        if not voice_client:
            voice_client: discord.voice_client.VoiceClient = await voice_channel.connect()
        await context.send(f'{voice_client.is_playing()}')

    def clear_playlist(self, context: commands.context.Context):
        voice_channel = self.voice_channel(context)
        session = db_session.create_session()
        result = session.query(GuildsToUrls).filter(GuildsToUrls.guild == voice_channel.guild.id).all()
        for instance in result:
            session.delete(instance)
            session.commit()

    @staticmethod
    def add_to_playlist(context: commands.context.Context, title, url):
        session = db_session.create_session()
        session.add(GuildsToUrls(guild=context.guild.id, title=title, url=url))
        session.commit()

    @staticmethod
    def is_yt_video(url: str) -> bool:
        if re.match(r"(https?://)?(www\.)?youtu\.be|(https?://)?(www\.)?youtube\.com/watch\?v=", url):
            return True
        return False

    @staticmethod
    def is_yt_playlist(url: str) -> bool:
        if re.match(r"(https?://)?(www\.)?youtube\.com/playlist\?", url):
            return True
        return False

    @staticmethod
    def is_yamusic_playlist(url: str) -> bool:
        if re.match(r"(https?://)?(www\.)?music\.yandex\.ru/album/\d+($|/$)", url):
            return True
        return False

    @staticmethod
    def is_yamusic_track(url: str) -> bool:
        if re.match(r"(https?://)?(www\.)?music\.yandex\.ru/album/\d+/track/\d+($|/$)", url):
            return True
        return False

    @staticmethod
    def is_yamusic_user_playlist(url: str) -> bool:
        if re.match(r"(https?://)?(www\.)?music\.yandex\.ru/users/\w+/playlists/\d+($|/$)", url):
            return True
        return False
