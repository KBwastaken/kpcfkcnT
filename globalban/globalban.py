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
                print("Global ban list checked and updated.")  # Logging here

    async def sync_bans(self):
        banned_users = await self.config.banned_users()
        print("Starting sync of global bans.")  # Logging the start of the sync
        for guild in self.bot.guilds:
            try:
                print(f"Fetching bans from {guild.name}...")  # Logging guild fetching
                async for ban_entry in guild.bans():
                    if ban_entry.user.id not in banned_users:
                        banned_users.append(ban_entry.user.id)
                        print(f"Added ban: {ban_entry.user.id} from {guild.name}.")  # Logging each addition
                        await asyncio.sleep(1)  # Prevent rate limits
                await self.config.banned_users.set(banned_users)
                print(f"Finished syncing bans from {guild.name}.")  # Logging after each guild
            except discord.HTTPException as e:
                print(f"Error syncing bans from {guild.name}: {e}")  # Logging the error
                continue
        
        print("Finished syncing all bans.")  # Final log after all guilds are synced

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
        await self.config.banned_users.set(banned_users)
        
        for guild in self.bot.guilds:
            try:
                print(f"Banning {user.id} from {guild.name} with reason: {reason}")  # Logging each ban
                await guild.ban(user, reason=f"Global Ban: {reason}")
                await asyncio.sleep(1)  # Prevent rate limits
            except discord.Forbidden:
                print(f"Permission denied to ban {user.id} in {guild.name}.")  # Logging permission error
                continue
        await ctx.send(f"{user} has been globally banned.")

    @commands.command()
    @commands.is_owner()
    async def unglobalban(self, ctx, user: discord.User, *, reason: str):
        """Globally unbans a user across all servers."""
        banned_users = await self.config.banned_users()
        if user.id not in banned_users:
            return await ctx.send("User is not globally banned.")
        banned_users.remove(user.id)
        await self.config.banned_users.set(banned_users)

        for guild in self.bot.guilds:
            try:
                print(f"Unbanning {user.id} from {guild.name} with reason: {reason}")  # Logging each unban
                await guild.unban(user, reason=f"Global Unban: {reason}")
                await asyncio.sleep(1)  # Prevent rate limits
            except discord.Forbidden:
                print(f"Permission denied to unban {user.id} in {guild.name}.")  # Logging permission error
                continue
        await ctx.send(f"{user} has been globally unbanned.")

    @commands.command()
    @commands.is_owner()
    async def bansync(self, ctx):
        """Syncs the global ban list with all the servers the bot is in."""
        await self.sync_bans()
        await ctx.send("Global bans synced.")
        print("Global bans synced.")  # Logging sync completion

    @commands.command()
    @commands.is_owner()
    async def globalbanupdatelist(self, ctx):
        """Updates the global ban list by fetching bans from all servers."""
        banned_users = await self.config.banned_users()
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
                    print(f"Processed {chunk_counter} bans from {guild.name}.")
                    chunk_bans = []  # Clear the chunk list

                # Keep track of the total bans fetched
                total_bans_fetched += fetched_bans

            except discord.Forbidden:
                print(f"Permission denied: Unable to fetch bans from {guild.name}.")  # Logging permission error
                continue
            except discord.HTTPException:
                print(f"An error occurred while fetching bans from {guild.name}.")  # Logging HTTP error
                continue

        # After finishing all servers, update the global ban list
        await self.config.banned_users.set(banned_users)

        # Write the updated list to the YAML file
        with open("globalbans.yaml", "w") as file:
            yaml.dump(banned_users, file)

        # Log the completion and the total number of bans fetched
        await ctx.send(f"Global ban list updated. Total bans fetched: {total_bans_fetched} bans.")
        print(f"Global ban list updated. Total bans fetched: {total_bans_fetched} bans.")  # Logging total fetch

    @commands.command()
    @commands.is_owner()
    async def globalbanlist(self, ctx):
        """Sends the global ban list to the user."""
        if not os.path.exists("globalbans.yaml"):
            with open("globalbans.yaml", "w") as file:
                yaml.dump([], file)
        await ctx.author.send(file=discord.File("globalbans.yaml"))
        await ctx.send("Global ban list sent to your DMs.")
        print("Global ban list sent to the user.")  # Logging successful send

    @commands.command()
    @commands.is_owner()
    async def globalbanlistwipe(self, ctx):
        """Wipes the global ban list after confirmation."""
        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) == '✅'

        await ctx.send("Are you sure you want to wipe the global ban list? React with ✅ to confirm.")
        try:
            reaction, user = await self.bot.wait_for('reaction_add', timeout=60.0, check=check)
        except asyncio.TimeoutError:
            await ctx.send("Wipe operation timed out. No changes made.")
            return

        # Wipe the global ban list
        await self.config.banned_users.set([])
        await ctx.send("Global ban list has been wiped.")
        print("Global ban list has been wiped.")  # Logging wipe action


def setup(bot):
    bot.add_cog(GlobalBan(bot))
