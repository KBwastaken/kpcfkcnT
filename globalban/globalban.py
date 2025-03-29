import discord
from redbot.core import commands, Config
import asyncio
import logging

log = logging.getLogger("red.globalban")

class GlobalBan(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=1234567890, force_registration=True)
        self.config.register_global(ban_list={})
        self.ban_sync_task = self.bot.loop.create_task(self.ban_sync_loop())
    
    async def ban_sync_loop(self):
        await self.bot.wait_until_ready()
        while True:
            log.info("Starting 12-hour global ban sync...")
            await self.sync_bans()
            log.info("Global ban sync complete. Next sync in 12 hours.")
            await asyncio.sleep(43200)  # 12 hours
    
    async def sync_bans(self):
        ban_list = await self.config.ban_list()
        for guild in self.bot.guilds:
            log.info(f"Syncing bans for {guild.name}...")
            count = 0
            for user_id in ban_list.keys():
                user = discord.Object(id=user_id)
                try:
                    await guild.ban(user, reason="Global ban sync")
                    count += 1
                    if count % 20 == 0:
                        log.info(f"{count} bans synced in {guild.name}")
                    await asyncio.sleep(1)  # Prevent rate limits
                except discord.Forbidden:
                    log.warning(f"No permission to ban in {guild.name}")
                except discord.HTTPException as e:
                    log.error(f"Error banning in {guild.name}: {e}")
            log.info(f"All bans synced in {guild.name} ({count} total).")

    @commands.command()
    async def globalban(self, ctx, user: discord.Member, *, reason="No reason provided"):
        "Ban a user globally"
        ban_list = await self.config.ban_list()
        if str(user.id) in ban_list:
            await ctx.send("User is already globally banned.")
            return
        
        ban_list[str(user.id)] = {"reason": reason, "banned_by": ctx.author.id}
        await self.config.ban_list.set(ban_list)
        
        for guild in self.bot.guilds:
            try:
                await guild.ban(user, reason=f"Global ban: {reason}")
            except discord.Forbidden:
                log.warning(f"No permission to ban {user} in {guild.name}")
            except discord.HTTPException as e:
                log.error(f"Failed to ban {user} in {guild.name}: {e}")
        
        await ctx.send(f"{user} has been globally banned.")
        log.info(f"{user} globally banned by {ctx.author} for: {reason}")

    @commands.command()
    async def unglobalban(self, ctx, user: discord.User):
        "Unban a user globally"
        ban_list = await self.config.ban_list()
        if str(user.id) not in ban_list:
            await ctx.send("User is not globally banned.")
            return
        
        del ban_list[str(user.id)]
        await self.config.ban_list.set(ban_list)
        
        for guild in self.bot.guilds:
            try:
                await guild.unban(user)
            except discord.Forbidden:
                log.warning(f"No permission to unban {user} in {guild.name}")
            except discord.HTTPException as e:
                log.error(f"Failed to unban {user} in {guild.name}: {e}")
        
        await ctx.send(f"{user} has been globally unbanned.")
        log.info(f"{user} globally unbanned by {ctx.author}")

    @commands.command()
    async def globaltotalbans(self, ctx):
        "Count total global bans"
        ban_list = await self.config.ban_list()
        await ctx.send(f"{len(ban_list)} users have been globally banned.")
        log.info(f"Total global bans: {len(ban_list)}")

    @commands.command()
    async def globalbanlist(self, ctx):
        "Send the global ban list"
        ban_list = await self.config.ban_list()
        if not ban_list:
            await ctx.send("No global bans.")
            return
        
        output = "\n".join([f"{uid}: {data['reason']} (by {data['banned_by']})" for uid, data in ban_list.items()])
        if len(output) > 1500:
            await ctx.send("Global ban list too long, sending as file.")
            with open("globalbanlist.txt", "w") as f:
                f.write(output)
            await ctx.send(file=discord.File("globalbanlist.txt"))
        else:
            await ctx.send(f"```{output}```")
        log.info("Sent global ban list.")

    @commands.command()
    async def globalbanlistwipe(self, ctx):
        "Wipe the global ban list"
        await ctx.send("Are you sure? React to confirm.")
        
        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) == "✅"
        
        try:
            reaction, _ = await self.bot.wait_for("reaction_add", timeout=30.0, check=check)
            await self.config.ban_list.set({})
            await ctx.send("Global ban list wiped.")
            log.info("Global ban list wiped.")
        except asyncio.TimeoutError:
            await ctx.send("Wipe cancelled.")

async def setup(bot):
    await bot.add_cog(GlobalBan(bot))
