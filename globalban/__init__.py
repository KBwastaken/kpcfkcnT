from .globalban import GlobalBan

async def setup(bot):
    """Setup function for loading the GlobalBan cog."""
    await bot.add_cog(GlobalBan(bot))  # Asynchronously add the cog to the bot
    print("GlobalBan cog loaded successfully.")
