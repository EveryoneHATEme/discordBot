import asyncio
import logging

import discord
from discord.ext import commands

from utils import Video
from utils.video import youtube_playlist
from utils import ya_music
from utils import Query

from db.models.guilds_to_urls import GuildsToUrls
from db import db_session

logger = logging.getLogger()
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
            await context.send('Please call this command in format:\n'
                               '!play <song name or song video link>')
            return
        voice_channel = self.voice_channel(context)
        if not voice_channel:
            await context.send('Connect to the voice channel first')
            return
        if not self.voice_client(context):
            await self.clear_playlist(context)

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
        elif query.is_yamusic_album():
            album_id = query.get_yamusic_album_id()
            track_list = await ya_music.tracks_in_album(album_id)
            first_link = await ya_music.direct_link(track_list[0]['id'])
            if first_link:
                self.add_to_playlist(context, f"{track_list[0]['artist']} - {track_list[0]['title']}",
                                     first_link, track_list[0]['id'], service='yandex_music')
            for track in track_list[1:]:
                self.add_to_playlist(context, f"{track['artist']} - {track['title']}",
                                     id=track['id'], service='yandex_music')
        elif query.is_yamusic_playlist():
            playlist_info = query.get_yamusic_playlist_and_user_id()
            tracks = await ya_music.tracks_in_playlist(playlist_info["user_id"], playlist_info["playlist_id"])
            first_link = await ya_music.direct_link(tracks[0]['id'])
            if first_link:
                self.add_to_playlist(context, f"{tracks[0]['artist']} - {tracks[0]['title']}",
                                     first_link, tracks[0]['id'], service='yandex_music')
            for track in tracks[1:]:
                self.add_to_playlist(context, f"{track['artist']} - {track['title']}",
                                     id=track['id'], service='yandex_music')
        else:
            music_info: dict = await Video(title=str(query)).get_music_info()
            self.add_to_playlist(context, music_info['title'], music_info['url'], service='youtube')

        voice_client = self.voice_client(context)
        if not voice_client:
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
                else:
                    return
                player = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(link, **ffmpeg_options))
            else:
                player = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(track.url, **ffmpeg_options))
            voice_client.play(player, after=lambda err: self._after_play(context, voice_client, err))
            asyncio.run_coroutine_threadsafe(context.send(f'Playing {track.title}'), self.bot.loop)

    def _after_play(self, context: commands.context.Context,
                    voice_client: discord.voice_client.VoiceClient,
                    error=None):
        if error:
            logger.error(f'Guild: {context.guild.id}, An error occurred while playing: {error}')
            return
        session = db_session.create_session()
        tracks = session.query(GuildsToUrls).filter(GuildsToUrls.guild == context.guild.id).all()
        session.delete(tracks[0])
        session.commit()
        if len(tracks) >= 1:
            self._play(context, voice_client)

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
            for msg in [res_str[y - 1998:y] for y in range(1998, len(res_str) + 1998, 1998)]:
                await context.send(msg)
        else:
            await context.send(f'Playlist is empty')
            await self.disconnect(context)

    @add_track.error
    async def add_track_error(self, context: commands.context.Context, error):
        logger.error(f'Guild: {context.guild.id}, An error occurred:\n{error}')

    @commands.command(aliases=['next', 'skip'])
    async def p_next(self, context: commands.context.Context):
        voice_client = self.voice_client(context)
        voice_client.stop()

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

    def voice_client(self, context: commands.context.Context) -> discord.voice_client.VoiceClient:
        """
        :param context:
        :return: voice_client if exists otherwise None
        """
        voice_channel = self.voice_channel(context)
        if voice_channel and self.bot.user in voice_channel.members:
            return voice_channel.guild.voice_client

    @staticmethod
    def voice_channel(context: commands.context.Context) -> discord.VoiceChannel:
        if context.message.author.voice:
            return context.message.author.voice.channel

    @commands.command('p_clear')
    async def clear_playlist(self, context: commands.context.Context):
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
            await self.clear_playlist(context)
