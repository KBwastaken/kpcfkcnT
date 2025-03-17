import discord
from redbot.core import commands, Config
from redbot.core.bot import Red
from datetime import datetime

class DMLogger(commands.Cog):
    """Logs DMs sent to the bot and forwards them to a designated server/channel."""

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=9876543210, force_registration=True)
        self.config.register_global(dm_guild=None, dm_channel=None)

    @commands.admin()
    @commands.command()
    async def dmset(self, ctx, guild_id: int, channel_id: int):
        """Set the server and channel where DMs should be logged."""
        guild = self.bot.get_guild(guild_id)
        if not guild:
            return await ctx.send("Invalid Guild ID or bot is not in the server.")
        
        channel = guild.get_channel(channel_id)
        if not channel:
            return await ctx.send("Invalid Channel ID or bot lacks permission.")
        
        await self.config.dm_guild.set(guild_id)
        await self.config.dm_channel.set(channel_id)
        await ctx.send(f"DMs will now be logged in {guild.name} - {channel.mention}")

    async def send_dm_log(self, user: discord.User, message: discord.Message):
        """Handles forwarding the DM to the configured channel."""
        guild_id = await self.config.dm_guild()
        channel_id = await self.config.dm_channel()
        
        if not guild_id or not channel_id:
            return  # No setup found
        
        guild = self.bot.get_guild(guild_id)
        if not guild:
            return
        
        channel = guild.get_channel(channel_id)
        if not channel:
            return
        
        mutual_guilds = [g.name for g in self.bot.guilds if g.get_member(user.id)]
        mutual_guilds_text = ", ".join(mutual_guilds) if mutual_guilds else "None"
        
        message_content = message.content or "*No text content*"
        if len(message_content) > 1024:
            message_content = message_content[:1020] + "... (truncated)"
        
        embed = discord.Embed(title="DM Received", color=discord.Color.blue(), timestamp=datetime.utcnow())
        embed.add_field(name="From", value=f"{user} ({user.id})", inline=False)
        embed.add_field(name="Message", value=message_content, inline=False)
        embed.set_footer(text=f"Mutual Servers: {mutual_guilds_text}")
        
        await channel.send(embed=embed)
        
        # Send attachments separately
        if message.attachments:
            attachment_urls = [att.url for att in message.attachments if att.url]
            for url in attachment_urls:
                await channel.send(f"📎 **Attachment:** {url}")
        
        # Send stickers separately
        if message.stickers:
            for sticker in message.stickers:
                await channel.send(f"🖼️ **Sticker:** {sticker.name}\n{sticker.url}")
        
        # Voice message detection (if applicable)
        for attachment in message.attachments:
            if attachment.filename.endswith(".ogg") or "voice-message" in attachment.filename:
                await channel.send(f"🎙️ **Voice Message:** {attachment.url}")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Detects incoming DMs to the bot."""
        if message.guild is None and not message.author.bot:
            await self.send_dm_log(message.author, message) 

async def setup(bot: Red):
    await bot.add_cog(DMLogger(bot))
