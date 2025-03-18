import discord
from redbot.core import commands
from redbot.core.commands import Context
from typing import Optional


class GlobalNick(commands.Cog):
    """A cog for globally changing a user's nickname across all servers."""

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def globalnick(self, ctx: Context, user: Optional[discord.Member] = None, *, nickname: str = None):
        """Globally change a user's nickname across all servers the bot is in."""
        if user is None:
            user = ctx.author  # If no user is provided, use the command executor.

        if nickname is None:
            await ctx.send("Please provide a nickname.")
            return

        # Iterate through all the guilds the bot is in
        for guild in self.bot.guilds:
            # Ensure the bot has the necessary permissions
            member = guild.get_member(user.id)
            if member is not None:
                try:
                    # Change the user's nickname globally
                    await member.edit(nick=nickname)
                    await ctx.send(f"Successfully changed the nickname of {user} to `{nickname}` in {guild.name}.")
                except discord.Forbidden:
                    await ctx.send(f"Could not change nickname for {user} in {guild.name}, missing permissions.")
                except discord.HTTPException as e:
                    await ctx.send(f"Failed to change nickname for {user} in {guild.name}: {e}")
            else:
                await ctx.send(f"{user} is not a member of {guild.name}.")

    @globalnick.error
    async def globalnick_error(self, ctx: Context, error: Exception):
        """Handles errors that occur during the .globalnick command."""
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("You do not have permission to use this command. Only administrators can use it.")
        elif isinstance(error, commands.CommandInvokeError):
            await ctx.send("An error occurred while trying to change the nickname.")
        else:
            raise error
