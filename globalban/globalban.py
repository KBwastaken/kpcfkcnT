import discord
import yaml
import asyncio
import os
import time
from redbot.core import commands, Config
from redbot.core.bot import Red

class GlobalBan(commands.Cog):
    """A cog for global banning users across all servers the bot is in."""

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=1234567890)
        self.config.register_global(
            banned_users=[],
            last_check_time=0
        )
        self.bg_task = self.bot.loop.create_task(self.ban_check_loop())

    async def ban_check_loop(self):
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            # Checking every 12 hours (43200 seconds)
            await asyncio.sleep(43200)  
            await self.sync_bans()
            owner = self.bot.owner or (await self.bot.application_info()).owner
            if owner:
                await owner.send("Global ban list checked and updated.")

    async def sync_bans(self):
        banned_users = await self.config.banned_users()
        total_bans = 0
        total_servers = len(self.bot.guilds)
        server_counter = 0

        # Loop over all guilds
        for guild in self.bot.guilds:
            server_counter += 1
            # Track how many bans we fetched from this server
            fetched_bans = 0
            try:
                async for ban_entry in guild.bans():
                    # Add bans to the global list if not already present
                    if ban_entry.user.id not in banned_users:
                        banned_users.append(ban_entry.user.id)
                        fetched_bans += 1
                    # Log every 5 bans fetched from this server
                    if fetched_bans % 5 == 0:
                        await self.bot.get_channel(ctx.channel.id).send(f"Fetching from {guild.name}: {fetched_bans} bans fetched so far.")
                
                # After finishing a server, log that the server's bans are done
                await self.bot.get_channel(ctx.channel.id).send(f"Finished fetching bans from {guild.name}. {fetched_bans} bans fetched.")
                total_bans += fetched_bans

            except discord.HTTPException:
                continue

        # Update global banned users list after processing all servers
        await self.config.banned_users.set(banned_users)
        
        # Write to the YAML file after updating
        with open("globalbans.yaml", "w") as file:
            yaml.dump(banned_users, file)
        
        # Log when all bans have been fetched from all servers
        await self.bot.get_channel(ctx.channel.id).send(f"All bans fetched. List updated with {total_bans} bans.")

    @commands.command()
    @commands.is_owner()
    async def globalban(self, ctx, user: discord.User, *, reason: str = None):
        """Globally bans a user from all servers."""
        banned_users = await self.config.banned_users()
        if user.id in banned_users:
            return await ctx.send("User is already globally banned.")
        
        banned_users.append(user.id)
        await self.config.banned_users.set(banned_users)
        
        # Create log information for the ban
        ban_info = {
            'user_id': user.id,
            'reason': reason if reason else "No reason provided",
            'banned_by': str(ctx.author)  # The person who issued the ban
        }

        # Save the ban info in the global ban list (YAML file)
        await self.add_to_globalban_list(ban_info)
        
        for guild in self.bot.guilds:
            try:
                await guild.ban(user, reason=f"Global Ban: {reason if reason else 'No reason provided'}")
                await asyncio.sleep(1)  # Prevent rate limits
            except discord.Forbidden:
                continue

        await ctx.send(f"{user} has been globally banned.")

    @commands.command()
    @commands.is_owner()
    async def unglobalban(self, ctx, user: discord.User, *, reason: str = None):
        """Removes the global ban on a user."""
        banned_users = await self.config.banned_users()
        if user.id not in banned_users:
            return await ctx.send("User is not globally banned.")
        
        banned_users.remove(user.id)
        await self.config.banned_users.set(banned_users)

        # Remove from the global ban list (YAML file)
        await self.remove_from_globalban_list(user.id)

        for guild in self.bot.guilds:
            try:
                await guild.unban(user, reason=f"Global Unban: {reason if reason else 'No reason provided'}")
                await asyncio.sleep(1)  # Prevent rate limits
            except discord.Forbidden:
                continue

        await ctx.send(f"{user} has been globally unbanned.")

    @commands.command()
    @commands.is_owner()
    async def bansync(self, ctx):
        """Syncs the global ban list immediately."""
        await self.sync_bans()
        await ctx.send("Global bans synced.")

    @commands.command()
    @commands.is_owner()
    async def globalbanupdatelist(self, ctx):
        """Updates the global ban list by fetching bans from all servers."""
        banned_users = await self.config.banned_users()
        for guild in self.bot.guilds:
            try:
                # Fetch the bans from the server the command is issued from
                async for ban_entry in guild.bans():
                    if ban_entry.user.id not in banned_users:
                        banned_users.append(ban_entry.user.id)
                        await asyncio.sleep(1)  # Prevent rate limits
            except discord.HTTPException:
                continue
        
        # Update the global ban list
        await self.config.banned_users.set(banned_users)
        
        # Write the updated list to the YAML file
        with open("globalbans.yaml", "w") as file:
            yaml.dump(banned_users, file)

        await ctx.send("Global ban list updated.")

    @commands.command()
    @commands.is_owner()
    async def globalbanlist(self, ctx):
        """Sends the entire global ban list to the user in DMs."""
        if not os.path.exists("globalbans.yaml"):
            with open("globalbans.yaml", "w") as file:
                yaml.dump([], file)
        
        # Read the YAML file and send it in chunks
        with open("globalbans.yaml", "r") as file:
            banned_users = yaml.safe_load(file) or []
        
        # If list is too long, split into chunks
        chunk_size = 1500
        chunks = [banned_users[i:i + chunk_size] for i in range(0, len(banned_users), chunk_size)]
        
        for chunk in chunks:
            message_content = "\n".join([f"**ID:** {entry['user_id']}, **Reason:** {entry['reason']}, **Banned by:** {entry['banned_by']}" for entry in chunk])
            try:
                await ctx.author.send(message_content)
                await asyncio.sleep(1)
            except discord.HTTPException as e:
                await ctx.send(f"Error sending global ban list: {str(e)}")
                break
        await ctx.send("Global ban list sent to your DMs.")

    @commands.command()
    @commands.is_owner()
    async def globalbanlistwipe(self, ctx):
        """Wipes the global ban list after confirmation."""
        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) == '✅'

        # Ask for confirmation
        await ctx.send("Are you sure you want to wipe the global ban list? React with ✅ to confirm.")
        try:
            reaction, user = await self.bot.wait_for("reaction_add", check=check, timeout=60)
            if reaction:
                banned_users = []
                await self.config.banned_users.set(banned_users)
                with open("globalbans.yaml", "w") as file:
                    yaml.dump([], file)
                await ctx.send("Global ban list has been wiped.")
        except asyncio.TimeoutError:
            await ctx.send("You took too long to react, operation cancelled.")

    @commands.command()
    @commands.is_owner()
    async def globaltotalbans(self, ctx):
        """Shows the total number of banned users globally."""
        banned_users = await self.config.banned_users()
        await ctx.send(f"Total global bans: {len(banned_users)}.")

    async def add_to_globalban_list(self, ban_info):
        """Add a ban to the global ban list."""
        banned_users = await self.config.banned_users()
        banned_users.append(ban_info)
        await self.config.banned_users.set(banned_users)

    async def remove_from_globalban_list(self, user_id):
        """Remove a user from the global ban list."""
        banned_users = await self.config.banned_users()
        banned_users = [entry for entry in banned_users if entry['user_id'] != user_id]
        await self.config.banned_users.set(banned_users)

def setup(bot):
    bot.add_cog(GlobalBan(bot))
