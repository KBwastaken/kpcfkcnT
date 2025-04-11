import discord
from discord.ext import commands

APPEAL_LINK = "https://forms.gle/gR6f9iaaprASRgyP9"

class ServerBan(commands.Cog):
    """Force-ban and unban users by ID with appeal messaging."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="sban")
    @commands.guild_only()
    @commands.has_permissions(ban_members=True)
    async def sban(self, ctx: commands.Context, user_id: int, global_flag: str, *, reason: str = None):
        """Ban a user by ID with optional global effect and send appeal message to the user."""
        moderator = ctx.author
        is_global = global_flag.lower() == "yes"

        # Global logic check
        if is_global:
            ALLOWED_GLOBAL_IDS = {1174820638997872721, 1274438209715044415, 690239097150767153}
            if moderator.id not in ALLOWED_GLOBAL_IDS:
                await ctx.send("You are not authorized to use global bans.")
                return

        target_guilds = self.bot.guilds if is_global else [ctx.guild]

        # Default reason if not provided
        if not reason:
            reason = f"Action requested by {moderator.name} ({moderator.id})"

        # Ban the user in all target guilds (global or local)
        try:
            user = await self.bot.fetch_user(user_id)
            embed = discord.Embed(
                title="You have been banned",
                description=f"**Reason:** {reason}\n\n"
                            f"**Server:** {'Multiple Servers' if is_global else ctx.guild.name}\n\n"
                            "You may appeal using the link below. Appeals will be reviewed within 12 hours.\n"
                            "Try rejoining after 24 hours. If still banned, you can reapply in 30 days.",
                color=discord.Color.red()
            )
            embed.add_field(name="Appeal Link", value=f"[Click here to appeal]({APPEAL_LINK})", inline=False)
            embed.set_footer(text="Appeals are reviewed by the moderation team.")
            await user.send(embed=embed)
        except discord.HTTPException:
            await ctx.send("Could not DM the user, but proceeding with the ban.")

        # Try banning in the target guilds
        for guild in target_guilds:
            is_banned = False
            try:
                async for entry in guild.bans():
                    if entry.user.id == user_id:
                        is_banned = True
                        break
            except Exception as e:
                await ctx.send(f"Error while checking bans in {guild.name}: {e}")
                continue

            if is_banned:
                await ctx.send(f"User is already banned in {guild.name}.")
                continue

            try:
                await guild.ban(discord.Object(id=user_id), reason=reason)
                await ctx.send(f"Banned `{user_id}` in {guild.name}.")
            except Exception as e:
                await ctx.send(f"Failed to ban in {guild.name}: {e}")

    @commands.command(name="sunban")
    @commands.guild_only()
    @commands.has_permissions(ban_members=True)
    async def sunban(self, ctx: commands.Context, user_id: int, *, reason: str = "Your application has been accepted, you can now rejoin the server using the previous link or by requesting it with the button below"):
        """Unban a user by ID and send them an invite link, only in the current server."""
        
        guild = ctx.guild
        invite = await guild.text_channels[0].create_invite(max_uses=1, unique=True)

        # Check if the user is banned in the current guild
        is_banned = False
        try:
            async for entry in guild.bans():
                if entry.user.id == user_id:
                    is_banned = True
                    break
        except Exception as e:
            await ctx.send(f"Error while checking bans: {e}")
            return

        if not is_banned:
            return await ctx.send("User is already unbanned or not found in the ban list.")

        try:
            user = await self.bot.fetch_user(user_id)
            channel = user.dm_channel or await user.create_dm()

            embed = discord.Embed(
                title="You have been unbanned",
                description=f"**Reason:** {reason}\n\n"
                            f"**Server:** {guild.name}\n\n"
                            "Click the button below to rejoin the server.",
                color=discord.Color.green()
            )
            view = discord.ui.View()
            button = discord.ui.Button(label="Rejoin Server", url=invite.url, style=discord.ButtonStyle.link)
            view.add_item(button)

            await channel.send(embed=embed, view=view)

        except discord.NotFound:
            await ctx.send("User not found. They may have deleted their account.")
        except discord.Forbidden:
            await ctx.send("Could not DM the user.")

        # Unban the user in the current guild
        try:
            await guild.unban(discord.Object(id=user_id), reason=reason)
            await ctx.send(f"User with ID `{user_id}` has been unbanned from {guild.name}.")
        except Exception as e:
            await ctx.send(f"Failed to unban user `{user_id}` in {guild.name}: {e}")

async def setup(bot: commands.Bot):
    await bot.add_cog(ServerBan(bot))
