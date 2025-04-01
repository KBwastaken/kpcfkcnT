# rolemanager/__init__.py
from .rolemanager import RoleManager

async def setup(bot):
    await bot.add_cog(RoleManager(bot))
