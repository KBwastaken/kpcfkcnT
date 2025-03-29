# __init__.py
from .globalban import GlobalBan

def setup(bot):
    bot.add_cog(GlobalBan(bot))  # Use the correct method to load the cog
