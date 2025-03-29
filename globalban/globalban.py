import discord
from redbot.core import commands
import asyncio
import logging
import yaml
from datetime import datetime, timedelta

log = logging.getLogger("redbot")

# Store banned users in a global list or YAML file.
banned_users_list = set()  # Global banned list (can be saved to a file)
ban_data = {}  # Stores ban reason and who banned them.
ban_check_time = datetime.utcnow()  # Tracks when the next 12-hour ban check should occur.

class GlobalBan(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def globalban(self, ctx, user: discord.User, *, reason=None):
        """Ban a user globally and add them to the ban list"""
        banned_users_list.add(user.id)
        ban_data[user.id] = {
            "reason": reason,
            "banned_by": ctx.author.id,
            "timestamp": discord.utils.utcnow(),
        }
        log.info(f"Global banned user {user.name} with ID {user.id}. Reason: {reason}.")
        
        # Ban the user from all servers.
        for guild in self.bot.guilds:
            await self._ban_user_from_guild(user, guild)
        await ctx.send(f"{user.name} has been globally banned.")

    @commands.command()
    async def unglobalban(self, ctx, user: discord.User):
        """Remove a user from the global ban list and unban them from all servers"""
        if user.id not in banned_users_list:
            await ctx.send(f"{user.name} is not in the global ban list.")
            return
        
        banned_users_list.remove(user.id)
        del ban_data[user.id]
        
        # Unban the user from all servers.
        for guild in self.bot.guilds:
            await self._unban_user_from_guild(user, guild)
        await ctx.send(f"{user.name} has been removed from the global ban list and unbanned.")

    @commands.command()
    async def globalbanlist(self, ctx):
        """Send the global ban list to the bot owner"""
        global_ban_list = '\n'.join([f"{user_id}: {ban_data[user_id]}" for user_id in banned_users_list])
        
        # Send the list in chunks if it's too long
        max_chunk_size = 1500
        if len(global_ban_list) > max_chunk_size:
            for i in range(0, len(global_ban_list), max_chunk_size):
                await ctx.author.send(global_ban_list[i:i+max_chunk_size])
        else:
            await ctx.author.send(global_ban_list)
        log.info("Sent global ban list to owner.")

    @commands.command()
    async def globalbanupdatelist(self, ctx):
        """Update the global ban list by fetching bans from all servers"""
        log.info("Updating global ban list from the current server...")
        
        updated_ban_data = {}
        for guild in self.bot.guilds:
            log.info(f"Fetching bans from {guild.name}...")
            bans = await self._fetch_bans(guild)
            for user_id, ban_info in bans.items():
                if user_id not in banned_users_list:
                    banned_users_list.add(user_id)
                    updated_ban_data[user_id] = ban_info
            log.info(f"Fetched bans from {guild.name}. {len(bans)} bans found.")
        
        log.info("Global ban list updated successfully.")
        await ctx.send(f"Global ban list has been updated.")
    
    @commands.command()
    async def globaltotalbans(self, ctx):
        """Send the live global ban counter"""
        total_bans = len(banned_users_list)
        await ctx.send(f"Total global bans: {total_bans}")
        log.info(f"Global bans count: {total_bans}")

    @commands.command()
    async def bansync(self, ctx):
        """Sync the bans across all servers based on the global ban list"""
        log.info("Syncing bans across all servers...")
        
        # Loop over each server
        for guild in self.bot.guilds:
            log.info(f"Syncing bans in server {guild.name}...")
            bans_synced = 0
            for user_id in banned_users_list:
                user = await self.bot.get_user_info(user_id)
                if user:
                    await self._ban_user_from_guild(user, guild)
                    bans_synced += 1
                    if bans_synced % 20 == 0:
                        log.info(f"Synced {bans_synced} bans in {guild.name}.")
            log.info(f"Finished syncing {bans_synced} bans in {guild.name}.")
            await ctx.send(f"{bans_synced} bans synced in {guild.name}.")
        log.info("Finished syncing bans across all servers.")
        await ctx.send("Bans synced successfully in all servers.")

    @commands.command()
    async def globalbanlistwipe(self, ctx):
        """Wipe the global ban list"""
        await ctx.send("Are you sure you want to wipe the global ban list? React with ✅ to confirm.")
        
        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) == '✅'

        try:
            reaction, user = await self.bot.wait_for('reaction_add', timeout=60.0, check=check)
            if reaction:
                banned_users_list.clear()
                ban_data.clear()
                log.info("Global ban list has been wiped.")
                await ctx.send("Global ban list wiped successfully.")
        except asyncio.TimeoutError:
            await ctx.send("Wipe operation timed out. The global ban list was not wiped.")

    async def _ban_user_from_guild(self, user, guild):
        """Ban a user from a specific guild"""
        try:
            await guild.ban(user)
            log.info(f"User {user.name} banned from {guild.name}.")
        except discord.Forbidden:
            log.error(f"Failed to ban {user.name} from {guild.name}. Insufficient permissions.")
        except discord.HTTPException as e:
            log.error(f"Failed to ban {user.name} from {guild.name}: {e}")

    async def _unban_user_from_guild(self, user, guild):
        """Unban a user from a specific guild"""
        try:
            await guild.unban(user)
            log.info(f"User {user.name} unbanned from {guild.name}.")
        except discord.Forbidden:
            log.error(f"Failed to unban {user.name} from {guild.name}. Insufficient permissions.")
        except discord.HTTPException as e:
            log.error(f"Failed to unban {user.name} from {guild.name}: {e}")
    
    async def _fetch_bans(self, guild):
        """Fetch all bans from a guild"""
        bans = {}
        try:
            async for ban_entry in guild.bans():
                user_id = ban_entry.user.id
                bans[user_id] = {
                    "reason": ban_entry.reason,
                    "banned_by": ban_entry.user.name,
                }
            return bans
        except discord.HTTPException as e:
            log.error(f"Error fetching bans from {guild.name}: {e}")
            return {}

    @tasks.loop(hours=12)
    async def check_ban_rotations(self):
        """Check for bans every 12 hours"""
        global ban_check_time
        if datetime.utcnow() - ban_check_time >= timedelta(hours=12):
            log.info("12-hour ban check rotation started.")
            for guild in self.bot.guilds:
                log.info(f"Checking bans in {guild.name}...")
                bans = await self._fetch_bans(guild)
                for user_id, ban_info in bans.items():
                    if user_id in banned_users_list:
                        log.info(f"User {user_id} is already banned globally.")
                    else:
                        user = await self.bot.get_user_info(user_id)
                        if user:
                            await self._ban_user_from_guild(user, guild)
                            banned_users_list.add(user_id)
            ban_check_time = datetime.utcnow()
            log.info("12-hour ban check rotation completed.")

    @check_ban_rotations.before_loop
    async def before_check_ban_rotation(self):
        """Wait before starting the loop"""
        await asyncio.sleep(5)
        log.info("Starting 12-hour ban check rotation loop.")

def setup(bot):
    bot.add_cog(GlobalBan(bot))
