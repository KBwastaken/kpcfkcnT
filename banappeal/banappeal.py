import discord
from redbot.core import commands
from redbot.core.bot import Red

class BanAppeal(commands.Cog):
    """Custom Ban Command with Appeal Link."""
    
    def __init__(self, bot: Red):
        self.bot = bot

    @commands.command()
    @commands.guild_only()
    @commands.admin_or_permissions(ban_members=True)
    async def ban(self, ctx: commands.Context, user: discord.Member, *, reason: str = "No reason provided"):
        """Ban a user and send them an appeal link."""
        appeal_link = "https://forms.gle/gR6f9iaaprASRgyP9"
        
        # Create embed message
        embed = discord.Embed(
            title="You have been banned",
            description=f"**Reason:** {reason}\n\n"
                        "You may appeal using the link below. Appeals will be reviewed within 12 hours.\n"
                        "Try rejoining after 24 hours. If still banned, you can reapply in 30 days.",
            color=discord.Color.red()
        )
        embed.add_field(name="Appeal Link", value=f"[Click here to appeal]({appeal_link})", inline=False)
        embed.set_footer(text="Appeals are reviewed by the moderation team.")
        
        try:
            await user.send(embed=embed)  # DM the user with the embed
        except discord.Forbidden:
            await ctx.send(f"Could not DM {user.mention}, but proceeding with the ban.")
        
        await ctx.guild.ban(user, reason=reason)
        await ctx.send(f"{user.mention} has been banned. Reason: {reason}")

async def setup(bot: Red):
    await bot.add_cog(BanAppeal(bot))
