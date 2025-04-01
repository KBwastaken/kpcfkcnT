# rolemanager/rolemanager.py
from redbot.core import commands
import discord
from discord import app_commands
from redbot.core.bot import Red

class RoleManager(commands.Cog):
    """Role Management Cog for Redbot."""

    def __init__(self, bot: Red):
        self.bot = bot
        self.tree = bot.tree

    async def sync_slash_commands(self):
        self.tree.clear_commands(guild=None)  # Clear old commands
        self.tree.add_command(self.assignrole)
        self.tree.add_command(self.unassignrole)
        self.tree.add_command(self.assignmultirole)
        self.tree.add_command(self.unassignmultirole)
        self.tree.add_command(self.massrole)
        self.tree.add_command(self.roleif)
        await self.tree.sync()

    @app_commands.command(name="assignrole", description="Assigns a role to a user.")
    async def assignrole(self, interaction: discord.Interaction, role: discord.Role, user: discord.Member):
        await user.add_roles(role)
        await interaction.response.send_message(f"Assigned {role.name} to {user.mention}.", ephemeral=True)

    @app_commands.command(name="unassignrole", description="Removes a role from a user.")
    async def unassignrole(self, interaction: discord.Interaction, role: discord.Role, user: discord.Member):
        await user.remove_roles(role)
        await interaction.response.send_message(f"Removed {role.name} from {user.mention}.", ephemeral=True)

    @app_commands.command(name="assignmultirole", description="Assign multiple roles to a user (max 6).")
    async def assignmultirole(self, interaction: discord.Interaction, user: discord.Member, roles: str):
        role_list = [role.strip() for role in roles.split(",")][:6]
        discord_roles = [discord.utils.get(interaction.guild.roles, name=role) for role in role_list]
        discord_roles = [role for role in discord_roles if role]
        if not discord_roles:
            return await interaction.response.send_message("No valid roles found.", ephemeral=True)
        await user.add_roles(*discord_roles)
        await interaction.response.send_message(f"Assigned {', '.join([role.name for role in discord_roles])} to {user.mention}.", ephemeral=True)

    @app_commands.command(name="unassignmultirole", description="Removes multiple roles from a user (max 6).")
    async def unassignmultirole(self, interaction: discord.Interaction, user: discord.Member, roles: str):
        role_list = [role.strip() for role in roles.split(",")][:6]
        discord_roles = [discord.utils.get(interaction.guild.roles, name=role) for role in role_list]
        discord_roles = [role for role in discord_roles if role]
        if not discord_roles:
            return await interaction.response.send_message("No valid roles found.", ephemeral=True)
        await user.remove_roles(*discord_roles)
        await interaction.response.send_message(f"Removed {', '.join([role.name for role in discord_roles])} from {user.mention}.", ephemeral=True)

    @app_commands.command(name="massrole", description="Give or remove a role from all members.")
    async def massrole(self, interaction: discord.Interaction, role: discord.Role, action: str):
        if action.lower() not in ["give", "remove"]:
            return await interaction.response.send_message("Invalid action. Use 'give' or 'remove'.", ephemeral=True)
        guild = interaction.guild
        members = guild.members
        if action.lower() == "give":
            for member in members:
                if role not in member.roles:
                    await member.add_roles(role)
            await interaction.response.send_message(f"Gave {role.name} to all members.")
        else:
            for member in members:
                if role in member.roles:
                    await member.remove_roles(role)
            await interaction.response.send_message(f"Removed {role.name} from all members.")

    @app_commands.command(name="roleif", description="Gives roles if a user has a specific role.")
    async def roleif(self, interaction: discord.Interaction, base_role: discord.Role, roles: str):
        role_list = [role.strip() for role in roles.split(",")][:6]
        discord_roles = [discord.utils.get(interaction.guild.roles, name=role) for role in role_list]
        discord_roles = [role for role in discord_roles if role]
        if not discord_roles:
            return await interaction.response.send_message("No valid roles found.", ephemeral=True)
        for member in interaction.guild.members:
            if base_role in member.roles:
                await member.add_roles(*discord_roles)
        await interaction.response.send_message(f"Assigned {', '.join([role.name for role in discord_roles])} to members with {base_role.name}.")
