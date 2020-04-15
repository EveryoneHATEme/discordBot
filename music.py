import discord
from discord.ext import commands

from models import Video

ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn -nostats -loglevel 0'
}


class Music(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command('play')
    async def play(self, context: commands.context.Context, url: str):
        music_url: str = await Video(url=url).get_music_url()
        voice_channel: discord.VoiceChannel = context.guild.voice_channels[0]
        voice_client: discord.voice_client.VoiceClient = await voice_channel.connect()
        # async with context.typing(): зачем-то в примерах есть, но сути не меняет
        # пойму, что и как, тогда удалю, либо оставлю
        voice_client.play(discord.FFmpegPCMAudio(music_url, **ffmpeg_options))
        await context.send(f'playing {url}')
