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
                        await asyncio.sleep(1)  # Prevent rate limits
                await self.config.banned_users.set(banned_users)
            except discord.HTTPException:
                continue
        
        for user_id in banned_users:
            for guild in self.bot.guilds:
                try:
                    await guild.ban(discord.Object(id=user_id), reason="Global ban enforced.")
                    await asyncio.sleep(1)  # Prevent rate limits
                except discord.Forbidden:
                    continue

    @commands.command()
    @commands.is_owner()
    async def globalban(self, ctx, user: discord.User, *, reason: str):
        banned_users = await self.config.banned_users()
        if user.id in banned_users:
            return await ctx.send("User is already globally banned.")
        
        # Add reason and banned_by to the global ban list
        await self.add_to_globalban_list(user.id, reason, ctx.author)
        banned_users.append(user.id)
        await self.config.banned_users.set(banned_users)

        for guild in self.bot.guilds:
            try:
                await guild.ban(user, reason=f"Global Ban: {reason}")
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
        await self.remove_from_globalban_list(user.id)

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
                        await asyncio.sleep(1)  # Prevent rate limits
            except discord.HTTPException:
                continue
        await self.config.banned_users.set(banned_users)
        with open("globalbans.yaml", "w") as file:
            yaml.dump(banned_users, file)
        await ctx.send("Global ban list updated.")

    @commands.command()
    @commands.is_owner()
    async def globalbanlist(self, ctx):
        global_ban_list = await self.load_globalban_list()

        # Create list to send in chunks
        total_bans = len(global_ban_list)
        if total_bans == 0:
            return await ctx.send("No global bans found.")

        # 5 bans per message to avoid size limits
        ban_list_chunks = [global_ban_list[i:i + 5] for i in range(0, len(global_ban_list), 5)]
        
        for chunk in ban_list_chunks:
            message_content = "\n".join([f"**ID:** {entry['user_id']}, **Reason:** {entry['reason']}, **Banned by:** {entry['banned_by']}" for entry in chunk])
            try:
                await ctx.author.send(message_content)
            except discord.HTTPException as e:
                log.error(f"Error sending DM: {e}")
        
        await ctx.send(f"Sent the global ban list in DM.")

    @commands.command()
    @commands.is_owner()
    async def globaltotalbans(self, ctx):
        """Show the total number of globally banned users."""
        global_ban_list = await self.load_globalban_list()
        await ctx.send(f"Total global bans: {len(global_ban_list)}")

    @commands.command()
    @commands.is_owner()
    async def globalbanlistwipe(self, ctx):
        """Wipe the global ban list with confirmation."""
        confirmation_msg = await ctx.send("Are you sure you want to wipe the global ban list? React with ✅ to confirm.")
        
        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) == "✅" and reaction.message.id == confirmation_msg.id

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
                    # Safely load content and make sure it's a list of dictionaries
                    data = yaml.safe_load(file) or []
                    if isinstance(data, list):
                        # Ensure each entry is a dictionary with required fields
                        valid_data = []
                        for entry in data:
                            if isinstance(entry, dict) and 'user_id' in entry and 'reason' in entry and 'banned_by' in entry:
                                valid_data.append(entry)
                            else:
                                log.warning(f"Skipping invalid entry: {entry}")
                        return valid_data
                    else:
                        log.error("Loaded data from globalbans.yaml is not a list. Resetting file.")
                        return []  # Reset to empty list if structure is invalid
            except Exception as e:
                log.error(f"Error loading the global ban list: {e}")
                return []  # Return empty list on error
        return []

    async def add_to_globalban_list(self, user_id, reason, banned_by):
        """Adds a user to the global ban list."""
        global_ban_list = await self.load_globalban_list()

        # Ensure the entry is in the proper format
        new_entry = {
            'user_id': user_id,
            'reason': reason,
            'banned_by': banned_by.name
        }

        # Remove the entry if it already exists in the list (based on user_id)
        global_ban_list = [entry for entry in global_ban_list if entry['user_id'] != user_id]

        # Add the new entry
        global_ban_list.append(new_entry)

        # Save to the YAML file
        try:
            with open("globalbans.yaml", "w") as file:
                yaml.dump(global_ban_list, file)
            log.info(f"User {user_id} added to global ban list with reason: {reason}")
        except Exception as e:
            log.error(f"Error adding to the global ban list: {e}")

    async def remove_from_globalban_list(self, user_id):
        """Removes a user from the global ban list."""
        global_ban_list = await self.load_globalban_list()

        # Remove the entry from the list
        global_ban_list = [entry for entry in global_ban_list if entry['user_id'] != user_id]

        # Save to the YAML file
        try:
            with open("globalbans.yaml", "w") as file:
                yaml.dump(global_ban_list, file)
            log.info(f"User {user_id} removed from global ban list.")
        except Exception as e:
            log.error(f"Error removing from the global ban list: {e}")
