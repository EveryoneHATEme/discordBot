import re
from pprint import pprint

import discord
from discord.ext import commands

from utils import Video
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
        query = " ".join(args).strip()
        if not query:
            await self.play_next(context)
            return
        if self.is_yt_video(query):
            music_info: dict = await Video(url=query).get_music_info()
            self.add_to_playlist(context, music_info['title'], music_info['url'])
        elif self.is_yt_playlist(query):
            # TODO: playlist handler
            pass
        else:
            music_info: dict = await Video(title=query).get_music_info()
            self.add_to_playlist(context, music_info['title'], music_info['url'])
        await self.__play(context)

    async def __play(self, context: commands.context.Context):
        voice_channel = self.voice_channel(context)
        session = db_session.create_session()
        result = session.query(GuildsToUrls).filter(GuildsToUrls.guild == voice_channel.guild.id).all()
        if not result:
            await context.send(f'Playlist is empty')
            return
        voice_client = self.voice_client(context)
        if not voice_client:
            voice_client: discord.voice_client.VoiceClient = await voice_channel.connect()
        if not voice_client.is_playing():
            voice_client.play(discord.FFmpegPCMAudio(result[0].url, **ffmpeg_options))
            await context.send(f'Playing {result[0].title}')

    @commands.command('next')
    async def play_next(self, context: commands.context.Context):
        voice_client = self.voice_client(context)
        voice_channel = self.voice_channel(context)
        if not voice_client:
            voice_client: discord.voice_client.VoiceClient = await voice_channel.connect()
        session = db_session.create_session()
        result = session.query(GuildsToUrls).filter(GuildsToUrls.guild == voice_channel.guild.id).all()
        if result:
            session.delete(result[0])
            session.commit()
            voice_client.stop()
        await self.__play(context)

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