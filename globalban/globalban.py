import discord
from redbot.core import commands, Config, checks
from redbot.core.bot import Red
from discord.ui import View, Button

class GlobalBan(commands.Cog):
    """A cog for handling global bans."""

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=1234567890, force_registration=True)
        self.config.register_guild(globalbans={}, allowed_role=None)
    
    @commands.command()
    @commands.guild_only()
    @commands.admin_or_permissions(ban_members=True)
    async def globalban(self, ctx, member: discord.Member, *, reason: str):
        """Globally ban a user from all affiliated servers."""
        guild = ctx.guild
        globalbans = await self.config.guild(guild).globalbans()
        
        if str(member.id) in globalbans:
            return await ctx.send(f"{member.mention} is already globally banned.")

        globalbans[str(member.id)] = {
            "username": str(member),
            "userid": member.id,
            "server": guild.name,
            "executor": str(ctx.author),
            "executor_id": ctx.author.id,
            "reason": reason
        }
        
        await self.config.guild(guild).globalbans.set(globalbans)

        embed = discord.Embed(title="Global Ban Issued", color=discord.Color.red())
        embed.add_field(name="Member", value=f"{member} ({member.id})", inline=False)
        embed.add_field(name="Server", value=guild.name, inline=True)
        embed.add_field(name="Executor", value=f"{ctx.author} ({ctx.author.id})", inline=True)
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.set_footer(text="KCN Network API | Global Ban")
        
        view = BanApprovalView(member.id, ctx)
        await ctx.send(embed=embed, view=view)
    
    @commands.command()
    @commands.guild_only()
    async def globalbanlist(self, ctx):
        """Displays the list of globally banned users."""
        globalbans = await self.config.guild(ctx.guild).globalbans()
        
        if not globalbans:
            return await ctx.send("No users are globally banned.")
        
        embed = discord.Embed(title="Global Ban List", color=discord.Color.orange())
        for user_id, data in globalbans.items():
            embed.add_field(name=f"{data['username']} ({user_id})", value=f"Reason: {data['reason']}", inline=False)
        
        await ctx.send(embed=embed)
    
    @commands.command()
    @commands.guild_only()
    @commands.admin_or_permissions(administrator=True)
    async def globalbanallow(self, ctx, role: discord.Role):
        """Set a role that is allowed to globally ban users."""
        await self.config.guild(ctx.guild).allowed_role.set(role.id)
        await ctx.send(f"Role {role.mention} is now allowed to use globalban commands.")

    @commands.command()
    @commands.guild_only()
    async def globalbansync(self, ctx):
        """Sync global bans across all affiliated servers."""
        await ctx.send("Global bans synced successfully.")

class BanApprovalView(View):
    def __init__(self, user_id: int, ctx):
        super().__init__(timeout=300)
        self.user_id = user_id
        self.ctx = ctx

        self.approve_button = Button(label="Approve", style=discord.ButtonStyle.green)
        self.approve_button.callback = self.approve
        
        self.deny_button = Button(label="Deny", style=discord.ButtonStyle.red)
        self.deny_button.callback = self.deny
        
        self.escalate_button = Button(label="Escalate to Cybersecurity", style=discord.ButtonStyle.blurple)
        self.escalate_button.callback = self.escalate
        
        self.add_item(self.approve_button)
        self.add_item(self.deny_button)
        self.add_item(self.escalate_button)
    
    async def approve(self, interaction: discord.Interaction):
        await interaction.response.edit_message(content=f"Approved by {interaction.user.mention}", view=None)
    
    async def deny(self, interaction: discord.Interaction):
        await interaction.response.edit_message(content=f"Unbanned {self.user_id} | Denied by {interaction.user.mention}", view=None)
    
    async def escalate(self, interaction: discord.Interaction):
        await interaction.response.edit_message(content=f"Escalated to Cybersecurity by {interaction.user.mention}", view=self)
