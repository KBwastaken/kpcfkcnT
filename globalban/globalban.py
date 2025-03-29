import discord
from discord.ext import commands, tasks
import yaml
import asyncio
from datetime import datetime, timedelta
import pytz
import logging

# Set up logging for debugging and progress tracking
logging.basicConfig(level=logging.INFO)

class GlobalBan(commands.Cog):  # Ensure it inherits from commands.Cog
    def __init__(self, bot):
        self.bot = bot
        self.ban_list_file = "globalbans.yaml"  # Path to the file storing global bans
        self.timezone = pytz.timezone("Europe/Amsterdam")  # Amsterdam timezone for sync timing
        self.ban_sync_time = None  # Keeps track of the last ban sync
        self.locked = True  # To lock the owner to access commands only

    def load_ban_list(self):
        """Loads the global ban list from a YAML file."""
        try:
            with open(self.ban_list_file, 'r') as file:
                return yaml.safe_load(file) or []
        except FileNotFoundError:
            logging.warning("Global ban list file not found, creating a new one.")
            return []

    def save_ban_list(self, ban_list):
        """Saves the global ban list to a YAML file."""
        with open(self.ban_list_file, 'w') as file:
            yaml.dump(ban_list, file, default_flow_style=False)
        logging.info("Global ban list saved.")

    @tasks.loop(hours=12)
    async def ban_check_loop(self):
        """Checks for the scheduled global ban sync every 12 hours (noon and midnight Amsterdam time)."""
        current_time = datetime.now(self.timezone)
        if current_time.hour == 12:  # Syncs at noon and midnight
            logging.info("Starting the global ban sync.")
            await self.sync_bans()

    @commands.command()
    async def globalban(self, ctx, user: discord.User, *, reason: str = "No reason provided"):
        """Adds a global ban entry for a user and bans from all servers."""
        if ctx.author.id != self.bot.owner_id:
            await ctx.send("This command is owner-locked.")
            return
        
        ban_list = self.load_ban_list()
        if any(ban['user_id'] == str(user.id) for ban in ban_list):
            await ctx.send(f"{user} is already globally banned.")
            return

        ban_entry = {
            "user_id": str(user.id),
            "reason": reason,
            "banned_by": str(ctx.author),
            "date": datetime.now(self.timezone).strftime("%Y-%m-%d %H:%M:%S")
        }

        # Add to global ban list
        ban_list.append(ban_entry)
        self.save_ban_list(ban_list)

        # Ban user from all servers
        for guild in self.bot.guilds:
            try:
                member = guild.get_member(user.id)
                if member:
                    await guild.ban(member, reason=reason)
                    logging.info(f"Banned {user} from {guild.name} with reason: {reason}")
            except discord.Forbidden:
                logging.error(f"Permission denied to ban {user} from {guild.name}")

        await ctx.send(f"{user} has been globally banned and banned from all servers.")

    @commands.command()
    async def unglobalban(self, ctx, user: discord.User):
        """Removes a global ban entry for a user and unbans from all servers."""
        if ctx.author.id != self.bot.owner_id:
            await ctx.send("This command is owner-locked.")
            return
        
        ban_list = self.load_ban_list()
        new_ban_list = [ban for ban in ban_list if ban['user_id'] != str(user.id)]

        if len(new_ban_list) == len(ban_list):
            await ctx.send(f"{user} is not globally banned.")
            return

        # Remove from global ban list
        self.save_ban_list(new_ban_list)

        # Unban user from all servers
        for guild in self.bot.guilds:
            try:
                member = guild.get_member(user.id)
                if member:
                    await guild.unban(member)
                    logging.info(f"Unbanned {user} from {guild.name}")
            except discord.Forbidden:
                logging.error(f"Permission denied to unban {user} from {guild.name}")

        await ctx.send(f"{user} has been removed from the global ban list and unbanned from all servers.")

    @commands.command()
    async def globaltotalbans(self, ctx):
        """Counts and returns the total number of global bans."""
        ban_list = self.load_ban_list()
        total_bans = len(ban_list)
        await ctx.send(f"{total_bans} users have been globally banned.")

    @commands.command()
    async def globalbanlist(self, ctx):
        """Sends the global ban list to the user in chunks."""
        ban_list = self.load_ban_list()
        chunks = [ban_list[i:i + 5] for i in range(0, len(ban_list), 5)]
        for chunk in chunks:
            message_content = "\n".join([f"**ID:** {entry['user_id']}, **Reason:** {entry['reason']}, **Banned by:** {entry['banned_by']}" for entry in chunk])
            await ctx.author.send(message_content)
        await ctx.send("The global ban list has been sent to you.")

    @commands.command()
    async def globalbanupdatelist(self, ctx):
        """Fetches all bans from every server and updates the global ban list."""
        guilds = self.bot.guilds
        total_bans = 0
        all_ban_entries = []

        for index, guild in enumerate(guilds, 1):
            logging.info(f"Fetching bans from {guild.name}...")
            bans = await guild.bans()
            for ban_entry in bans:
                if not any(ban['user_id'] == str(ban_entry.user.id) for ban in all_ban_entries):
                    all_ban_entries.append({
                        "user_id": str(ban_entry.user.id),
                        "reason": ban_entry.reason or "No reason provided",
                        "banned_by": str(ban_entry.user),
                        "date": datetime.now(self.timezone).strftime("%Y-%m-%d %H:%M:%S")
                    })
                    total_bans += 1
            logging.info(f"Finished fetching bans from {guild.name}, {len(bans)} bans found.")

        self.save_ban_list(all_ban_entries)
        logging.info(f"All bans fetched, {total_bans} global bans added to the list.")
        await ctx.send(f"All bans have been updated. Total bans: {total_bans}")

    @commands.command()
    async def globalbanlistwipe(self, ctx):
        """Wipes the entire global ban list after confirmation."""
        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) == '✅'

        await ctx.send("Are you sure you want to wipe the global ban list? React with ✅ to confirm.")
        reaction, user = await self.bot.wait_for('reaction_add', check=check)

        if reaction:
            self.save_ban_list([])
            await ctx.send("The global ban list has been wiped.")
            logging.info("Global ban list wiped.")

    @commands.command()
    async def bansync(self, ctx):
        """Syncs the global ban list with the bans from each server."""
        await ctx.send("Syncing bans...")
        await self.globalbanupdatelist(ctx)

    @commands.command()
    async def globalbanliststatus(self, ctx):
        """Shows the status of the global ban list."""
        ban_list = self.load_ban_list()
        total_bans = len(ban_list)
        await ctx.send(f"Global ban list contains {total_bans} bans.")

    # Starts the ban sync loop at noon and midnight Amsterdam time
    @commands.Cog.listener()
    async def on_ready(self):
        """Starts the scheduled sync task when the bot is ready."""
        self.ban_check_loop.start()

    @tasks.loop(hours=12)
    async def ban_check_loop(self):
        """Checks the time every 12 hours and performs the sync if it matches."""
        current_time = datetime.now(self.timezone)
        if current_time.hour == 12:  # Sync at noon and midnight Amsterdam time
            logging.info("Starting the global ban sync.")
            await self.sync_bans()

    async def sync_bans(self):
        """Syncs the global bans from all servers."""
        logging.info("Syncing bans across all servers...")
        await self.globalbanupdatelist()

# Add the cog to the bot
def setup(bot):
    bot.add_cog(GlobalBan(bot))  # Use the correct method to load the cog
