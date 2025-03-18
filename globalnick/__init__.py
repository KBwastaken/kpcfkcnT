from .globalnick import GlobalNick

def setup(bot):
    bot.add_cog(GlobalNick(bot))
