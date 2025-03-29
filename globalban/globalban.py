from discord.ext import commands
import logging
import discord
import asyncio
import yaml

log = logging.getLogger(__name__)

# Global banned users list
banned_users = []
ban_list_file = "global_ban_list.yaml"

# Helper function to load the ban list from the file
def load_ban_list():
    global banned_users
    try:
        with open(ban_list_file, 'r') as f:
            banned_users = yaml.safe_load(f) or []
    except FileNotFoundError:
        banned_users = []

# Helper function to save the ban list to the file
def save_ban_list():
    with open(ban_list_file, 'w') as f:
        yaml.safe_dump(banned_users, f)

# Function to check if a user is globally banned
def is_globally_banned(user_id):
    return user_id in [ban_entry['user_id'] for ban_entry in banned_users]

class GlobalBanCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        load_ban_list()  # Load the ban list on startup

    @commands.command(name='globalban')
    async def globalban(self, ctx, user: discord.User, *, reason=None):
        """Global ban a user from all servers."""
        if is_globally_banned(user.id):
            await ctx.send(f"{user} is already globally banned.")
            return

        banned_users.append({
            'user_id': user.id,
            'username': str(user),
            'reason': reason or "No reason provided",
            'banned_by': str(ctx.author)
        })
        save_ban_list()

        for guild in self.bot.guilds:
            try:
                await guild.ban(user, reason=reason)
                log.info(f"Banned {user} from {guild.name} (Reason: {reason})")
            except discord.Forbidden:
                log.error(f"Could not ban {user} from {guild.name} due to lack of permissions.")

        await ctx.send(f"{user} has been globally banned.")
        log.info(f"{user} has been globally banned.")

    @commands.command(name='unglobalban')
    async def unglobalban(self, ctx, user: discord.User):
        """Remove a global ban and unban the user from all servers."""
        global banned_users
        banned_users = [ban for ban in banned_users if ban['user_id'] != user.id]
        save_ban_list()

        for guild in self.bot.guilds:
            try:
                await guild.unban(user)
                log.info(f"Unbanned {user} from {guild.name}.")
            except discord.Forbidden:
                log.error(f"Could not unban {user} from {guild.name} due to lack of permissions.")

        await ctx.send(f"{user} has been unglobally banned.")
        log.info(f"{user} has been unglobally banned.")

    @commands.command(name='globaltotalbans')
    async def globaltotalbans(self, ctx):
        """Show the total number of global bans."""
        await ctx.send(f"There are {len(banned_users)} globally banned users.")

    @commands.command(name='globalbanlist')
    async def globalbanlist(self, ctx):
        """Send the list of globally banned users."""
        if not banned_users:
            await ctx.send("No globally banned users.")
            return

        user_data = "\n".join([f"{user['username']} (ID: {user['user_id']}) - Reason: {user['reason']}" for user in banned_users])
        chunk_size = 1500
        for i in range(0, len(user_data), chunk_size):
            await ctx.send(user_data[i:i + chunk_size])

    @commands.command(name='globalbanupdatelist')
    async def globalbanupdatelist(self, ctx):
        """Update the global ban list from all servers."""
        log.info("Updating global ban list from the current server...")
        banned_users_current_server = []
        guild = ctx.guild
        if not guild:
            log.error("No guild found. This command must be run from a server.")
            return await ctx.send("This command must be run from a server.")

        log.info(f"Fetching bans from the server: {guild.name}")
        try:
            count = 0
            async for ban_entry in guild.bans():
                if ban_entry.user.id not in [ban['user_id'] for ban in banned_users]:
                    banned_users.append({
                        'user_id': ban_entry.user.id,
                        'username': str(ban_entry.user),
                        'reason': ban_entry.reason or "No reason provided",
                        'banned_by': str(ban_entry.mod)
                    })
                    count += 1
                await asyncio.sleep(1)  # Prevent rate limits
                if count % 5 == 0:
                    log.info(f"Still fetching bans... {count} users added so far.")
            log.info(f"Fetched {len(banned_users)} bans from {guild.name}")
            save_ban_list()
        except discord.HTTPException as e:
            log.error(f"Error fetching bans from {guild.name}: {e}")
            return await ctx.send(f"An error occurred while fetching bans from {guild.name}.")

        await ctx.send(f"Ban list updated from {guild.name}. {len(banned_users)} bans fetched.")
        log.info(f"Ban list updated from {guild.name}. {len(banned_users)} bans fetched.")

    @commands.command(name='bansync')
    async def bansync(self, ctx):
        """Sync bans with the list, overriding 12h rotation."""
        if not banned_users:
            await ctx.send("No bans on the global list.")
            return

        total_synced = 0
        for guild in self.bot.guilds:
            synced = 0
            log.info(f"Syncing bans for server: {guild.name}")
            for ban in banned_users:
                try:
                    await guild.ban(discord.Object(id=ban['user_id']), reason=ban['reason'])
                    synced += 1
                    if synced % 20 == 0:
                        log.info(f"Synced {synced} bans in {guild.name}")
                except discord.Forbidden:
                    log.error(f"Could not ban user {ban['username']} in {guild.name}.")

            total_synced += synced
            await ctx.send(f"Finished syncing {synced} bans in {guild.name}")

        await ctx.send(f"Total bans successfully synced: {total_synced}")
        log.info(f"Total bans successfully synced: {total_synced}")

    @commands.command(name='globalbanlistwipe')
    async def globalbanlistwipe(self, ctx):
        """Wipe the entire global ban list."""
        await ctx.send("Are you sure you want to wipe the global ban list? React with ✅ to confirm.")
        
        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) == '✅'
        
        try:
            reaction, _ = await self.bot.wait_for('reaction_add', check=check, timeout=60)
            if reaction:
                banned_users.clear()
                save_ban_list()
                await ctx.send("Global ban list has been wiped.")
                log.info("Global ban list has been wiped.")
        except asyncio.TimeoutError:
            await ctx.send("Global ban list wipe cancelled.")

# Setup the cog
def setup(bot):
    bot.add_cog(GlobalBanCog(bot))
