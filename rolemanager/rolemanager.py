# rolemanager/rolemanager.py
from redbot.core import commands
import discord
import asyncio
from redbot.core.commands import has_permissions
from redbot.core.bot import Red

class RoleManager(commands.Cog):
    """Role Management Cog for Redbot."""

    def __init__(self, bot: Red):
        self.bot = bot

    @commands.command()
    @commands.guild_only()
    @has_permissions(manage_roles=True)
    async def assignrole(self, ctx, role: discord.Role):
        """Assigns a role to the user."""
        await ctx.author.add_roles(role)
        await ctx.send(f"Assigned {role.name} to {ctx.author.mention}.")

    @commands.command()
    @commands.guild_only()
    @has_permissions(manage_roles=True)
    async def unassignrole(self, ctx, role: discord.Role):
        """Removes a role from the user."""
        await ctx.author.remove_roles(role)
        await ctx.send(f"Removed {role.name} from {ctx.author.mention}.")

    @commands.command()
    @commands.guild_only()
    @has_permissions(manage_roles=True)
    async def assignmultirole(self, ctx, *roles: discord.Role):
        """Assign multiple roles at once (max 6)."""
        if len(roles) > 6:
            return await ctx.send("You can only assign up to 6 roles at a time.")
        await ctx.author.add_roles(*roles)
        await ctx.send(f"Assigned {', '.join([role.name for role in roles])} to {ctx.author.mention}.")

    @commands.command()
    @commands.guild_only()
    @has_permissions(manage_roles=True)
    async def massrole(self, ctx, role: discord.Role, action: str):
        """Give or remove a role from all members."""
        if action.lower() not in ["give", "remove"]:
            return await ctx.send("Invalid action. Use 'give' or 'remove'.")
        guild = ctx.guild
        members = guild.members
        if action.lower() == "give":
            for member in members:
                if role not in member.roles:
                    await member.add_roles(role)
            await ctx.send(f"Gave {role.name} to all members.")
        else:
            for member in members:
                if role in member.roles:
                    await member.remove_roles(role)
            await ctx.send(f"Removed {role.name} from all members.")

    @commands.command()
    @commands.guild_only()
    @has_permissions(manage_roles=True)
    async def roleif(self, ctx, base_role: discord.Role, *given_roles: discord.Role):
        """Gives roles if a user has a specific role."""
        if len(given_roles) > 6:
            return await ctx.send("You can only assign up to 6 roles at a time.")
        for member in ctx.guild.members:
            if base_role in member.roles:
                await member.add_roles(*given_roles)
        await ctx.send(f"Assigned {', '.join([role.name for role in given_roles])} to members with {base_role.name}.")
