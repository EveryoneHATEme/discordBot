from discord.ext import commands

from settings import TOKEN
from music import Music


class PeyokaBot(commands.Bot):
    def __init__(self, name='PeyokaPeyoka', command_prefix='!'):
        super().__init__(command_prefix=command_prefix)
        self.name = name

    async def on_ready(self):
        print(f'Connected to the channels: {", ".join([x.name for x in self.guilds])}')


if __name__ == '__main__':
    bot = PeyokaBot()
    bot.add_cog(Music(bot))
    bot.run(TOKEN)