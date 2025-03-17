import discord
from redbot.core import commands, Config
from redbot.core.bot import Red
from datetime import datetime
import re
import tempfile
import os

class DMLogger(commands.Cog):
    """Logs DMs sent to the bot and forwards them to a designated server/channel."""

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=9876543210, force_registration=True)
        self.config.register_global(dm_guild=None, dm_channel=None)
        
        # Predefined list of trusted domains
        self.trusted_domains = [
            "youtube.com",   # All YouTube domains allowed (including youtu.be)
            "discord.com",   # Discord links allowed
            "github.com",    # GitHub links allowed
            "twitter.com",   # Twitter links allowed
            "facebook.com",  # Facebook links allowed
            "reddit.com",    # Reddit links allowed
            "twitch.tv",     # Twitch links allowed
        ]

        # Predefined list of known scam/malicious domains
        self.scam_domains = [
            "bit.ly",        # URL shortener often used for scams
            "t.co",          # Twitter's short URL
            "tinyurl.com",   # URL shortener often misused
            "shortlink.com", # Spammy URL shortener
            "is.gd",         # URL shortener associated with spam
            "goo.gl",        # Retired short URL, but could still be used for malicious purposes
            "freebitco.in",  # Known for spam and fraud
            "coinurl.com",   # URL shortener for crypto scams
        ]

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
        # Ensure the message content does not exceed 1024 characters for embeds
        if len(message_content) > 1020:
            message_content = message_content[:1020] + "... (truncated)"
        
        # Check for suspicious or untrusted links
        suspicious_links = []
        for link in re.findall(r"https?:\/\/(?:www\.)?[^\s]+", message_content):
            domain = link.split("/")[2]
            
            # Block known scam domains
            elif domain in self.scam_domains:
                suspicious_links.append(link)
            elif domain not in self.trusted_domains:  # Allow other trusted domains
                suspicious_links.append(link)

        if suspicious_links:
            await channel.send(f"🚨 **Untrusted Link Alert!** 🚨\nUser: {user} ({user.id})\nMessage: {message_content}")
        
        # Check if the message is too long and handle it
        if len(message_content) > 1024:  # Discord message length limit for embeds
            # Save to a temporary .txt file if the message is too long for an embed
            with tempfile.NamedTemporaryFile(delete=False, mode="w", encoding="utf-8", suffix=".txt") as f:
                file_path = f.name
                f.write(f"DM from {user} ({user.id})\n")
                f.write(f"Message: {message_content}\n")
                f.write(f"Mutual Servers: {mutual_guilds_text}\n")

            # Send the file to the channel
            await channel.send(f"🚨 **Message too long!** 🚨\nSending as a file instead:", file=discord.File(file_path))
            os.remove(file_path)  # Clean up the file after sending
        else:
            # Ensure the embed fields are not too long
            embed = discord.Embed(title="DM Received", color=discord.Color.blue(), timestamp=datetime.utcnow())
            embed.add_field(name="From", value=f"{user} ({user.id})", inline=False)
            embed.add_field(name="Message", value=message_content, inline=False)
            embed.set_footer(text=f"Mutual Servers: {mutual_guilds_text}")
            
            await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Detects incoming DMs to the bot."""
        if message.guild is None and not message.author.bot:
            await self.send_dm_log(message.author, message)
