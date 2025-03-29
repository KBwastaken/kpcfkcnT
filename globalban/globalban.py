import discord
from discord.ext import commands, tasks
import yaml
import logging
from datetime import datetime
import pytz
import asyncio

# Set up logging
logging.basicConfig(level=logging.INFO)

class GlobalBan(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.ban_list_file = "globalbans.yaml"
        self.timezone = pytz.timezone("Europe/Amsterdam")
        self.ban_sync.start()  # Start the 12h rotation task
        logging.info("GlobalBan cog has been loaded successfully.")

    def load_ban_list(self):
        """Load the ban list from the YAML file."""
        try:
            with open(self.ban_list_file, 'r') as file:
                return yaml.safe_load(file) or []
        except FileNotFoundError:
            logging.warning("Global ban list file not found.")
            return []

    def save_ban_list(self, ban_list):
        """Save the updated ban list to the YAML file."""
        with open(self.ban_list_file, 'w') as file:
            yaml.dump(ban_list, file, default_flow_style=False)
        logging.info("Global ban list saved.")

    async def rotate_ban_sync(self):
        """Handle the 12-hour rotation sync."""
        current_time = datetime.now(self.timezone)
        hour = current_time.hour
        if hour == 12 or hour == 0:  # Every 12 hours (afternoon and midnight Amsterdam time)
            await self.sync_bans()

    @tasks.loop(hours=12)
    async def ban_sync(self):
        """12-hour rotation task."""
        await self.rotate_ban_sync()

    @commands.command()
    async def globalban(self, ctx, user: discord.User, *, reason: str = "No reason provided"):
        """Add a user to the global ban list and ban them from all servers."""
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

        ban_list.append(ban_entry)
        self.save_ban_list(ban_list)

        # Apply the ban across all servers
        for guild in self.bot.guilds:
            try:
                member = guild.get_member(user.id)
                if member:
                    await guild.ban(member, reason=reason)
                    logging.info(f"Banned {user} from {guild.name}")
            except discord.Forbidden:
                logging.error(f"Permission denied to ban {user} from {guild.name}")

        await ctx.send(f"{user} has been globally banned and banned from all servers.")

    @commands.command()
    async def unglobalban(self, ctx, user: discord.User):
        """Remove a user from the global ban list and unban them from all servers."""
        if ctx.author.id != self.bot.owner_id:
            await ctx.send("This command is owner-locked.")
            return

        ban_list = self.load_ban_list()
        new_ban_list = [ban for ban in ban_list if ban['user_id'] != str(user.id)]

        if len(new_ban_list) == len(ban_list):
            await ctx.send(f"{user} is not globally banned.")
            return

        self.save_ban_list(new_ban_list)

        # Unban the user from all servers
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
        """Send the total number of globally banned users."""
        ban_list = self.load_ban_list()
        total_bans = len(ban_list)
        await ctx.send(f"{total_bans} users have been globally banned.")

    @commands.command()
    async def globalbanlist(self, ctx):
        """Send the list of globally banned users."""
        ban_list = self.load_ban_list()
        chunks = [ban_list[i:i + 5] for i in range(0, len(ban_list), 5)]
        for chunk in chunks:
            message_content = "\n".join([f"**ID:** {entry['user_id']}, **Reason:** {entry['reason']}, **Banned by:** {entry['banned_by']}" for entry in chunk])
            await ctx.author.send(message_content)
        await ctx.send("The global ban list has been sent to you.")

    @commands.command()
    async def globalbanupdatelist(self, ctx):
        """Update the global ban list with bans from all servers."""
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
        """Wipe the global ban list and all bans from all servers."""
        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) == '✅'

        await ctx.send("Are you sure you want to wipe the global ban list? React with ✅ to confirm.")
        reaction, user = await self.bot.wait_for('reaction_add', check=check)

        if reaction:
            self.save_ban_list([])
            await ctx.send("The global ban list has been wiped.")
            logging.info("Global ban list wiped.")

    # Utility function to log bans across all servers
    async def log_bans(self, bans, guild_name):
        for ban in bans:
            logging.info(f"Ban details from {guild_name}: User {ban.user.name}, Reason: {ban.reason}")

    # Utility function for rotating ban checks
    async def sync_bans(self):
        logging.info("Starting global ban sync.")
        guilds = self.bot.guilds
        total_bans = 0

        for guild in guilds:
            logging.info(f"Checking bans for guild: {guild.name}")
            bans = await guild.bans()
            for ban_entry in bans:
                logging.info(f"Banned user: {ban_entry.user}, Reason: {ban_entry.reason}")
                total_bans += 1

        logging.info(f"Ban sync complete. Total bans: {total_bans}")
        await self.bot.owner.send(f"Global ban sync complete. Total bans across all servers: {total_bans}")

    @commands.command()
    async def forceban(self, ctx, user: discord.User, *, reason: str = "No reason provided"):
        """Force ban a user even if they are not in the server."""
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

        ban_list.append(ban_entry)
        self.save_ban_list(ban_list)

        # Apply the ban across all servers
        for guild in self.bot.guilds:
            try:
                await guild.ban(user, reason=reason)
                logging.info(f"Force banned {user} from {guild.name}")
            except discord.Forbidden:
                logging.error(f"Permission denied to force ban {user} from {guild.name}")

        await ctx.send(f"{user} has been forcefully banned from all servers.")

# Add the cog to the bot
def setup(bot):
    bot.add_cog(GlobalBan(bot))  # Synchronous setup
