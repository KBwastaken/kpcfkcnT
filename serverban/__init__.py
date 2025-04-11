from redbot.core.bot import Red
from .serverban import ServerBan

async def setup(bot: Red):
    cog = ServerBan(bot)
    await bot.add_cog(cog)
    await cog.sync_slash_commands()
