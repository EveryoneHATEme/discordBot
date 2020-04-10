import os
import discord

from settings import TOKEN
from download_handler import Downloader


class BotClient(discord.Client):
    def __init__(self):
        super().__init__()
        self.downloader = Downloader()

    async def on_message(self, message: discord.message.Message):
        await self.wait_until_ready()

        if message.author == self.user:
            return
        content: str = message.content.strip()
        if not content.startswith('!'):
            return

        command, *args = content.split()
        if command[1:] == 'play':
            self.downloader.download_audio(args[0])
            filename = [x for x in os.listdir() if x.split('.')[-1] == 'mp3'][0]

            channel = message.author.guild.voice_channels[0]
            voice_client: discord.VoiceClient = await channel.connect(timeout=60, reconnect=True)
            voice_client.play(discord.FFmpegPCMAudio(filename))


if __name__ == '__main__':
    bot = BotClient()
    bot.run(TOKEN)
