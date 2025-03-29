import discord
import yaml
import asyncio
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

    async def sync_bans(self):
        banned_users = await self.config.banned_users()
        ban_reasons = await self.config.ban_reasons()
        print("Starting global ban sync...")

        for guild in self.bot.guilds:
            print(f"Fetching bans from {guild.name}...")
            try:
                async for ban_entry in guild.bans():
                    user_id = ban_entry.user.id
                    if user_id not in banned_users:
                        # Only add if the user isn't already banned
                        banned_users.append(user_id)
                        ban_reasons[user_id] = ban_entry.reason if ban_entry.reason else "No reason provided"
                        print(f"Added {user_id} to global ban list with reason: {ban_entry.reason}")
                    await asyncio.sleep(1)  # Prevent rate limits
            except discord.HTTPException:
                print(f"Failed to fetch bans for {guild.name}")
                continue

        await self.config.banned_users.set(banned_users)
        await self.config.ban_reasons.set(ban_reasons)

        # Now, ban those in the global ban list who aren't already banned in each server
        for user_id in banned_users:
            for guild in self.bot.guilds:
                try:
                    # Check if the user is not banned in this guild
                    if not await self.is_user_banned_in_guild(user_id, guild):
                        await guild.ban(discord.Object(id=user_id), reason=ban_reasons.get(user_id, "Global ban enforced."))
                        print(f"Banned {user_id} from {guild.name}")
                        await asyncio.sleep(1)  # Prevent rate limits
                except discord.Forbidden:
                    print(f"Failed to ban {user_id} in {guild.name}")
                    continue

    async def is_user_banned_in_guild(self, user_id, guild):
        """Check if the user is already banned in the guild."""
        try:
            bans = await guild.bans()
            return any(ban_entry.user.id == user_id for ban_entry in bans)
        except discord.HTTPException:
            return False

    @commands.command()
    @commands.is_owner()
    async def globalban(self, ctx, user: discord.User, *, reason: str = "No reason provided"):
        """Global ban a user."""
        banned_users = await self.config.banned_users()
        if user.id in banned_users:
            return await ctx.send("User is already globally banned.")
        
        banned_users.append(user.id)
        await self.config.banned_users.set(banned_users)
        await self.config.ban_reasons.set({user.id: reason})

        # Apply the global ban to all servers
        for guild in self.bot.guilds:
            try:
                await guild.ban(user, reason=f"Global Ban: {reason}")
                print(f"Banned {user} from {guild.name} with reason: {reason}")
                await asyncio.sleep(1)  # Prevent rate limits
            except discord.Forbidden:
                print(f"Failed to ban {user} from {guild.name}")
                continue
        await ctx.send(f"{user} has been globally banned.")

    @commands.command()
    @commands.is_owner()
    async def unglobalban(self, ctx, user: discord.User):
        """Remove a global ban and unban the user from all servers."""
        banned_users = await self.config.banned_users()
        if user.id not in banned_users:
            return await ctx.send("User is not globally banned.")
        
        banned_users.remove(user.id)
        await self.config.banned_users.set(banned_users)
        await self.config.ban_reasons.set({user.id: None})

        # Remove the global ban from all servers
        for guild in self.bot.guilds:
            try:
                await guild.unban(user)
                print(f"Unbanned {user} from {guild.name}")
                await asyncio.sleep(1)  # Prevent rate limits
            except discord.Forbidden:
                print(f"Failed to unban {user} from {guild.name}")
                continue
        await ctx.send(f"{user} has been globally unbanned.")

    @commands.command()
    @commands.is_owner()
    async def bansync(self, ctx):
        """Sync the global bans to all servers."""
        await self.sync_bans()
        await ctx.send("Global bans synced.")

    @commands.command()
    @commands.is_owner()
    async def globalbanupdatelist(self, ctx):
        """Update the global ban list and remove duplicates."""
        banned_users = []
        ban_reasons = {}

        for guild in self.bot.guilds:
            print(f"Fetching bans from {guild.name}...")
            try:
                async for ban_entry in guild.bans():
                    user_id = ban_entry.user.id
                    if user_id not in banned_users:
                        banned_users.append(user_id)
                        ban_reasons[user_id] = ban_entry.reason if ban_entry.reason else "No reason provided"
                        print(f"Added {user_id} to global ban list with reason: {ban_entry.reason}")
                    await asyncio.sleep(1)  # Prevent rate limits
            except discord.HTTPException:
                print(f"Failed to fetch bans for {guild.name}")
                continue

        await self.config.banned_users.set(banned_users)
        await self.config.ban_reasons.set(ban_reasons)

        # Log the update
        print(f"Global ban list updated. Total bans: {len(banned_users)}")
        await ctx.send(f"Global ban list updated. Total bans: {len(banned_users)}.")

    @commands.command()
    @commands.is_owner()
    async def globalbanlist(self, ctx):
        """Send the global ban list to the user in chunks of 1500 characters."""
        banned_users = await self.config.banned_users()
        ban_reasons = await self.config.ban_reasons()
        total_bans = len(banned_users)

        if total_bans == 0:
            await ctx.send("No users are globally banned.")
            return

        # Prepare the global ban list
        ban_list = [
            f"**ID:** {user_id}, **Reason:** {ban_reasons.get(user_id, 'No reason provided')}, **Banned by:** {ctx.author}" 
            for user_id in banned_users
        ]
        
        # Split the list into chunks of 1500 characters
        chunk_size = 1500
        for i in range(0, len(ban_list), chunk_size):
            chunk = "\n".join(ban_list[i:i + chunk_size])
            await ctx.author.send(chunk)

        await ctx.send(f"Global ban list sent to your DMs.")

    @commands.command()
    @commands.is_owner()
    async def globaltotalbans(self, ctx):
        """Show the total number of global bans."""
        banned_users = await self.config.banned_users()
        await ctx.send(f"Total global bans: {len(banned_users)}.")

    @commands.command()
    @commands.is_owner()
    async def globalbanlistwipe(self, ctx):
        """Wipe the global ban list with confirmation."""
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
