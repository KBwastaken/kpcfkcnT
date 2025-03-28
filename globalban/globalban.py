import discord
import yaml
import asyncio
import os
from redbot.core import commands, Config, checks
from redbot.core.bot import Red
import logging

log = logging.getLogger("red.GlobalBan")

class GlobalBan(commands.Cog):
    """A cog for global banning users across all servers the bot is in."""

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=1234567890)
        self.config.register_global(banned_users=[])
        self.bg_task = self.bot.loop.create_task(self.ban_check_loop())

    async def ban_check_loop(self):
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            await asyncio.sleep(43200)  # 12 hours
            await self.sync_bans()
            owner = self.bot.owner or (await self.bot.application_info()).owner
            if owner:
                await owner.send("Global ban list checked and updated.")

    async def sync_bans(self):
        banned_users = await self.config.banned_users()
        for guild in self.bot.guilds:
            try:
                async for ban_entry in guild.bans():
                    if ban_entry.user.id not in banned_users:
                        banned_users.append(ban_entry.user.id)
                        log.info(f"User {ban_entry.user.id} added to global ban list.")
                        await asyncio.sleep(1)  # Prevent rate limits
                await self.config.banned_users.set(banned_users)
            except discord.HTTPException:
                continue
        
        for user_id in banned_users:
            for guild in self.bot.guilds:
                try:
                    await guild.ban(discord.Object(id=user_id), reason="Global ban enforced.")
                    log.info(f"Global ban enforced for {user_id}.")
                    await asyncio.sleep(1)  # Prevent rate limits
                except discord.Forbidden:
                    continue

    @commands.command()
    @commands.is_owner()
    async def globalban(self, ctx, user: discord.User, *, reason: str = None):
        banned_users = await self.config.banned_users()
        if user.id in banned_users:
            return await ctx.send("User is already globally banned.")
        
        banned_users.append(user.id)
        await self.config.banned_users.set(banned_users)
        
        # Log and store the reason and who banned
        ban_info = {
            'user_id': user.id,
            'reason': reason if reason else "No reason provided",
            'banned_by': str(ctx.author)
        }

        await self.add_to_globalban_list(ban_info)
        
        for guild in self.bot.guilds:
            try:
                await guild.ban(user, reason=f"Global Ban: {reason if reason else 'No reason provided'}")
                log.info(f"User {user.id} banned globally with reason: {reason if reason else 'No reason provided'}")
                await asyncio.sleep(1)  # Prevent rate limits
            except discord.Forbidden:
                continue

        await ctx.send(f"{user} has been globally banned.")

    @commands.command()
    @commands.is_owner()
    async def unglobalban(self, ctx, user: discord.User, *, reason: str = None):
        banned_users = await self.config.banned_users()
        if user.id not in banned_users:
            return await ctx.send("User is not globally banned.")
        
        banned_users.remove(user.id)
        await self.config.banned_users.set(banned_users)
        
        # Remove from global ban list
        await self.remove_from_globalban_list(user.id)
        
        for guild in self.bot.guilds:
            try:
                await guild.unban(user, reason=f"Global Unban: {reason if reason else 'No reason provided'}")
                log.info(f"User {user.id} unbanned globally with reason: {reason if reason else 'No reason provided'}")
                await asyncio.sleep(1)  # Prevent rate limits
            except discord.Forbidden:
                continue

        await ctx.send(f"{user} has been globally unbanned.")

    @commands.command()
    @commands.is_owner()
    async def bansync(self, ctx):
        await self.sync_bans()
        await ctx.send("Global bans synced.")

    @commands.command()
    @commands.is_owner()
    async def globalbanupdatelist(self, ctx):
        banned_users = []
        for guild in self.bot.guilds:
            try:
                async for ban_entry in guild.bans():
                    if ban_entry.user.id not in banned_users:
                        banned_users.append(ban_entry.user.id)
                        log.info(f"User {ban_entry.user.id} added to global ban list.")
                        await asyncio.sleep(1)  # Prevent rate limits
            except discord.HTTPException:
                continue

        await self.config.banned_users.set(banned_users)
        await self.update_globalban_list_from_bans()

        await ctx.send("Global ban list updated.")

    async def update_globalban_list_from_bans(self):
        # Get bans and add them to the global ban list
        for guild in self.bot.guilds:
            try:
                async for ban_entry in guild.bans():
                    ban_info = {
                        'user_id': ban_entry.user.id,
                        'reason': ban_entry.reason if ban_entry.reason else "No reason provided",
                        'banned_by': str(ban_entry.user)  # The user who banned (usually the bot)
                    }
                    await self.add_to_globalban_list(ban_info)
            except discord.HTTPException:
                continue

    async def add_to_globalban_list(self, ban_info):
        """ Add user to the global ban list in YAML file. """
        global_ban_list = await self.load_globalban_list()

        # Prevent duplicates
        if any(entry['user_id'] == ban_info['user_id'] for entry in global_ban_list):
            log.warning(f"Skipping duplicate entry for user {ban_info['user_id']}")
            return

        global_ban_list.append(ban_info)

        with open("globalbans.yaml", "w") as file:
            yaml.dump(global_ban_list, file)

    async def remove_from_globalban_list(self, user_id):
        """ Remove a user from the global ban list. """
        global_ban_list = await self.load_globalban_list()

        # Remove the user from the list if present
        global_ban_list = [entry for entry in global_ban_list if entry['user_id'] != user_id]

        with open("globalbans.yaml", "w") as file:
            yaml.dump(global_ban_list, file)

    async def load_globalban_list(self):
        """ Load the global ban list from the YAML file. """
        if not os.path.exists("globalbans.yaml"):
            return []

        with open("globalbans.yaml", "r") as file:
            return yaml.safe_load(file) or []

    @commands.command()
    @commands.is_owner()
    async def globalbanlist(self, ctx):
        """Show the global ban list."""
        try:
            # Load the global ban list from the YAML file
            global_ban_list = await self.load_globalban_list()

            # Log the number of entries
            log.info(f"Loaded global ban list with {len(global_ban_list)} entries.")
            
            # Split the list into chunks of 1500 characters (Discord's message limit)
            chunk_size = 1500
            chunks = []
            current_chunk = ""

            for entry in global_ban_list:
                message = f"**ID:** {entry['user_id']}, **Reason:** {entry['reason']}, **Banned by:** {entry['banned_by']}\n"
                
                # Check if adding the message to the current chunk would exceed the limit
                if len(current_chunk) + len(message) > chunk_size:
                    chunks.append(current_chunk)
                    current_chunk = message  # Start a new chunk
                else:
                    current_chunk += message  # Add to the current chunk

            # Add the final chunk
            if current_chunk:
                chunks.append(current_chunk)

            # Send each chunk as a separate message
            for chunk in chunks:
                try:
                    await ctx.author.send(chunk)
                    log.info("Global ban list chunk sent to the bot owner.")
                except discord.HTTPException:
                    await ctx.author.send("Global ban list is too large to send in a single message.")
                    log.warning("Message content too large to send.")
                    break

        except Exception as e:
            log.error(f"Error reading the global ban list: {e}")
            await ctx.send("Error reading the global ban list.")

    @commands.command()
    @commands.is_owner()
    async def globaltotalbans(self, ctx):
        """Show the total number of global bans."""
        global_ban_list = await self.load_globalban_list()
        total_bans = len(global_ban_list)
        await ctx.send(f"There are currently {total_bans} users globally banned.")


def setup(bot):
    bot.add_cog(GlobalBan(bot))
