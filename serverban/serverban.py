import discord
from redbot.core import commands
from redbot.core.bot import Red

class ServerBan(commands.Cog):
    """Force-ban users by ID and send an appeal message."""
    
    def __init__(self, bot: Red):
        self.bot = bot

    @commands.command()
    @commands.guild_only()
    @commands.admin_or_permissions(ban_members=True)
    async def serverban(self, ctx: commands.Context, user_id: int, *, reason: str = None):
        """Force-ban a user by ID and send them an appeal link."""
        guild = ctx.guild
        moderator = ctx.author
        appeal_link = "https://forms.gle/gR6f9iaaprASRgyP9"

        # Default reason if none is provided
        if not reason:
            reason = f"Action requested by {moderator.name} ({moderator.id})"

        try:
            user = await self.bot.fetch_user(user_id)
            embed = discord.Embed(
                title="You have been banned",
                description=f"**Reason:** {reason}\n\n"
                            "You may appeal using the link below. Appeals will be reviewed within 12 hours.\n"
                            "Try rejoining after 24 hours. If still banned, you can reapply in 30 days.",
                color=discord.Color.red()
            )
            embed.add_field(name="Appeal Link", value=f"[Click here to appeal]({appeal_link})", inline=False)
            embed.set_footer(text="Appeals are reviewed by the moderation team.")
            
            await user.send(embed=embed)  # DM the user
        except discord.NotFound:
            await ctx.send("User not found. They may have deleted their account.")
        except discord.Forbidden:
            await ctx.send("Could not DM the user, but proceeding with the ban.")
        
        # Force-ban the user by ID
        await guild.ban(discord.Object(id=user_id), reason=reason)
        await ctx.send(f"User with ID `{user_id}` has been banned. Reason: {reason}")

async def setup(bot: Red):
    await bot.add_cog(ServerBan(bot))
