import discord
from redbot.core import commands, Config, checks

class BlockInvites(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=987654321)
        self.config.register_guild(block_invites=False)
    
    @commands.command()
    @checks.is_owner()
    async def blockinvites(self, ctx):
        """Toggle blocking new invite links from being created."""
        guild = ctx.guild
        is_blocking_invites = await self.config.guild(guild).block_invites()
        
        if is_blocking_invites:
            await self.config.guild(guild).block_invites.set(False)
            await ctx.send("🔓 Invite creation is now **unblocked**.")
        else:
            await self.config.guild(guild).block_invites.set(True)
            await ctx.send("🔒 Invite creation is now **blocked**.")
    
    @commands.Cog.listener()
    async def on_invite_create(self, invite: discord.Invite):
        guild = invite.guild
        is_blocking_invites = await self.config.guild(guild).block_invites()
        
        if is_blocking_invites:
            try:
                await invite.delete(reason="Auto-deleting invite due to invite block.")
                embed = discord.Embed(
                    title="Invite Blocked",
                    description=f"**Server:** {guild.name}\n"
                                f"**Inviter:** {invite.inviter.mention} ({invite.inviter.id})\n\n"
                                "This server is currently blocking new invites. Your invite has been deleted.",
                    color=discord.Color.red()
                )
                await invite.inviter.send(embed=embed)
            except discord.HTTPException:
                pass
