import discord
from redbot.core import commands, Config, checks
from redbot.core.bot import Red
from discord.ui import View, Button

class GlobalBan(commands.Cog):
    """A cog for handling global bans."""

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=1234567890, force_registration=True)
        self.config.register_global(globalbans={}, log_channel=None)
        self.config.register_guild(allowed_role=None)
    
    @commands.command()
    @commands.admin_or_permissions(ban_members=True)
    async def globalban(self, ctx, user: discord.User, *, reason: str):
        """Globally ban a user from all affiliated servers."""
        globalbans = await self.config.globalbans()
        
        if str(user.id) in globalbans:
            return await ctx.send(f"{user.mention} is already globally banned.")

        globalbans[str(user.id)] = {
            "username": str(user),
            "userid": user.id,
            "server": ctx.guild.name,
            "executor": str(ctx.author),
            "executor_id": ctx.author.id,
            "reason": reason
        }
        
        await self.config.globalbans.set(globalbans)
        
        for guild in self.bot.guilds:
            try:
                await guild.ban(user, reason=f"Globally banned: {reason}")
            except discord.Forbidden:
                continue
            except discord.NotFound:
                continue

        embed = discord.Embed(title="Global Ban Issued", color=discord.Color.red())
        embed.add_field(name="Member", value=f"{user} ({user.id})", inline=False)
        embed.add_field(name="Server", value=ctx.guild.name, inline=True)
        embed.add_field(name="Executor", value=f"{ctx.author} ({ctx.author.id})", inline=True)
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.set_footer(text="KCN Network API | Global Ban")
        
        view = BanApprovalView(user.id, ctx)
        log_channel_id = await self.config.log_channel()
        if log_channel_id:
            log_channel = self.bot.get_channel(log_channel_id)
            if log_channel:
                await log_channel.send(embed=embed, view=view)
        else:
            await ctx.send(embed=embed, view=view)
    
    @commands.command()
    @commands.is_owner()
    async def globalbansync(self, ctx):
        """Sync global bans across all servers."""
        globalbans = await self.config.globalbans()
        for user_id, ban_data in globalbans.items():
            user = await self.bot.fetch_user(int(user_id))
            for guild in self.bot.guilds:
                try:
                    await guild.ban(user, reason=f"Global ban sync: {ban_data['reason']}")
                except discord.Forbidden:
                    continue
                except discord.NotFound:
                    continue
        await ctx.send("Global bans have been synced across all servers.")
    
    @commands.command()
    @commands.admin_or_permissions(ban_members=True)
    async def globalunban(self, ctx, user_id: int):
        """Unban a globally banned user."""
        globalbans = await self.config.globalbans()
        
        if str(user_id) not in globalbans:
            return await ctx.send("User is not globally banned.")
        
        del globalbans[str(user_id)]
        await self.config.globalbans.set(globalbans)
        
        for guild in self.bot.guilds:
            try:
                user = await self.bot.fetch_user(user_id)
                await guild.unban(user)
            except discord.NotFound:
                continue
            except discord.Forbidden:
                continue

        await ctx.send(f"User {user_id} has been globally unbanned.")

class BanApprovalView(View):
    def __init__(self, user_id: int, ctx):
        super().__init__(timeout=300)
        self.user_id = user_id
        self.ctx = ctx

        self.approve_button = Button(label="Approve", style=discord.ButtonStyle.green, disabled=False)
        self.approve_button.callback = self.approve
        
        self.deny_button = Button(label="Deny", style=discord.ButtonStyle.red, disabled=False)
        self.deny_button.callback = self.deny
        
        self.escalate_button = Button(label="Escalate to Cybersecurity", style=discord.ButtonStyle.blurple, disabled=False)
        self.escalate_button.callback = self.escalate
        
        self.add_item(self.approve_button)
        self.add_item(self.deny_button)
        self.add_item(self.escalate_button)
    
    async def approve(self, interaction: discord.Interaction):
        self.approve_button.disabled = True
        self.deny_button.disabled = True
        await interaction.response.edit_message(content=f"Approved by {interaction.user.mention}", view=self)
    
    async def deny(self, interaction: discord.Interaction):
        self.approve_button.disabled = True
        self.deny_button.disabled = True
        globalbans = await self.ctx.cog.config.globalbans()
        
        if str(self.user_id) in globalbans:
            del globalbans[str(self.user_id)]
            await self.ctx.cog.config.globalbans.set(globalbans)
        
        for guild in self.ctx.bot.guilds:
            try:
                user = await self.ctx.bot.fetch_user(self.user_id)
                await guild.unban(user)
            except discord.NotFound:
                continue
            except discord.Forbidden:
                continue
        
        await interaction.response.edit_message(content=f"Unbanned {self.user_id} | Denied by {interaction.user.mention}", view=self)
    
    async def escalate(self, interaction: discord.Interaction):
        self.escalate_button.disabled = True
        await interaction.response.edit_message(content=f"Escalated to Cybersecurity by {interaction.user.mention}", view=self)
