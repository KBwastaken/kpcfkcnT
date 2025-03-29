from .botwhitelist import BotWhitelist

__red_end_user_data_statement__ = "This cog does not store any persistent data."

def setup(bot):
    bot.add_cog(BotWhitelist(bot))  # This is a synchronous call
