from redbot.core import commands
import discord

class BotWhitelist(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.whitelist = set()  # Store whitelisted bot IDs

    @commands.command()
    @commands.is_owner()  # Ensures that only the bot owner can use this command
    async def whitelistbot(self, ctx, bot_id: int):
        """Add or remove a bot to/from the whitelist"""
        # We add the bot to the whitelist regardless of whether it's in the server or not
        if bot_id in self.whitelist:
            self.whitelist.remove(bot_id)
            await ctx.send(f"Bot with ID {bot_id} has been removed from the whitelist.")
        else:
            self.whitelist.add(bot_id)
            await ctx.send(f"Bot with ID {bot_id} has been added to the whitelist.")
        
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """Automatically kicks unwhitelisted bots upon joining"""
        if member.bot:  # Check if the member is a bot
            if member.id not in self.whitelist:
                # If the bot is not in the whitelist, kick it
                await member.kick(reason="Bot not whitelisted.")
                # Send an asynchronous message to the system channel if it exists
                if member.guild.system_channel:
                    await member.guild.system_channel.send(f"A bot ({member.name}) has been kicked because it is not on the whitelist.")
            else:
                # Log the joining of a whitelisted bot
                print(f"Whitelisted bot {member.name} joined the server.")

# Setup function to add the cog to the bot
async def setup(bot):
    await bot.add_cog(BotWhitelist(bot))  # Await add_cog to avoid the warning/error
