import discord
from redbot.core import commands, Config, checks

class BlockJoins(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=123456789)
        self.config.register_guild(blocking=False, reason="The server has been locked by {author} due to security reasons.")
    
    @commands.command()
    @checks.is_owner()
    async def blockjoins(self, ctx, *, reason: str = None):
        """Toggle blocking new users from joining the server."""
        guild = ctx.guild
        is_blocking = await self.config.guild(guild).blocking()
        
        if is_blocking:
            await self.config.guild(guild).blocking.set(False)
            await ctx.send("🔓 New user joins are now **unblocked**.")
        else:
            reason = reason or f"The server has been locked by {ctx.author} due to security reasons."
            await self.config.guild(guild).blocking.set(True)
            await self.config.guild(guild).reason.set(reason)
            await ctx.send("🔒 New user joins are now **blocked**.")
            
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        guild = member.guild
        is_blocking = await self.config.guild(guild).blocking()
        reason = await self.config.guild(guild).reason()
        
        if is_blocking:
            try:
                dm_embed = discord.Embed(
                    title="Server Locked",
                    description=reason,
                    color=discord.Color.red()
                )
                await member.send(embed=dm_embed)
            except discord.HTTPException:
                pass
            
            await member.kick(reason="Server is locked. Auto-kicked new join.")
