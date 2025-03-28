import discord
import yaml
import asyncio
import os
import logging
from redbot.core import commands, Config, checks
from redbot.core.bot import Red

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
        log.info("Starting ban sync...")
        banned_users = await self.config.banned_users()
        for guild in self.bot.guilds:
            try:
                count = 0
                async for ban_entry in guild.bans():
                    if ban_entry.user.id not in banned_users:
                        banned_users.append(ban_entry.user.id)
                        count += 1
                        await asyncio.sleep(1)  # Prevent rate limits
                        if count % 5 == 0:  # Log every 5 bans
                            log.info(f"Still fetching bans from {guild.name}... {count} bans added so far.")
                await self.config.banned_users.set(banned_users)
                log.info(f"Synced bans from guild: {guild.name}")
            except discord.HTTPException as e:
                log.error(f"Error fetching bans from {guild.name}: {e}")
                continue
        
        # Remove duplicates using a set to ensure no duplicates in the final list
        banned_users = list(set(banned_users))

        for user_id in banned_users:
            for guild in self.bot.guilds:
                try:
                    await guild.ban(discord.Object(id=user_id), reason="Global ban enforced.")
                    await asyncio.sleep(1)  # Prevent rate limits
                except discord.Forbidden:
                    log.warning(f"No permission to ban in {guild.name}")
                    continue
                log.info(f"Still banning users... {user_id} banned.")
        log.info("Ban sync completed.")

    @commands.command()
    @commands.is_owner()
    async def globalban(self, ctx, user: discord.User, *, reason: str):
        banned_users = await self.config.banned_users()
        if user.id in banned_users:
            return await ctx.send("User is already globally banned.")
        
        # Check if there's an existing ban reason
        global_ban_list = await self.load_globalban_list()
        existing_reason = None
        for entry in global_ban_list:
            if entry['user_id'] == user.id:
                existing_reason = entry['reason']
                break
        
        # Use the existing reason if found, otherwise use the provided reason
        if existing_reason:
            reason = existing_reason

        banned_users.append(user.id)
        
        # Remove duplicates before saving
        banned_users = list(set(banned_users))
        
        await self.config.banned_users.set(banned_users)

        # Save to global ban list with the who banned info
        await self.add_to_globalban_list(user.id, reason, ctx.author)

        for guild in self.bot.guilds:
            try:
                await guild.ban(user, reason=reason)
                await asyncio.sleep(1)  # Prevent rate limits
            except discord.Forbidden:
                continue
        await ctx.send(f"{user} has been globally banned.")

    @commands.command()
    @commands.is_owner()
    async def unglobalban(self, ctx, user: discord.User, *, reason: str):
        banned_users = await self.config.banned_users()
        if user.id not in banned_users:
            return await ctx.send("User is not globally banned.")
        banned_users.remove(user.id)
        await self.config.banned_users.set(banned_users)
        for guild in self.bot.guilds:
            try:
                await guild.unban(user, reason=f"Global Unban: {reason}")
                await asyncio.sleep(1)  # Prevent rate limits
            except discord.Forbidden:
                continue
        await ctx.send(f"{user} has been globally unbanned.")

    @commands.command()
    @commands.is_owner()
    async def bansync(self, ctx):
        log.info("Manual ban sync initiated.")
        await self.sync_bans()
        await ctx.send("Global bans synced.")

    @commands.command()
    @commands.is_owner()
    async def globalbanupdatelist(self, ctx):
        log.info("Updating global ban list from multiple servers...")
        banned_users = []

        # Fetch bans from all servers concurrently
        async def fetch_bans(guild):
            log.info(f"Fetching bans from the server: {guild.name}")
            local_banned_users = []
            try:
                count = 0
                async for ban_entry in guild.bans():
                    if ban_entry.user.id not in banned_users:
                        banned_users.append(ban_entry.user.id)
                        local_banned_users.append(ban_entry.user.id)
                        count += 1
                        await asyncio.sleep(1)  # Prevent rate limits
                        if count % 5 == 0:  # Log every 5 bans
                            log.info(f"Still fetching bans from {guild.name}... {count} bans added so far.")
                log.info(f"Finished fetching bans from {guild.name}. {count} bans added.")
            except discord.HTTPException as e:
                log.error(f"Error fetching bans from {guild.name}: {e}")
            return local_banned_users

        # Run fetch_bans concurrently for all servers
        tasks = [fetch_bans(guild) for guild in self.bot.guilds]
        results = await asyncio.gather(*tasks)

        # Combine all fetched banned users into one list, removing duplicates
        for result in results:
            for user_id in result:
                if user_id not in banned_users:
                    banned_users.append(user_id)

        # Remove duplicates using a set to ensure no duplicates in the final list
        banned_users = list(set(banned_users))

        # Save the bans to YAML
        try:
            with open("globalbans.yaml", "w") as file:
                yaml.dump(banned_users, file)
            log.info(f"Global ban list updated with {len(banned_users)} users.")
        except Exception as e:
            log.error(f"Error saving the global ban list: {e}")
            return await ctx.send("An error occurred while saving the global ban list.")
        
        await self.config.banned_users.set(banned_users)
        await ctx.send("Global ban list updated from all servers.")

    @commands.command()
    @commands.is_owner()
    async def globalbanlist(self, ctx):
        """Sends the global ban list to the user's DMs, splitting into chunks if necessary."""
        if not os.path.exists("globalbans.yaml"):
            with open("globalbans.yaml", "w") as file:
                yaml.dump([], file)
        
        try:
            with open("globalbans.yaml", "r") as file:
                data = yaml.safe_load(file) or []  # Safely load the content if file is not empty
            
            # Prepare the content for sending in chunks
            data_str = "\n".join([f"User ID: {entry['user_id']} | Reason: {entry['reason']} | Banned by: {entry['banned_by']}" for entry in data])
            chunk_size = 1500  # Discord's character limit for messages
            for i in range(0, len(data_str), chunk_size):
                await ctx.author.send(f"Global Ban List (Part {i//chunk_size + 1}):\n{data_str[i:i+chunk_size]}")
            
            await ctx.send("Global ban list sent to your DMs.")
        except Exception as e:
            log.error(f"Error reading the global ban list: {e}")
            await ctx.send("An error occurred while reading the global ban list.")

    @commands.command()
    @commands.is_owner()
    async def globaltotalbans(self, ctx):
        """Displays the total number of globally banned users."""
        try:
            with open("globalbans.yaml", "r") as file:
                data = yaml.safe_load(file) or []  # Safely load the content if file is not empty
            
            total_bans = len(data)  # Count the number of banned users in the global ban list
            await ctx.send(f"There are currently {total_bans} users globally banned.")
        except Exception as e:
            log.error(f"Error reading the global ban list: {e}")
            await ctx.send("An error occurred while reading the global ban list.")

    @commands.command()
    @commands.is_owner()
    async def globalbanlistwipe(self, ctx):
        """Wipes the global ban list after reaction confirmation."""
        confirm_msg = await ctx.send("Are you sure you want to wipe the global ban list? React with ✅ to confirm.")
        
        # Add the confirmation reaction
        await confirm_msg.add_reaction("✅")
        
        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) == "✅" and reaction.message.id == confirm_msg.id

        try:
            await self.bot.wait_for("reaction_add", timeout=60.0, check=check)
        except asyncio.TimeoutError:
            return await ctx.send("You took too long to confirm. The action was cancelled.")
        
        # Proceed with wiping the global ban list
        try:
            with open("globalbans.yaml", "w") as file:
                yaml.dump([], file)
            log.info("Global ban list wiped.")
            await ctx.send("Global ban list has been wiped.")
        except Exception as e:
            log.error(f"Error wiping the global ban list: {e}")
            await ctx.send("An error occurred while wiping the global ban list.")

    async def load_globalban_list(self):
        """Load the global ban list from the YAML file."""
        if os.path.exists("globalbans.yaml"):
            try:
                with open("globalbans.yaml", "r") as file:
                    return yaml.safe_load(file) or []  # Safely load the content if file is empty
            except Exception as e:
                log.error(f"Error loading the global ban list: {e}")
                return []
        return []

    async def add_to_globalban_list(self, user_id, reason, banned_by):
        """Adds a user to the global ban list."""
        global_ban_list = await self.load_globalban_list()

        # Remove the entry if it exists already
        global_ban_list = [entry for entry in global_ban_list if entry['user_id'] != user_id]

        # Add the new entry
        global_ban_list.append({
            'user_id': user_id,
            'reason': reason,
            'banned_by': banned_by.name
        })

        # Save to the YAML file
        try:
            with open("globalbans.yaml", "w") as file:
                yaml.dump(global_ban_list, file)
            log.info(f"User {user_id} added to global ban list with reason: {reason}")
        except Exception as e:
            log.error(f"Error adding to the global ban list: {e}")
