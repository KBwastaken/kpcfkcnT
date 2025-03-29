import discord
import yaml
import asyncio
import os
from redbot.core import commands, Config
from redbot.core.bot import Red

class GlobalBan(commands.Cog):
    """A cog for global banning users across all servers the bot is in."""

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=1234567890)
        self.config.register_global(banned_users=[], ban_reasons={})
        self.bg_task = self.bot.loop.create_task(self.ban_check_loop())

    async def ban_check_loop(self):
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            await asyncio.sleep(43200)  # 12 hours
            await self.sync_bans()

            owner = self.bot.owner or (await self.bot.application_info()).owner
            if owner:
                await owner.send("Global ban list checked and updated.")
                print("Global ban list checked and updated.")  # Logging here

    async def sync_bans(self):
        banned_users = await self.config.banned_users()
        ban_reasons = await self.config.ban_reasons()
        print("Starting sync of global bans.")  # Logging the start of the sync
        total_bans_fetched = 0
        for guild in self.bot.guilds:
            try:
                print(f"Fetching bans from {guild.name}...")  # Logging guild fetching
                async for ban_entry in guild.bans():
                    if ban_entry.user.id not in banned_users:
                        banned_users.append(ban_entry.user.id)
                        ban_reasons[ban_entry.user.id] = ban_entry.reason or "Global ban enforced."
                        print(f"Added ban: {ban_entry.user.id} from {guild.name}.")  # Logging each addition
                        total_bans_fetched += 1
                        await asyncio.sleep(1)  # Prevent rate limits
                await self.config.banned_users.set(banned_users)
                await self.config.ban_reasons.set(ban_reasons)
                print(f"Finished syncing bans from {guild.name}.")  # Logging after each guild
            except discord.HTTPException as e:
                print(f"Error syncing bans from {guild.name}: {e}")  # Logging the error
                continue
        
        print(f"Finished syncing all bans. Total bans fetched: {total_bans_fetched}.")  # Logging total bans fetched

        for user_id in banned_users:
            for guild in self.bot.guilds:
                try:
                    print(f"Applying global ban for {user_id} in {guild.name}.")  # Logging each ban application
                    await guild.ban(discord.Object(id=user_id), reason="Global ban enforced.")
                    await asyncio.sleep(1)  # Prevent rate limits
                except discord.Forbidden:
                    print(f"Permission denied to ban user {user_id} in {guild.name}.")  # Logging permission error
                    continue
        print("Finished applying global bans.")  # Final log for the ban application

    @commands.command()
    @commands.is_owner()
    async def globalban(self, ctx, user: discord.User, *, reason: str):
        """Globally bans a user across all servers."""
        banned_users = await self.config.banned_users()
        if user.id in banned_users:
            return await ctx.send("User is already globally banned.")
        
        banned_users.append(user.id)
        ban_reasons = await self.config.ban_reasons()
        ban_reasons[user.id] = reason
        await self.config.banned_users.set(banned_users)
        await self.config.ban_reasons.set(ban_reasons)
        
        for guild in self.bot.guilds:
            try:
                print(f"Banning {user.id} from {guild.name} with reason: {reason}")  # Logging each ban
                await guild.ban(user, reason=f"Global Ban: {reason}")
                await asyncio.sleep(1)  # Prevent rate limits
            except discord.Forbidden:
                print(f"Permission denied to ban {user.id} in {guild.name}.")  # Logging permission error
                continue
        await ctx.send(f"{user} has been globally banned.")
        print(f"{user} has been globally banned.")  # Logging successful global ban

    @commands.command()
    @commands.is_owner()
    async def unglobalban(self, ctx, user: discord.User, *, reason: str):
        """Globally unbans a user across all servers."""
        banned_users = await self.config.banned_users()
        if user.id not in banned_users:
            return await ctx.send("User is not globally banned.")
        
        banned_users.remove(user.id)
        ban_reasons = await self.config.ban_reasons()
        del ban_reasons[user.id]
        await self.config.banned_users.set(banned_users)
        await self.config.ban_reasons.set(ban_reasons)

        for guild in self.bot.guilds:
            try:
                print(f"Unbanning {user.id} from {guild.name} with reason: {reason}")  # Logging each unban
                await guild.unban(user, reason=f"Global Unban: {reason}")
                await asyncio.sleep(1)  # Prevent rate limits
            except discord.Forbidden:
                print(f"Permission denied to unban {user.id} in {guild.name}.")  # Logging permission error
                continue
        await ctx.send(f"{user} has been globally unbanned.")
        print(f"{user} has been globally unbanned.")  # Logging successful global unban

    @commands.command()
    @commands.is_owner()
    async def bansync(self, ctx):
        """Syncs the global ban list with all the servers the bot is in and applies the bans."""
        banned_users = await self.config.banned_users()
        ban_reasons = await self.config.ban_reasons()

        total_bans_applied = 0
        for user_id in banned_users:
            for guild in self.bot.guilds:
                try:
                    reason = ban_reasons.get(user_id, "Global ban enforced.")
                    print(f"Applying global ban for {user_id} in {guild.name} with reason: {reason}")  # Logging each ban application
                    await guild.ban(discord.Object(id=user_id), reason=reason)
                    total_bans_applied += 1
                    await asyncio.sleep(1)  # Prevent rate limits
                except discord.Forbidden:
                    print(f"Permission denied to ban {user_id} in {guild.name}.")  # Logging permission error
                    continue
        await ctx.send(f"{total_bans_applied} global bans have been applied.")
        print(f"{total_bans_applied} global bans applied.")  # Logging bans applied

    @commands.command()
    @commands.is_owner()
    async def globaltotalbans(self, ctx):
        """Shows the total number of globally banned users."""
        banned_users = await self.config.banned_users()
        total_bans = len(banned_users)
        await ctx.send(f"There are currently {total_bans} users globally banned.")
        print(f"Total global bans: {total_bans}")  # Logging total bans

    @commands.command()
    @commands.is_owner()
    async def globalbanupdatelist(self, ctx):
        """Updates the global ban list by fetching bans from all servers."""
        banned_users = await self.config.banned_users()
        ban_reasons = await self.config.ban_reasons()
        total_bans_fetched = 0
        server_counter = 0
        chunk_size = 5  # You can adjust this number to change the chunk size

        # Loop over all guilds (servers the bot is in)
        for guild in self.bot.guilds:
            server_counter += 1
            fetched_bans = 0
            chunk_counter = 0
            chunk_bans = []

            # Try fetching bans from the server
            try:
                print(f"Fetching bans from {guild.name}...")  # Logging guild fetching
                async for ban_entry in guild.bans():  # This is an async generator, so we need to iterate over it
                    # Check if the user is already globally banned; if not, add them
                    if ban_entry.user.id not in banned_users:
                        banned_users.append(ban_entry.user.id)
                        ban_reasons[ban_entry.user.id] = ban_entry.reason or "Global ban enforced."
                        chunk_bans.append(ban_entry.user.id)
                        fetched_bans += 1
                        chunk_counter += 1

                        # Log each chunk's progress
                        if chunk_counter >= chunk_size:
                            # After processing a chunk of bans, log the progress and reset the chunk
                            print(f"Processed {chunk_size} bans from {guild.name}.")
                            chunk_bans = []  # Clear the chunk list
                            chunk_counter = 0  # Reset chunk counter

                # If there are any remaining bans in the chunk after the loop, log them
                if chunk_counter > 0:
                    print(f"Processed {chunk_counter} bans from {guild.name}.")  # Logging the chunk of bans
                    chunk_bans = []  # Clear after logging

                await self.config.banned_users.set(banned_users)
                await self.config.ban_reasons.set(ban_reasons)
                print(f"Finished fetching bans from {guild.name}. {fetched_bans} bans fetched.")  # Logging after each server
            except discord.HTTPException as e:
                print(f"Error fetching bans from {guild.name}: {e}")  # Logging the error
                continue

        print(f"Global ban list updated. Total bans fetched: {total_bans_fetched}.")  # Final log for updates

    @commands.command()
    @commands.is_owner()
    async def globalbanlistwipe(self, ctx):
        """Wipes the global ban list and requires confirmation."""
        await ctx.send("Are you sure you want to wipe the global ban list? React with ✅ to confirm.")

        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) == "✅"

        try:
            reaction, _ = await self.bot.wait_for('reaction_add', timeout=60.0, check=check)
        except asyncio.TimeoutError:
            await ctx.send("Wipe operation timed out. No changes made.")
            return

        # Wipe the global ban list
        await self.config.banned_users.set([])
        await self.config.ban_reasons.set({})
        await ctx.send("Global ban list has been wiped.")
        print("Global ban list has been wiped.")  # Logging wipe action


def setup(bot):
    bot.add_cog(GlobalBan(bot))
