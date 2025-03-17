import discord
from discord.ext import commands, tasks
from discord.ui import Button, View
from datetime import datetime, timedelta
import re
import asyncio

class DMLogger(commands.Cog):
    """Logs DMs sent to the bot, handles spam detection, blocks users, and provides unblock button."""

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=9876543210, force_registration=True)
        self.config.register_global(dm_guild=None, dm_channel=None)
        
        self.trusted_domains = [
            "youtube.com", "discord.com", "github.com", "twitter.com", 
            "facebook.com", "reddit.com", "twitch.tv"
        ]
        
        self.scam_domains = [
            "bit.ly", "t.co", "tinyurl.com", "shortlink.com", "is.gd", 
            "goo.gl", "freebitco.in", "coinurl.com"
        ]
        
        self.user_spam_data = {}  # To track user messages and time to detect spamming
        self.spam_limit = 15  # Messages in a short time period (5 seconds)
        self.spam_timeframe = 5  # 5 seconds to detect spam
        self.blocked_users = set()  # Set of blocked users

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
        if user.id in self.blocked_users:
            await message.author.send("You are currently blocked for spamming the bot.")
            return  # Block further processing
        
        # Track user spam activity
        now = datetime.utcnow()
        if user.id not in self.user_spam_data:
            self.user_spam_data[user.id] = []
        
        self.user_spam_data[user.id].append(now)
        
        # Remove outdated timestamps (messages outside the spam time frame)
        self.user_spam_data[user.id] = [timestamp for timestamp in self.user_spam_data[user.id] if (now - timestamp).total_seconds() <= self.spam_timeframe]
        
        # If the user has sent more than the allowed amount of messages within the timeframe, block them
        if len(self.user_spam_data[user.id]) > self.spam_limit:
            await self.block_user(user)
            return
        
        # Regular message processing after spam check
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
        
        # Check for suspicious links
        if re.search(r"https?:\/\/(?:www\.)?[^\s]+", message_content):
            if any(domain in message_content for domain in self.scam_domains):
                await channel.send(f"🚨 **Suspicious Link Alert!** 🚨\nUser: {user} ({user.id})\nMessage: {message_content}")
            elif any(domain in message_content for domain in self.trusted_domains):
                pass  # Trusted domains are allowed, no alert
            else:
                await channel.send(f"⚠️ **Link Alert!** ⚠️\nUser: {user} ({user.id})\nMessage: {message_content}")

        embed = discord.Embed(title="DM Received", color=discord.Color.blue(), timestamp=datetime.utcnow())
        embed.add_field(name="From", value=f"{user} ({user.id})", inline=False)
        embed.add_field(name="Message", value=message_content, inline=False)
        embed.set_footer(text=f"Mutual Servers: {mutual_guilds_text}")
        
        await channel.send(embed=embed)

        if message.attachments:
            for attachment in message.attachments:
                await channel.send(f"📎 **Attachment:** {attachment.url}")
        
        if message.stickers:
            for sticker in message.stickers:
                sticker_url = sticker.url
                await channel.send(f"🖼️ **Sticker:** {sticker.name}\n**URL:** {sticker_url}")
        
        for attachment in message.attachments:
            if attachment.filename.endswith(".ogg") or "voice-message" in attachment.filename:
                await channel.send(f"🎙️ **Voice Message:** {attachment.url}")

    async def block_user(self, user: discord.User):
        """Block the user and send a message with an unblock button."""
        self.blocked_users.add(user.id)  # Add to the blocked set
        # Send a message with a button to unblock the user
        unblock_button = Button(label="Unblock User", style=discord.ButtonStyle.green)
        
        async def unblock_callback(interaction):
            if interaction.user.guild_permissions.administrator:
                self.blocked_users.discard(user.id)  # Remove from blocked users
                await interaction.response.send_message(f"User {user} has been unblocked.", ephemeral=True)
                unblock_message = await interaction.channel.fetch_message(interaction.message.id)
                await unblock_message.delete()  # Remove the unblock message once clicked
            else:
                await interaction.response.send_message("You don't have permission to unblock users.", ephemeral=True)
        
        unblock_button.callback = unblock_callback
        view = View()
        view.add_item(unblock_button)
        
        # Send the message with the unblock button and pin it
        unblock_message = await interaction.channel.send(f"User {user} has been blocked for spamming. Click the button below to unblock them.", view=view)
        await unblock_message.pin()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Detects incoming DMs to the bot."""
        if message.guild is None and not message.author.bot:
            await self.send_dm_log(message.author, message)
