import discord
from discord import app_commands
from redbot.core import commands
from redbot.core.bot import Red

ALLOWED_GLOBAL_IDS = {1174820638997872721, 1274438209715044415, 690239097150767153}
APPEAL_LINK = "https://forms.gle/gR6f9iaaprASRgyP9"

class ServerBan(commands.Cog):
    """Force-ban or unban users by ID with global option and appeal messaging."""

    def __init__(self, bot: Red):
        self.bot = bot
        self.tree = bot.tree  # Ensure slash commands are in sync

    async def sync_slash_commands(self):
        """Sync all slash commands."""
        self.tree.clear_commands(guild=None)  # Clear old commands
        self.tree.add_command(self.sban)
        self.tree.add_command(self.sunban)
        await self.tree.sync()

    @app_commands.command(name="sban", description="Ban a user by ID with optional global effect and DM appeal info.")
    @app_commands.describe(user_id="The ID of the user to ban", reason="Reason for banning the user")
    @app_commands.choices(
        is_global=[
            app_commands.Choice(name="Yes", value="yes"),
            app_commands.Choice(name="No", value="no")
        ]
    )
    async def sban(self, interaction: discord.Interaction, user_id: str, is_global: str, reason: str = None):
        """Ban a user by ID with optional global effect and DM appeal info."""
        try:
            user_id = int(user_id)  # Convert user_id to an integer
        except ValueError:
            return await interaction.response.send_message("Please provide a valid user ID as an integer.")

        moderator = interaction.user

        # Defer the response to let Discord know you're working on it
        await interaction.response.defer()

        # Convert is_global to boolean from string (Yes = True, No = False)
        is_global = True if is_global.lower() == 'yes' else False

        if is_global and moderator.id not in ALLOWED_GLOBAL_IDS:
            return await interaction.followup.send("You are not authorized to use global bans.")

        target_guilds = self.bot.guilds if is_global else [interaction.guild]

        if not reason:
            reason = f"Action requested by {moderator.name} ({moderator.id})"

        try:
            user = await self.bot.fetch_user(user_id)
            embed = discord.Embed(
                title="You have been banned",
                description=f"**Reason:** {reason}\n\n"
                            f"**Servers:** {'globalban' if is_global and len(target_guilds) > 1 else interaction.guild.name}\n\n"
                            "You may appeal using the link below. Appeals will be reviewed within 12 hours.\n"
                            "Try rejoining after 24 hours. If still banned, you can reapply in 30 days.",
                color=discord.Color.red()
            )
            embed.add_field(name="Appeal Link", value=f"[Click here to appeal]({APPEAL_LINK})", inline=False)
            embed.set_footer(text="Appeals are reviewed by the moderation team.")
            await user.send(embed=embed)
        except discord.HTTPException:
            await interaction.followup.send("Could not DM the user, but proceeding with the ban.")

        ban_errors = []  # List to store errors if any occur during banning

        for guild in target_guilds:
            try:
                is_banned = False
                async for entry in guild.bans():
                    if entry.user.id == user_id:
                        is_banned = True
                        break
                if is_banned:
                    ban_errors.append(f"User is already banned in {guild.name}.")
                    continue

                await guild.ban(discord.Object(id=user_id), reason=reason)
                ban_errors.append(f"Banned {user_id} in {guild.name}.")
            except Exception as e:
                ban_errors.append(f"Failed to ban in {guild.name}: {e}")

        # Send a final response only once, containing all the errors and successes
        if ban_errors:
            await interaction.followup.send("\n".join(ban_errors))
        else:
            # Make sure we indicate the global status in the final message
            global_status = "globally" if is_global else "locally"
            await interaction.followup.send(f"User {user_id} banned {global_status} in all target servers.")

    @app_commands.command(name="sunban", description="Unban a user by ID with optional global effect.")
    @app_commands.describe(user_id="The ID of the user to unban")
    @app_commands.choices(
        is_global=[
            app_commands.Choice(name="Yes", value="yes"),
            app_commands.Choice(name="No", value="no")
        ]
    )
    async def sunban(self, interaction: discord.Interaction, user_id: str, is_global: str):
        """Unban a user by ID with optional global effect."""
        try:
            user_id = int(user_id)  # Convert user_id to an integer
        except ValueError:
            return await interaction.response.send_message("Please provide a valid user ID as an integer.")

        moderator = interaction.user

        # Defer the response to let Discord know you're working on it
        await interaction.response.defer()

        # Convert is_global to boolean from string (Yes = True, No = False)
        is_global = True if is_global.lower() == 'yes' else False

        if is_global and moderator.id not in ALLOWED_GLOBAL_IDS:
            return await interaction.followup.send("You are not authorized to use global unbans.")

        target_guilds = self.bot.guilds if is_global else [interaction.guild]

        unban_errors = []  # List to store errors if any occur during unbanning

        for guild in target_guilds:
            try:
                await guild.unban(discord.Object(id=user_id))
                unban_errors.append(f"Unbanned {user_id} in {guild.name}.")
            except discord.NotFound:
                unban_errors.append(f"User {user_id} was not found in {guild.name}.")
            except Exception as e:
                unban_errors.append(f"Failed to unban in {guild.name}: {e}")

        # Send a final response only once, containing all the errors and successes
        if unban_errors:
            await interaction.followup.send("\n".join(unban_errors))
        else:
            # Make sure we indicate the global status in the final message
            global_status = "globally" if is_global else "locally"
            await interaction.followup.send(f"User {user_id} unbanned {global_status} in all target servers.")
