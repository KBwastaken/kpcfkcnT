from .globalban import GlobalBan

def setup(bot):
    # This is the entry point to add the cog to the bot
    bot.add_cog(GlobalBan(bot))
