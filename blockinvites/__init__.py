from .blockinvites import Blockinvites

async def setup(bot):
    await bot.add_cog(Blockinvites(bot))
