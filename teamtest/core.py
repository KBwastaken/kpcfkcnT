import discord
from redbot.core import commands, Config
from redbot.core.utils.predicates import MessagePredicate, ReactionPredicate
from redbot.core.utils.menus import start_adding_reactions

class TeamRole(commands.Cog):
    """Manage team role across all servers"""
    
    owner_id = 1174820638997872721  # Your owner ID
    role_name = "KCN | Team"
    role_color = "#77bcd6"

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=78631109)
        self.config.register_global(team_users=[])

    async def red_delete_data_for_user(self, **kwargs):
        """No data to delete"""
        pass

    async def bot_owner_check(self, ctx):
        """Check if user is the defined owner"""
        return ctx.author.id == self.owner_id

    async def team_member_check(self, ctx):
        """Check if user is owner, in team list, or has role"""
        if await self.bot_owner_check(ctx):
            return True
            
        team_users = await self.config.team_users()
        if ctx.author.id in team_users:
            return True
            
        if ctx.guild:
            role = discord.utils.get(ctx.guild.roles, name=self.role_name)
            if role and role in ctx.author.roles:
                return True
        return False

    @commands.group()
    @commands.check(lambda ctx: ctx.cog.bot_owner_check(ctx))
    async def team(self, ctx):
        """Team management commands"""
        pass

    # Owner-only commands
    @team.command()
    async def setup(self, ctx):
        """Create team role in this server"""
        existing_role = discord.utils.get(ctx.guild.roles, name=self.role_name)
        if existing_role:
            return await ctx.send("Role already exists!")
            
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
            await ctx.send(f"Successfully created {new_role.mention}")
        except discord.Forbidden:
            await ctx.send("I need Manage Roles permission!")
        except discord.HTTPException:
            await ctx.send("Failed to create role!")

    @team.command()
    async def add(self, ctx, user: discord.User):
        """Add user to the team list"""
        async with self.config.team_users() as users:
            if user.id not in users:
                users.append(user.id)
                await ctx.send(f"Added {user} to team list")
                await self.update_roles(user.id, add=True)
            else:
                await ctx.send("User already in team list")

    @team.command()
    async def remove(self, ctx, user: discord.User):
        """Remove user from the team list"""
        async with self.config.team_users() as users:
            if user.id in users:
                users.remove(user.id)
                await ctx.send(f"Removed {user} from team list")
                await self.update_roles(user.id, add=False)
            else:
                await ctx.send("User not in team list")

    async def update_roles(self, user_id: int, add: bool):
        """Update roles across all servers for specific user"""
        for guild in self.bot.guilds:
            try:
                role = discord.utils.get(guild.roles, name=self.role_name)
                member = guild.get_member(user_id)
                if role and member:
                    if add and role not in member.roles:
                        await member.add_roles(role)
                    elif not add and role in member.roles:
                        await member.remove_roles(role)
            except Exception as e:
                print(f"Error updating roles in {guild.name}: {str(e)}")

    @team.command()
    async def update(self, ctx):
        """Update team roles across all servers"""
        team_users = await self.config.team_users()
        msg = await ctx.send("Starting global role update...")
        
        success = errors = 0
        for guild in self.bot.guilds:
            try:
                role = discord.utils.get(guild.roles, name=self.role_name)
                if not role:
                    await ctx.send(f"{guild.name}: Server not setup")
                    errors += 1
                    continue
                
                # Force role position update
                bot_top_role = guild.me.top_role
                if bot_top_role.position > 1:
                    try:
                        await role.edit(
                            position=bot_top_role.position - 1,
                            reason="Maintain role position"
                        )
                    except Exception as e:
                        await ctx.send(f"Can't position role in {guild.name}: {str(e)}")
                        errors += 1
                        continue
                
                # Sync members
                current_members = {m.id for m in role.members}
                to_remove = current_members - set(team_users)
                to_add = set(team_users) - current_members
                
                for uid in to_remove:
                    member = guild.get_member(uid)
                    if member:
                        await member.remove_roles(role)
                
                for uid in to_add:
                    member = guild.get_member(uid)
                    if member:
                        await member.add_roles(role)
                
                success += 1
            except Exception as e:
                errors += 1
                await ctx.send(f"Error in {guild.name}: {str(e)}")
        
        await msg.edit(content=f"Update complete! Success: {success}, Errors: {errors}")

    # ... [Keep wipe, delete commands same as previous version] ...

    # Team member commands
    @team.command()
    @commands.check("team_member_check")
    async def getinvite(self, ctx):
        """Generate single-use invites for all servers"""
        invites = []
        for guild in self.bot.guilds:
            try:
                channel = next((c for c in guild.text_channels if c.permissions_for(guild.me).create_instant_invite), None)
                if channel:
                    invite = await channel.create_invite(
                        max_uses=1,
                        unique=True,
                        reason=f"Invite by {ctx.author}"
                    )
                    invites.append(f"{guild.name}: {invite.url}")
            except:
                pass
        
        try:
            await ctx.author.send("**Server Invites (1 use each):**\n" + "\n".join(invites))
            await ctx.send("Check your DMs!")
        except discord.Forbidden:
            await ctx.send("I can't DM you! Enable DMs and try again.")

    @team.command()
    @commands.check("team_member_check")
    async def sendmessage(self, ctx):
        """Send a message to all team members"""
        await ctx.send("Type your message (5 minute timeout):")
        try:
            msg = await self.bot.wait_for(
                "message",
                check=lambda m: m.author == ctx.author,
                timeout=300
            )
        except TimeoutError:
            return await ctx.send("Timed out.")
            
        embed = discord.Embed(
            title=f"Team Message from {ctx.author}",
            description=msg.content,
            color=discord.Color.from_str(self.role_color)
        )
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar.url)
        
        if msg.attachments:
            embed.set_image(url=msg.attachments[0].url)
        
        sent, failed = 0, 0
        team_users = await self.config.team_users()
        for uid in team_users:
            user = self.bot.get_user(uid)
            if user:
                try:
                    await user.send(embed=embed)
                    sent += 1
                except:
                    failed += 1
        await ctx.send(f"Delivered to {sent} members. Failed: {failed}")

    @team.command(name="list")
    @commands.check("team_member_check")
    async def team_list(self, ctx):
        """List all team members"""
        team_users = await self.config.team_users()
        members = []
        for uid in team_users:
            user = self.bot.get_user(uid)
            members.append(f"{user.mention} ({user.id})" if user else f"Unknown ({uid})")
        
        embed = discord.Embed(
            title="Team Members",
            description="\n".join(members) if members else "No members",
            color=discord.Color.from_str(self.role_color)
        )
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(TeamRole(bot))
