import re

import discord
from discord.ext import commands

from models import Video
from pprint import pprint
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
        if self.is_yt_video(query):
            music_info: dict = await Video(url=query).get_music_info()
        elif self.is_yt_playlist(query):
            # TODO: playlist handler
            pass
        else:
            music_info: dict = await Video(title=query).get_music_info()

        voice_channel: discord.VoiceChannel = context.guild.voice_channels[0]
        voice_client: discord.voice_client.VoiceClient = await voice_channel.connect()
        # async with context.typing(): зачем-то в примерах есть, но сути не меняет
        # пойму, что и как, тогда удалю, либо оставлю
        voice_client.play(discord.FFmpegPCMAudio(music_info['url'], **ffmpeg_options))
        await context.send(f'playing {music_info["title"]}')

    @staticmethod
    def is_yt_video(url: str) -> bool:
        if re.match(r"(https?://)?(www.)?youtu.be|(https?://)?(www.)?youtube.com/watch\?v=", url):
            return True
        return False

    @staticmethod
    def is_yt_playlist(url: str) -> bool:
        if re.match(r"(https?://)?(www.)?youtube.com/playlist\?", url):
            return True
        return False
