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
    async def sban(self, ctx: commands.Context, user_id: int, *, reason: str = None):
        """Force-ban a user by ID and send them an appeal link."""
        guild = ctx.guild
        moderator = ctx.author
        appeal_link = "https://forms.gle/gR6f9iaaprASRgyP9"

        if not reason:
            reason = f"Action requested by {moderator.name} ({moderator.id})"

        try:
            user = await self.bot.fetch_user(user_id)
            embed = discord.Embed(
                title="You have been banned",
                description=f"**Reason:** {reason}\n\n"
                            f"**Server:** {guild.name}\n\n"
                            "You may appeal using the link below. Appeals will be reviewed within 12 hours.\n"
                            "Try rejoining after 24 hours. If still banned, you can reapply in 30 days.",
                color=discord.Color.red()
            )
            embed.add_field(name="Appeal Link", value=f"[Click here to appeal]({appeal_link})", inline=False)
            embed.set_footer(text="Appeals are reviewed by the moderation team.")
            
            await user.send(embed=embed)
        except discord.NotFound:
            await ctx.send("User not found. They may have deleted their account.")
        except discord.Forbidden:
            await ctx.send("Could not DM the user, but proceeding with the ban.")
        
        await guild.ban(discord.Object(id=user_id), reason=reason)
        await ctx.send(f"User with ID `{user_id}` has been banned from {guild.name}. Reason: {reason}")

    @commands.command(name="sunban")
    @commands.guild_only()
    @commands.admin_or_permissions(ban_members=True)
    async def sunban(self, ctx: commands.Context, user_id: int, *, reason: str = "Your application has been accepted, you can now rejoin the server using the previous link or by requesting it with the button below"):
        """Unban a user and send them an invite link."""
        guild = ctx.guild
        invite = await guild.text_channels[0].create_invite(max_uses=1, unique=True)
        
        try:
            user = await self.bot.fetch_user(user_id)
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
            
            await user.send(embed=embed, view=view)
        except discord.NotFound:
            await ctx.send("User not found. They may have deleted their account.")
        except discord.Forbidden:
            await ctx.send("Could not DM the user, but they have been unbanned.")
        
        await guild.unban(discord.Object(id=user_id), reason=reason)
        await ctx.send(f"User with ID `{user_id}` has been unbanned from {guild.name}.")

async def setup(bot: Red):
    await bot.add_cog(ServerBan(bot))
