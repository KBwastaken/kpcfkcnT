import discord
from redbot.core import commands
from redbot.core.bot import Red

ALLOWED_GLOBAL_IDS = {1174820638997872721, 1274438209715044415, 690239097150767153}
APPEAL_LINK = "https://forms.gle/gR6f9iaaprASRgyP9"

class ServerBan(commands.Cog):
    """Force-ban or unban users by ID with global option and appeal messaging."""

    def __init__(self, bot: Red):
        self.bot = bot

    @commands.command(name="sban")
    @commands.guild_only()
    @commands.admin_or_permissions(ban_members=True)
    async def sban(self, ctx: commands.Context, user_id: int, global_flag: str, *, reason: str = None):
        """Ban a user by ID with optional global effect and DM appeal info."""
        moderator = ctx.author
        is_global = global_flag.lower() == "yes"

        if is_global and moderator.id not in ALLOWED_GLOBAL_IDS:
            await ctx.send("You are not authorized to use global bans.")
            return

        target_guilds = self.bot.guilds if is_global else [ctx.guild]

        # Adjust the reason for global bans
        if not reason:
            reason = f"Action requested by {moderator.name} ({moderator.id})"
        
        # Prepare the embed with reason and the server details
        embed = discord.Embed(
            title="You have been banned",
            description=f"**Reason:** {reason}\n\n"
                        f"**Servers:** {'Multiple Servers (globalban)' if is_global else ctx.guild.name}\n\n"
                        "You may appeal using the link below. Appeals will be reviewed within 12 hours.\n"
                        "Try rejoining after 24 hours. If still banned, you can reapply in 30 days.",
            color=discord.Color.red()
        )
        embed.add_field(name="Appeal Link", value=f"[Click here to appeal]({APPEAL_LINK})", inline=False)
        embed.set_footer(text="Appeals are reviewed by the moderation team.")

        try:
            user = await self.bot.fetch_user(user_id)
            await user.send(embed=embed)
        except discord.HTTPException:
            await ctx.send("Could not DM the user, but proceeding with the ban.")

        # Process banning in target guilds
        for guild in target_guilds:
            try:
                is_banned = False
                async for entry in guild.bans():
                    if entry.user.id == user_id:
                        is_banned = True
                        break
                if is_banned:
                    await ctx.send(f"User is already banned in {guild.name}.")
                    continue

                await guild.ban(discord.Object(id=user_id), reason=reason)
                await ctx.send(f"Banned `{user_id}` in {guild.name}.")
            except Exception as e:
                await ctx.send(f"Failed to ban in {guild.name}: {e}")

    @commands.command(name="sunban")
    @commands.guild_only()
    @commands.admin_or_permissions(ban_members=True)
    async def sunban(self, ctx: commands.Context, user_id: int, global_flag: str, *, reason: str = None):
        """Unban a user by ID with optional global scope and DM rejoin invite."""
        moderator = ctx.author
        is_global = global_flag.lower() == "yes"

        if is_global and moderator.id not in ALLOWED_GLOBAL_IDS:
            await ctx.send("You are not authorized to use global unbans.")
            return

        if not reason:
            reason = "Your application has been accepted, you can now rejoin the server using the previous link or by requesting it with the button below."

        successful_unbans = []
        failed_guilds = []
        skipped_unbans = []

        # Logic for global unbanning (across all servers the bot is in)
        if is_global:
            target_guilds = self.bot.guilds  # Get all the guilds the bot is in
        else:
            target_guilds = [ctx.guild]  # Only target the current server if not global

        # Loop through each server the bot is in and check if the user is banned
        for guild in target_guilds:
            try:
                is_banned = False
                async for entry in guild.bans():
                    if entry.user.id == user_id:
                        is_banned = True
                        break
            except Exception as e:
                failed_guilds.append(f"{guild.name} (error checking ban: {e})")
                continue

            if is_banned:
                try:
                    await guild.unban(discord.Object(id=user_id), reason=reason)
                    successful_unbans.append(guild)
                    await ctx.send(f"Unbanned `{user_id}` in {guild.name}.")
                except Exception as e:
                    failed_guilds.append(f"{guild.name} (unban error: {e})")
            else:
                skipped_unbans.append(guild.name)

        # After processing, send a summary of the unban attempts
        if successful_unbans:
            try:
                user = await self.bot.fetch_user(user_id)
                channel = user.dm_channel or await user.create_dm()

                embed = discord.Embed(
                    title="You have been unbanned",
                    description=f"**Reason:** {reason}\n\n"
                                f"**Servers:** {', '.join(g.name for g in successful_unbans)}\n\n"
                                "Click the button(s) below to rejoin the server(s).",
                    color=discord.Color.green()
                )
                view = discord.ui.View()

                # Add a button for each successful unban with an invite link
                for g in successful_unbans:
                    try:
                        text_channels = [c for c in g.text_channels if c.permissions_for(g.me).create_instant_invite]
                        if not text_channels:
                            continue
                        invite = await text_channels[0].create_invite(max_uses=1, unique=True)
                        button = discord.ui.Button(label=f"Rejoin {g.name}", url=invite.url, style=discord.ButtonStyle.link)
                        view.add_item(button)
                    except Exception as e:
                        await ctx.send(f"Error generating invite for {g.name}: {e}")

                # Send the embed with the invite buttons
                await channel.send(embed=embed, view=view)
            except discord.HTTPException:
                await ctx.send("Could not DM the user, but they were unbanned.")

        # Summary message of the unban result
        summary = ""
        if successful_unbans:
            summary += f"✅ Successfully unbanned from: {', '.join(g.name for g in successful_unbans)}\n"
        if skipped_unbans:
            summary += f"⚠️ Already unbanned or not banned in: {', '.join(skipped_unbans)}\n"
        if failed_guilds:
            summary += f"❌ Failed in: {', '.join(failed_guilds)}"

        if summary:
            await ctx.send(f"**Unban Summary:**\n{summary}")

async def setup(bot: Red):
    await bot.add_cog(ServerBan(bot))
