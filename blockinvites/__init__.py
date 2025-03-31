from .blockinvites import blockinvites

async def setup(bot):
    await bot.add_cog(blockinvites(bot))
