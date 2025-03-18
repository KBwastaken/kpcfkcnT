import discord
from redbot.core import commands
from redbot.core import checks
from redbot.core.bot import Red
from discord.ext import commands

class GlobalNick(commands.Cog):
    """A cog that allows administrators to change the global nickname of a user."""

    def __init__(self, bot: Red):
        self.bot = bot

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def globalnick(self, ctx: commands.Context, member: discord.Member = None, *, nick: str = None):
        """Change the nickname of a user globally. Only admins can use this command."""
        if member is None:
            member = ctx.author  # If no user is provided, use the command executor's user

        if nick is None:
            await ctx.send("You need to provide a new nickname.")
            return

        try:
            # Attempt to change the nickname
            await member.edit(nick=nick)
            await ctx.send(f"Successfully changed the nickname of {member.mention} to {nick}")
        except discord.Forbidden:
            await ctx.send(f"I don't have permission to change {member.mention}'s nickname.")
        except discord.HTTPException as e:
            await ctx.send(f"An error occurred while trying to change {member.mention}'s nickname: {e}")

    @globalnick.error
    async def globalnick_error(self, ctx: commands.Context, error: Exception):
        """Handle errors for the globalnick command."""
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("You do not have permission to use this command.")
        elif isinstance(error, commands.CommandInvokeError):
            await ctx.send(f"An error occurred while executing the command: {error}")
        else:
            await ctx.send(f"Unexpected error: {error}")

# The setup function that Redbot needs to load the cog.
def setup(bot: Red):
    bot.add_cog(GlobalNick(bot))
