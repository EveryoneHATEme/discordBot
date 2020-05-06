import re
import asyncio

import discord
from discord.ext import commands

from utils import Video
from utils.video import youtube_playlist
from utils import ya_music
from utils import Query
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
    async def add_track(self, context: commands.context.Context, *args):
        query = Query(args)
        if not query:
            await context.send('Empty request')
            await context.send('Please call this command in format'
                               ' !play <song name or song video link>')
            return

        if not self.voice_client(context):
            self.clear_playlist(context)

        if query.is_yt_video():
            music_info: dict = await Video(url=str(query)).get_music_info()
            self.add_to_playlist(context, music_info['title'], music_info['url'], service='youtube')
        elif query.is_yt_playlist():
            videos = await youtube_playlist(str(query))
            music_info: dict = await Video(video_id=videos[0][0]).get_music_info()
            self.add_to_playlist(context, music_info['title'], music_info['url'])
            for id_, title in videos:
                self.add_to_playlist(context, title, id=id_, service='youtube')
        elif query.is_yamusic_track():
            track_id = query.get_yamusic_track_id()
            track = await ya_music.track_info(track_id)
            link = await ya_music.direct_link(track_id)
            if link and track:
                self.add_to_playlist(context, track["artist"] + ' - ' + track["title"],
                                     link, service='yandex_music')
        elif query.is_yamusic_playlist():
            album_id = query.get_yamusic_album_id()
            track_list = await ya_music.tracks_in_album(album_id)
            first_link = await ya_music.direct_link(track_list[0]['id'])
            if first_link:
                self.add_to_playlist(context, f"{track_list[0]['artist']} - {track_list[0]['title']}",
                                     first_link, track_list[0]['id'], service='yandex_music')
            for track in track_list[1:]:
                self.add_to_playlist(context, f"{track['artist']} - {track['title']}",
                                     id=track['id'], service='yandex_music')
        else:
            music_info: dict = await Video(title=str(query)).get_music_info()
            self.add_to_playlist(context, music_info['title'], music_info['url'], service='youtube')
        voice_client = self.voice_client(context)
        if not voice_client:
            voice_channel = self.voice_channel(context)
            voice_client: discord.voice_client.VoiceClient = await voice_channel.connect()
        if not voice_client.is_playing() and not voice_client.is_paused():
            self._play(context, voice_client)

    def _play(self, context: commands.context.Context, voice_client: discord.voice_client.VoiceClient):
        session = db_session.create_session()
        track = session.query(GuildsToUrls).filter(GuildsToUrls.guild == context.guild.id).first()
        if not track:
            asyncio.run_coroutine_threadsafe(self.disconnect(context, 'Playlist is empty'), self.bot.loop)
            return
        if not voice_client.is_playing() and not voice_client.is_paused():
            if track.url is None:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                if track.service == 'youtube':
                    link = loop.run_until_complete(Video(video_id=track.track_id).get_music_info())['url']
                elif track.service == 'yandex_music':
                    link = loop.run_until_complete(ya_music.direct_link(track.track_id))
                player = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(link, **ffmpeg_options))
            else:
                player = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(track.url, **ffmpeg_options))
            voice_client.play(player, after=lambda err: self._after_play(context, voice_client, err))
            asyncio.run_coroutine_threadsafe(context.send(f'Playing {track.title}'), self.bot.loop)

    def _after_play(self, context: commands.context.Context,
                    voice_client: discord.voice_client.VoiceClient,
                    error=None):
        if error:
            print(f'An error occurred while playing: {error}')
            return
        session = db_session.create_session()
        track = session.query(GuildsToUrls).filter(GuildsToUrls.guild == context.guild.id).first()
        session.delete(track)
        session.commit()
        self._play(context, voice_client)

    @add_track.error
    async def add_track_error(self, context, error):
        print(f'An error occurred:\n{error}')

    @commands.command(aliases=['next', 'skip'])
    async def p_next(self, context: commands.context.Context):
        voice_client = self.voice_client(context)
        voice_client.stop()

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

    def clear_playlist(self, context: commands.context.Context):
        voice_channel = self.voice_channel(context)
        session = db_session.create_session()
        result = session.query(GuildsToUrls).filter(GuildsToUrls.guild == voice_channel.guild.id).all()
        for instance in result:
            session.delete(instance)
            session.commit()

    @staticmethod
    def add_to_playlist(context: commands.context.Context, title, url=None, id=None, service=None):
        session = db_session.create_session()
        session.add(GuildsToUrls(guild=context.guild.id, title=title, url=url, track_id=id, service=service))
        session.commit()

    @commands.command(aliases=['stop', 'leave', 'dc'])
    async def disconnect(self, context: commands.context.Context, message: str = None):
        voice_client = self.voice_client(context)
        if voice_client:
            if message is not None:
                await context.send(message)
            await voice_client.disconnect()
            self.clear_playlist(context)
