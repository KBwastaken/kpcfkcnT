from redbot.core import commands
import discord

class BotWhitelist(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.whitelist = set()  # Store whitelisted bot IDs

    @commands.command()
    async def whitelistbot(self, ctx, bot_id: int):
        """Add or remove a bot to/from the whitelist"""
        bot_user = self.bot.get_user(bot_id)
        if bot_user:
            if bot_id in self.whitelist:
                self.whitelist.remove(bot_id)
                await ctx.send(f"{bot_user.mention} has been removed from the whitelist.")
            else:
                self.whitelist.add(bot_id)
                await ctx.send(f"{bot_user.mention} has been added to the whitelist.")
        else:
            await ctx.send("Could not find the bot with the given ID.")

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """Automatically kicks unwhitelisted bots upon joining"""
        if member.bot:  # Check if the member is a bot
            if member.id not in self.whitelist:
                await member.kick(reason="Bot not whitelisted.")
                # Send an asynchronous message to the system channel if it exists
                if member.guild.system_channel:
                    await member.guild.system_channel.send(f"A bot ({member.name}) has been kicked because it is not on the whitelist.")
            else:
                # This log also runs asynchronously when a bot is whitelisted and joins
                print(f"Whitelisted bot {member.name} joined the server.")

# Setup function to add the cog to the bot
def setup(bot):
    bot.add_cog(BotWhitelist(bot))  # This should remain synchronous
