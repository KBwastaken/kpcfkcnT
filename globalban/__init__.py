from .globalban_cog import GlobalBanCog

async def setup(bot):
    await bot.add_cog(GlobalBanCog(bot))
