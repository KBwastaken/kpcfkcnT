import discord
from discord.ext import commands
from discord.ui import Button, View
import json
import asyncio

class GlobalBanCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.global_bans = self.load_bans()  # Load any pre-existing global bans
        self.allowed_roles = []  # List to store roles allowed to use .globalban command
        self.logging_channel = None  # Channel for global ban logs

    def load_bans(self):
        # Load the global bans from a JSON file (can be replaced with database logic if needed)
        try:
            with open('global_bans.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    def save_bans(self):
        with open('global_bans.json', 'w') as f:
            json.dump(self.global_bans, f, indent=4)

    @commands.command()
    @commands.is_owner()
    async def globalban(self, ctx, user: discord.User, reason: str):
        """Globally ban a user across all servers the bot is in."""
        if not self.check_permission(ctx):
            await ctx.send("You do not have permission to use this command.")
            return
        
        # Ensure the user is not already globally banned
        if str(user.id) in self.global_bans:
            await ctx.send(f"{user} is already globally banned.")
            return
        
        # Log the ban and execute the global ban
        self.global_bans[str(user.id)] = {
            "reason": reason,
            "banned_by": ctx.author.name,
            "banned_at": str(ctx.message.created_at)
        }
        self.save_bans()

        # Embed for ban confirmation
        embed = discord.Embed(title=f"Global Ban: {user}", description=reason, color=discord.Color.red())
        embed.add_field(name="User", value=f"{user.name} | {user.id}")
        embed.add_field(name="Banned By", value=ctx.author.name)
        embed.add_field(name="Server", value=ctx.guild.name)

        # Buttons for approval
        approve_button = Button(label="Approve", style=discord.ButtonStyle.green)
        deny_button = Button(label="Deny", style=discord.ButtonStyle.red)
        escalate_button = Button(label="Escalate to Cybersecurity", style=discord.ButtonStyle.blurple)

        # Add button interactions
        view = View()
        view.add_item(approve_button)
        view.add_item(deny_button)
        view.add_item(escalate_button)

        # Send the embed to the logging channel
        if self.logging_channel:
            await self.logging_channel.send(embed=embed, view=view)
        
        # Ban the user from all servers the bot is in
        for guild in self.bot.guilds:
            try:
                member = guild.get_member(user.id)
                if member:
                    await member.ban(reason=f"Global ban: {reason}")
            except discord.DiscordException:
                continue

        await ctx.send(f"{user} has been globally banned.")

    def check_permission(self, ctx):
        """Check if the user has the required role or permission to execute the globalban command."""
        if any(role.id in self.allowed_roles for role in ctx.author.roles):
            return True
        return False

    @commands.command()
    async def globalbanlist(self, ctx):
        """List all globally banned users."""
        banned_users = "\n".join([f"{user_id}: {data['reason']}" for user_id, data in self.global_bans.items()])
        if banned_users:
            await ctx.send(f"Global Ban List:\n{banned_users}")
        else:
            await ctx.send("No users are globally banned.")

    @commands.command()
    @commands.is_owner()
    async def globalbanallow(self, ctx, role: discord.Role):
        """Allow a specific role to execute the .globalban command."""
        if role.id not in self.allowed_roles:
            self.allowed_roles.append(role.id)
            await ctx.send(f"Role {role.name} is now allowed to execute globalban.")
        else:
            await ctx.send(f"Role {role.name} is already allowed to execute globalban.")

    @commands.command()
    @commands.is_owner()
    async def globalbanset(self, ctx, channel: discord.TextChannel):
        """Set a specific channel to log global bans."""
        self.logging_channel = channel
        await ctx.send(f"Global ban logs will be sent to {channel.mention}.")

    @commands.command()
    async def unban(self, ctx, user: discord.User):
        """Unban a user from the global ban list."""
        if str(user.id) in self.global_bans:
            del self.global_bans[str(user.id)]
            self.save_bans()
            await ctx.send(f"{user} has been unglobally banned.")
        else:
            await ctx.send(f"{user} is not globally banned.")

    @commands.command()
    @commands.is_owner()
    async def sync_globalbans(self, ctx):
        """Sync global bans across servers."""
        for guild in self.bot.guilds:
            for user_id in self.global_bans:
                member = guild.get_member(int(user_id))
                if member:
                    await member.ban(reason=f"Global ban: {self.global_bans[user_id]['reason']}")
        await ctx.send("Global bans have been synced.")

    @commands.Cog.listener()
    async def on_button_click(self, interaction: discord.Interaction):
        """Handle button clicks for global ban approvals and denials."""
        if interaction.component.label == "Approve":
            # Approve the global ban and make all buttons unclickable
            await interaction.message.edit(view=None)
            await interaction.response.send_message(f"Approved by {interaction.user.name}.", ephemeral=True)
        elif interaction.component.label == "Deny":
            # Deny the global ban and unban the user
            user_id = int(interaction.message.embeds[0].fields[0].value.split(":")[1].strip())
            user = self.bot.get_user(user_id)
            if user:
                for guild in self.bot.guilds:
                    try:
                        await guild.unban(user)
                    except discord.DiscordException:
                        continue
            await interaction.message.edit(view=None)
            await interaction.response.send_message(f"{user} has been unbanned.", ephemeral=True)
        elif interaction.component.label == "Escalate to Cybersecurity":
            # Handle escalation
            await interaction.message.edit(view=None)
            await interaction.response.send_message(f"Escalated to Cybersecurity.", ephemeral=True)

def setup(bot):
    bot.add_cog(GlobalBanCog(bot))
