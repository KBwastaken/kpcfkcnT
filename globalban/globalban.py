# globalban.py
import discord
import yaml
import asyncio
from redbot.core import commands, Config, checks
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
        await ctx.author.send(file=discord.File("globalbans.yaml"))
        await ctx.send("Global ban list sent to your DMs.")


def setup(bot):
    bot.add_cog(GlobalBan(bot))
