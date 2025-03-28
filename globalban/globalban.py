import discord
import yaml
import asyncio
import os
from redbot.core import commands, Config, checks
from redbot.core.bot import Red
import logging
import time

# Setup logger
log = logging.getLogger("red.GlobalBan")
log.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
log.addHandler(handler)

class GlobalBan(commands.Cog):
    """A cog for global banning users across all servers the bot is in."""

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=1234567890)
        self.config.register_global(banned_users=[], last_sync_time=0)
        self.bg_task = self.bot.loop.create_task(self.ban_check_loop())

    async def ban_check_loop(self):
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            # Get the current time and the last sync time from config
            last_sync_time = await self.config.last_sync_time()
            current_time = time.time()
            
            # If more than 12 hours have passed, sync the bans
            if current_time - last_sync_time >= 43200:  # 12 hours in seconds
                log.info("12 hours passed, syncing global bans...")
                await self.sync_bans()

                # Update the last sync time in config
                await self.config.last_sync_time.set(current_time)

            # Wait for a certain amount of time before checking again
            await asyncio.sleep(3600)  # Check every hour

    async def sync_bans(self):
        banned_users = await self.config.banned_users()
        for guild in self.bot.guilds:
            try:
                async for ban_entry in guild.bans():
                    if ban_entry.user.id not in banned_users:
                        banned_users.append(ban_entry.user.id)
                        log.info(f"Adding user {ban_entry.user.id} to global ban list.")
                        await asyncio.sleep(1)  # Prevent rate limits
                await self.config.banned_users.set(banned_users)
            except discord.HTTPException:
                continue
        
        for user_id in banned_users:
            for guild in self.bot.guilds:
                try:
                    # Fetch reason and banned_by if available
                    reason = None
                    banned_by = None
                    ban_entry = next((entry for entry in guild.bans() if entry.user.id == user_id), None)
                    if ban_entry:
                        reason = ban_entry.reason
                        banned_by = ban_entry.user.name
                    await guild.ban(discord.Object(id=user_id), reason=reason or "Global ban enforced.")
                    log.info(f"User {user_id} globally banned with reason: {reason or 'Global ban enforced.'} (Banned by {banned_by or 'Unknown'})")
                    await asyncio.sleep(1)  # Prevent rate limits
                except discord.Forbidden:
                    continue

    async def load_globalban_list(self):
        """Load the global ban list from the YAML file."""
        file_path = "globalbans.yaml"
        
        # If the file doesn't exist, create an empty list and return
        if not os.path.exists(file_path):
            log.warning(f"{file_path} not found. Creating a new file.")
            return []

        try:
            with open(file_path, "r") as file:
                return yaml.safe_load(file) or []
        except Exception as e:
            log.error(f"Error reading global ban list: {e}")
            return []

    async def save_globalban_list(self, global_ban_list):
        """Save the global ban list to the YAML file."""
        try:
            with open("globalbans.yaml", "w") as file:
                yaml.dump(global_ban_list, file)
            log.info("Global ban list saved successfully.")
        except Exception as e:
            log.error(f"Error saving the global ban list: {e}")

    @commands.command()
    @commands.is_owner()
    async def globalban(self, ctx, user: discord.User, *, reason: str):
        """Globally ban a user across all servers."""
        banned_users = await self.config.banned_users()
        if user.id in banned_users:
            return await ctx.send("User is already globally banned.")
        banned_users.append(user.id)
        await self.config.banned_users.set(banned_users)
        
        # Fetch the banning user info and reason for this global ban
        banned_by = ctx.author.name
        reason = reason or "No reason provided"
        
        for guild in self.bot.guilds:
            try:
                await guild.ban(user, reason=f"Global Ban: {reason}")
                log.info(f"Banned {user} globally with reason: {reason} (Banned by {banned_by})")
                await asyncio.sleep(1)  # Prevent rate limits
            except discord.Forbidden:
                continue

        await ctx.send(f"{user} has been globally banned.")

    @commands.command()
    @commands.is_owner()
    async def unglobalban(self, ctx, user: discord.User, *, reason: str):
        """Globally unban a user from all servers."""
        banned_users = await self.config.banned_users()
        if user.id not in banned_users:
            return await ctx.send("User is not globally banned.")
        banned_users.remove(user.id)
        await self.config.banned_users.set(banned_users)
        
        # Fetch the banning user info and reason for this unban
        banned_by = ctx.author.name
        reason = reason or "No reason provided"
        
        for guild in self.bot.guilds:
            try:
                await guild.unban(user, reason=f"Global Unban: {reason}")
                log.info(f"Unbanned {user} globally with reason: {reason} (Unbanned by {banned_by})")
                await asyncio.sleep(1)  # Prevent rate limits
            except discord.Forbidden:
                continue

        await ctx.send(f"{user} has been globally unbanned.")

    @commands.command()
    @commands.is_owner()
    async def bansync(self, ctx):
        """Sync all bans across all servers."""
        await self.sync_bans()
        await ctx.send("Global bans synced.")

    @commands.command()
    @commands.is_owner()
    async def globalbanupdatelist(self, ctx):
        """Update the global ban list from the server where the command is issued."""
        global_ban_list = await self.load_globalban_list()

        log.info(f"Starting global ban list update in server: {ctx.guild.name}")

        updated_bans = []
        
        async for ban_entry in ctx.guild.bans():
            user_id = ban_entry.user.id
            reason = ban_entry.reason if ban_entry.reason else "No reason provided"
            banned_by = ban_entry.user.name if ban_entry.user else "Unknown"
            
            existing_entry = next((entry for entry in global_ban_list if entry['user_id'] == user_id), None)

            if existing_entry:
                # If the user is already in the list, update their reason and the banning user
                existing_entry['reason'] = reason
                existing_entry['banned_by'] = banned_by
                updated_bans.append(existing_entry)
                log.info(f"Updated ban for user {user_id}: {reason} (Banned by {banned_by})")
            else:
                # If the user is not in the list, add a new entry
                updated_bans.append({
                    'user_id': user_id,
                    'reason': reason,
                    'banned_by': banned_by
                })
                log.info(f"Added new ban for user {user_id}: {reason} (Banned by {banned_by})")

        # Save the updated list to the YAML file
        await self.save_globalban_list(updated_bans)
        await ctx.send("Global ban list updated successfully.")

    @commands.command()
    @commands.is_owner()
    async def globalbanlist(self, ctx):
        """Show the global ban list."""
        try:
            global_ban_list = await self.load_globalban_list()
            
            log.info(f"Loaded global ban list with {len(global_ban_list)} entries.")
            
            # Split list into chunks for sending messages
            chunk_size = 1500
            chunks = [global_ban_list[i:i + chunk_size] for i in range(0, len(global_ban_list), chunk_size)]

            for chunk in chunks:
                message_content = "\n".join([f"**ID:** {entry['user_id']}, **Reason:** {entry['reason']}, **Banned by:** {entry['banned_by']}" for entry in chunk])
                try:
                    await ctx.author.send(message_content)
                    log.info("Global ban list sent to the bot owner.")
                except discord.HTTPException:
                    await ctx.author.send("Global ban list is too large to send in a single message.")
                    log.warning("Message content too large to send.")
                    break
        except Exception as e:
            log.error(f"Error reading the global ban list: {e}")
            await ctx.send("Error reading the global ban list.")

    @commands.command()
    @commands.is_owner()
    async def globalbanlistwipe(self, ctx):
        """Wipe the global ban list, with confirmation."""
        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) == '✅'
        
        await ctx.send("Are you sure you want to wipe the global ban list? React with ✅ to confirm.")
        try:
            reaction, _ = await self.bot.wait_for('reaction_add', timeout=60.0, check=check)
            if reaction:
                os.remove("globalbans.yaml")
                log.info("Global ban list wiped.")
                await ctx.send("Global ban list has been wiped.")
        except asyncio.TimeoutError:
            await ctx.send("Confirmation timed out, global ban list was not wiped.")

    @commands.command()
    @commands.is_owner()
    async def globaltotalbans(self, ctx):
        """Show the total number of global bans."""
        try:
            global_ban_list = await self.load_globalban_list()
            total_bans = len(global_ban_list)
            log.info(f"Total number of global bans: {total_bans}")
            await ctx.send(f"Total number of global bans: {total_bans}")
        except Exception as e:
            log.error(f"Error reading the global ban list: {e}")
            await ctx.send("Error fetching the total global bans.")


def setup(bot):
    bot.add_cog(GlobalBan(bot))
