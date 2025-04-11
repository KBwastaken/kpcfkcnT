import discord
from redbot.core import commands
from redbot.core.bot import Red

class ServerBan(commands.Cog):
    """Force-ban users by ID and send an appeal message. Also supports unbanning."""

    def __init__(self, bot: Red):
        self.bot = bot

    @commands.command(name="sban")
    @commands.guild_only()
    @commands.admin_or_permissions(ban_members=True)
    async def sban(
        self, ctx: commands.Context, user_id: int, reason: str = None, global_ban: str = "no"
    ):
        """Force-ban a user by ID and send them an appeal link. Optionally do it globally."""
        moderator = ctx.author
        appeal_link = "https://forms.gle/gR6f9iaaprASRgyP9"
        if not reason or reason.lower() in ("yes", "no"):
            reason = f"Action requested by {moderator.name} ({moderator.id})"

        global_ban = global_ban.lower() == "yes"

        try:
            user = await self.bot.fetch_user(user_id)
            embed = discord.Embed(
                title="You have been banned",
                description=f"**Reason:** {reason}\n\n"
                            f"**Server:** Multiple" if global_ban else f"**Server:** {ctx.guild.name}\n\n"
                            "You may appeal using the link below. Appeals will be reviewed within 12 hours.\n"
                            "Try rejoining after 24 hours. If still banned, you can reapply in 30 days.",
                color=discord.Color.red()
            )
            embed.add_field(name="Appeal Link", value=f"[Click here to appeal]({appeal_link})", inline=False)
            embed.set_footer(text="Appeals are reviewed by the moderation team.")
            await user.send(embed=embed)
        except discord.HTTPException:
            await ctx.send("Could not DM the user, but proceeding with the ban.")

        # Apply ban(s)
        target_guilds = self.bot.guilds if global_ban else [ctx.guild]
        for guild in target_guilds:
            try:
                async for ban_entry in guild.bans():
                    if ban_entry.user.id == user_id:
                        await ctx.send(f"User is already banned in {guild.name}.")
                        continue
                await guild.ban(discord.Object(id=user_id), reason=reason)
                await ctx.send(f"Banned `{user_id}` in {guild.name}.")
            except Exception as e:
                await ctx.send(f"Failed to ban in {guild.name}: {e}")

    @commands.command(name="sunban")
    @commands.guild_only()
    @commands.admin_or_permissions(ban_members=True)
    async def sunban(
        self, ctx: commands.Context, user_id: int,
        reason: str = "Your application has been accepted, you can now rejoin the server using the previous link or by requesting it with the button below",
        global_unban: str = "no"
    ):
        """Unban a user and optionally do it globally."""
        global_unban = global_unban.lower() == "yes"
        target_guilds = self.bot.guilds if global_unban else [ctx.guild]

        successful_unbans = []
        for guild in target_guilds:
            is_banned = False
            try:
                async for ban_entry in guild.bans():
                    if ban_entry.user.id == user_id:
                        is_banned = True
                        break
            except Exception:
                continue

            if not is_banned:
                await ctx.send(f"User is already unbanned or not found in {guild.name}.")
                continue

            try:
                await guild.unban(discord.Object(id=user_id), reason=reason)
                successful_unbans.append(guild.name)
                await ctx.send(f"Unbanned `{user_id}` in {guild.name}.")
            except Exception as e:
                await ctx.send(f"Failed to unban in {guild.name}: {e}")

        if successful_unbans:
            try:
                user = await self.bot.fetch_user(user_id)
                channel = user.dm_channel or await user.create_dm()
                invite = await ctx.guild.text_channels[0].create_invite(max_uses=1, unique=True)

                embed = discord.Embed(
                    title="You have been unbanned",
                    description=f"**Reason:** {reason}\n\n"
                                f"**Server:** {ctx.guild.name if not global_unban else 'Multiple'}\n\n"
                                "Click the button below to rejoin the server.",
                    color=discord.Color.green()
                )
                view = discord.ui.View()
                button = discord.ui.Button(label="Rejoin Server", url=invite.url, style=discord.ButtonStyle.link)
                view.add_item(button)

                await channel.send(embed=embed, view=view)
            except discord.HTTPException:
                await ctx.send("Could not DM the user, but they were unbanned.")
        else:
            await ctx.send("No unbans were successful.")

async def setup(bot: Red):
    await bot.add_cog(ServerBan(bot))
