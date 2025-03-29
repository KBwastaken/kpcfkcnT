import discord
import yaml
import asyncio
import os
import logging
from redbot.core import commands, Config
from redbot.core.bot import Red
from datetime import datetime, timedelta
import pytz


# Set up logging
logging.basicConfig(level=logging.DEBUG)

class GlobalBan(commands.Cog):
    """A cog for global banning users across all servers the bot is in."""

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=1234567890)
        self.config.register_global(banned_users=[])
        self.config.register_global(ban_reasons={})
        self.bg_task = self.bot.loop.create_task(self.ban_check_loop())

    async def ban_check_loop(self):
        """Run the ban sync every 12 hours (at 12 PM and 12 AM Amsterdam time)"""
        await self.bot.wait_until_ready()

        while not self.bot.is_closed():
            now = datetime.now(pytz.timezone('Europe/Amsterdam'))
            next_run = self.get_next_run_time(now)
            logging.info(f"Next scheduled ban sync at {next_run.strftime('%Y-%m-%d %H:%M:%S')}")

            # Wait until the next scheduled time
            wait_time = (next_run - now).total_seconds()
            await asyncio.sleep(wait_time)

            await self.sync_bans()

            owner = self.bot.owner or (await self.bot.application_info()).owner
            if owner:
                await owner.send(f"Global ban list checked and updated at {next_run.strftime('%Y-%m-%d %H:%M:%S')}.")

    def get_next_run_time(self, now: datetime):
        """Return the next 12-hour mark, either 12:00 PM or 12:00 AM Amsterdam time."""
        next_run = now.replace(hour=12, minute=0, second=0, microsecond=0)
        if now > next_run:
            next_run = next_run + timedelta(hours=12)
        return next_run

    async def sync_bans(self):
        """Only bans users from the global ban list"""
        banned_users = await self.config.banned_users()
        for guild in self.bot.guilds:
            for user_id in banned_users:
                try:
                    await guild.ban(discord.Object(id=user_id), reason="Global ban enforced.")
                    await asyncio.sleep(1)  # Prevent rate limits
                except discord.Forbidden:
                    continue

    @commands.command()
    @commands.is_owner()
    async def globalban(self, ctx, user: discord.User, *, reason: str = "No reason provided"):
        """Globally ban a user"""
        banned_users = await self.config.banned_users()
        if user.id in banned_users:
            return await ctx.send("User is already globally banned.")

        # Add to the list
        banned_users.append(user.id)
        await self.config.banned_users.set(banned_users)

        # Save the reason and who banned
        ban_reasons = await self.config.ban_reasons()
        ban_reasons[user.id] = {"reason": reason, "banned_by": ctx.author.name}
        await self.config.ban_reasons.set(ban_reasons)

        for guild in self.bot.guilds:
            try:
                await guild.ban(user, reason=f"Global Ban: {reason}")
                await asyncio.sleep(1)  # Prevent rate limits
            except discord.Forbidden:
                continue
        await ctx.send(f"{user} has been globally banned.")

    @commands.command()
    @commands.is_owner()
    async def unglobalban(self, ctx, user: discord.User, *, reason: str = "No reason provided"):
        """Unban a globally banned user"""
        banned_users = await self.config.banned_users()
        if user.id not in banned_users:
            return await ctx.send("User is not globally banned.")
        
        # Remove from the list
        banned_users.remove(user.id)
        await self.config.banned_users.set(banned_users)

        # Remove the reason and banned by
        ban_reasons = await self.config.ban_reasons()
        if user.id in ban_reasons:
            del ban_reasons[user.id]
        await self.config.ban_reasons.set(ban_reasons)

        for guild in self.bot.guilds:
            try:
                await guild.unban(user, reason=f"Global Unban: {reason}")
                await asyncio.sleep(1)  # Prevent rate limits
            except discord.Forbidden:
                continue
        await ctx.send(f"{user} has been globally unbanned.")

    @commands.command()
    @commands.is_owner()
    async def globaltotalbans(self, ctx):
        """Count the total number of global bans"""
        banned_users = await self.config.banned_users()
        await ctx.send(f"Total global bans: {len(banned_users)}")

    @commands.command()
    @commands.is_owner()
    async def globalbanlist(self, ctx):
        """Send the global ban list to the user in chunks of 4000 characters."""
        banned_users = await self.config.banned_users()
        ban_reasons = await self.config.ban_reasons()
        total_bans = len(banned_users)

        if total_bans == 0:
            await ctx.send("No users are globally banned.")
            return

        # Prepare the global ban list
        ban_list = [
            f"**ID:** {user_id}, **Reason:** {ban_reasons.get(user_id, 'No reason provided')}, **Banned by:** {ban_reasons.get(user_id, {}).get('banned_by', 'Unknown')}" 
            for user_id in banned_users
        ]
        
        # Split the list into chunks of 4000 characters
        chunk_size = 4000
        current_chunk = ""
        
        for ban in ban_list:
            if len(current_chunk + "\n" + ban) <= chunk_size:
                current_chunk += "\n" + ban  # Add to the current chunk
            else:
                # Send the current chunk and start a new one
                await ctx.author.send(current_chunk)
                current_chunk = ban  # Start a new chunk

        # Send the last chunk if there is any content left
        if current_chunk:
            await ctx.author.send(current_chunk)

        await ctx.send(f"Global ban list sent to your DMs.")

    @commands.command()
    @commands.is_owner()
    async def globalbanupdatelist(self, ctx):
        """Fetch bans from all servers and update the global ban list"""
        banned_users = await self.config.banned_users()
        ban_reasons = await self.config.ban_reasons()
        total_servers = len(self.bot.guilds)
        server_counter = 0

        for guild in self.bot.guilds:
            server_counter += 1
            logging.info(f"Fetching bans from {guild.name}...")
            current_bans = []

            async for ban_entry in guild.bans():
                user_id = ban_entry.user.id
                reason = ban_entry.reason or "No reason provided"
                banned_by = ban_entry.user.name

                if user_id not in banned_users:
                    banned_users.append(user_id)
                    ban_reasons[user_id] = {"reason": reason, "banned_by": banned_by}
                    current_bans.append(f"ID: {user_id}, Reason: {reason}, Banned by: {banned_by}")
                
            logging.info(f"Finished fetching {len(current_bans)} bans from {guild.name}.")
            await asyncio.sleep(1)  # Prevent rate limits

            # Log progress
            if server_counter % 5 == 0:
                logging.info(f"{server_counter} servers processed out of {total_servers}.")

        # Save the updated list
        await self.config.banned_users.set(banned_users)
        await self.config.ban_reasons.set(ban_reasons)

        logging.info(f"All bans fetched. Total: {len(banned_users)}")
        await ctx.send(f"Global ban list updated. Total bans: {len(banned_users)}.")

    @commands.command()
    @commands.is_owner()
    async def bansync(self, ctx):
        """Sync the bans only from the global list"""
        banned_users = await self.config.banned_users()

        for guild in self.bot.guilds:
            for user_id in banned_users:
                try:
                    await guild.ban(discord.Object(id=user_id), reason="Global ban enforced.")
                    await asyncio.sleep(1)  # Prevent rate limits
                except discord.Forbidden:
                    continue

        await ctx.send("Global ban list has been synced to all servers.")

    @commands.command()
    @commands.is_owner()
    async def globalbanwipe(self, ctx):
        """Wipe the entire global ban list after confirmation"""
        def check(m):
            return m.author == ctx.author and m.content.lower() in ['yes', 'no']

        await ctx.send("Are you sure you want to wipe the global ban list? Type 'yes' to confirm.")
        try:
            response = await self.bot.wait_for('message', check=check, timeout=30)
            if response.content.lower() == 'yes':
                await self.config.banned_users.clear()
                await self.config.ban_reasons.clear()
                await ctx.send("Global ban list has been wiped.")
            else:
                await ctx.send("Action cancelled.")
        except asyncio.TimeoutError:
            await ctx.send("Confirmation timed out, action cancelled.")

def setup(bot):
    bot.add_cog(GlobalBan(bot))
