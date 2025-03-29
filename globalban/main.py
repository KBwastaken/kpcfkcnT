from init import bot, log, banned_users, save_ban_list, is_globally_banned
import discord
from discord.ext import commands, tasks
import asyncio

@bot.command(name='globalban')
async def globalban(ctx, user: discord.User, *, reason=None):
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
    
    for guild in bot.guilds:
        try:
            await guild.ban(user, reason=reason)
            log.info(f"Banned {user} from {guild.name} (Reason: {reason})")
        except discord.Forbidden:
            log.error(f"Could not ban {user} from {guild.name} due to lack of permissions.")
    
    await ctx.send(f"{user} has been globally banned.")
    log.info(f"{user} has been globally banned.")

@bot.command(name='unglobalban')
async def unglobalban(ctx, user: discord.User):
    """Remove a global ban and unban the user from all servers."""
    global banned_users
    banned_users = [ban for ban in banned_users if ban['user_id'] != user.id]
    save_ban_list()
    
    for guild in bot.guilds:
        try:
            await guild.unban(user)
            log.info(f"Unbanned {user} from {guild.name}.")
        except discord.Forbidden:
            log.error(f"Could not unban {user} from {guild.name} due to lack of permissions.")
    
    await ctx.send(f"{user} has been unglobally banned.")
    log.info(f"{user} has been unglobally banned.")

@bot.command(name='globaltotalbans')
async def globaltotalbans(ctx):
    """Show the total number of global bans."""
    await ctx.send(f"There are {len(banned_users)} globally banned users.")

@bot.command(name='globalbanlist')
async def globalbanlist(ctx):
    """Send the list of globally banned users."""
    if not banned_users:
        await ctx.send("No globally banned users.")
        return
    
    # Send the banned users list in chunks of 1500 characters
    user_data = "\n".join([f"{user['username']} (ID: {user['user_id']}) - Reason: {user['reason']}" for user in banned_users])
    chunk_size = 1500
    for i in range(0, len(user_data), chunk_size):
        await ctx.send(user_data[i:i + chunk_size])

@bot.command(name='globalbanupdatelist')
async def globalbanupdatelist(ctx):
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

@bot.command(name='bansync')
async def bansync(ctx):
    """Sync bans with the list, overriding 12h rotation."""
    if not banned_users:
        await ctx.send("No bans on the global list.")
        return
    
    total_synced = 0
    for guild in bot.guilds:
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

@bot.command(name='globalbanlistwipe')
async def globalbanlistwipe(ctx):
    """Wipe the entire global ban list."""
    await ctx.send("Are you sure you want to wipe the global ban list? React with ✅ to confirm.")
    
    def check(reaction, user):
        return user == ctx.author and str(reaction.emoji) == '✅'
    
    try:
        reaction, _ = await bot.wait_for('reaction_add', check=check, timeout=60)
        if reaction:
            banned_users.clear()
            save_ban_list()
            await ctx.send("Global ban list has been wiped.")
            log.info("Global ban list has been wiped.")
    except asyncio.TimeoutError:
        await ctx.send("Global ban list wipe cancelled.")

bot.run('YOUR_BOT_TOKEN')
