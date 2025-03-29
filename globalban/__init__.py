# __init__.py
from .globalban import GlobalBan

async def setup(bot):
    cog = GlobalBan(bot)
    await bot.add_cog(cog)  # Adding the cog asynchronously
