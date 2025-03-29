"""TeamRole cog for Red Discord Bot."""  
from .core import TeamTest  

async def setup(bot):  
    await bot.add_cog(TeamTest(bot))
