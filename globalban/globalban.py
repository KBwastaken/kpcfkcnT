import discord
from discord.ext import commands
from discord.ui import Button, View
import json
import asyncio

class GlobalBanCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.globalbans = self.loadbans()  # Load any pre-existing global bans
        self.allowedroles = []  # List to store roles allowed to use .globalban command
        self.loggingchannel = None  # Channel for global ban logs

    def loadbans(self):
        # Load the global bans from a JSON file (can be replaced with database logic if needed)
        try:
            with open('globalbans.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    def savebans(self):
        with open('globalbans.json', 'w') as f:
            json.dump(self.globalbans, f, indent=4)

    @commands.command()
    @commands.is_owner()
    async def globalban(self, ctx, user: discord.User, reason: str):
        """Globally ban a user across all servers the bot is in."""
        if not self.checkpermission(ctx):
            await ctx.send("You do not have permission to use this command.")
            return
        
        # Ensure the user is not already globally banned
        if str(user.id) in self.globalbans:
            await ctx.send(f"{user} is already globally banned.")
            return
        
        # Log the ban and execute the global ban
        self.globalbans[str(user.id)] = {
            "reason": reason,
            "bannedby": ctx.author.name,
            "bannedat": str(ctx.message.created_at)
        }
        self.savebans()

        # Embed for ban confirmation
        embed = discord.Embed(title=f"Global Ban: {user}", description=reason, color=discord.Color.red())
        embed.add_field(name="User", value=f"{user.name} | {user.id}")
        embed.add_field(name="Banned By", value=ctx.author.name)
        embed.add_field(name="Server", value=ctx.guild.name)

        # Buttons for approval
        approvebutton = Button(label="Approve", style=discord.ButtonStyle.green)
        denybutton = Button(label="Deny", style=discord.ButtonStyle.red)
        escalatebutton = Button(label="Escalate to Cybersecurity", style=discord.ButtonStyle.blurple)

        # Add button interactions
        view = View()
        view.add_item(approvebutton)
        view.add_item(denybutton)
        view.add_item(escalatebutton)

        # Send the embed to the logging channel
        if self.loggingchannel:
            await self.loggingchannel.send(embed=embed, view=view)
        
        # Ban the user from all servers the bot is in
        for guild in self.bot.guilds:
            try:
                member = guild.get_member(user.id)
                if member:
                    await member.ban(reason=f"Global ban: {reason}")
            except discord.DiscordException:
                continue

        await ctx.send(f"{user} has been globally banned.")

    def checkpermission(self, ctx):
        """Check if the user has the required role or permission to execute the globalban command."""
        if any(role.id in self.allowedroles for role in ctx.author.roles):
            return True
        return False

    @commands.command()
    async def globalbanlist(self, ctx):
        """List all globally banned users."""
        bannedusers = "\n".join([f"{user_id}: {data['reason']}" for user_id, data in self.globalbans.items()])
        if bannedusers:
            await ctx.send(f"Global Ban List:\n{bannedusers}")
        else:
            await ctx.send("No users are globally banned.")

    @commands.command()
    @commands.is_owner()
    async def globalbanallow(self, ctx, role: discord.Role):
        """Allow a specific role to execute the .globalban command."""
        if role.id not in self.allowedroles:
            self.allowedroles.append(role.id)
            await ctx.send(f"Role {role.name} is now allowed to execute globalban.")
        else:
            await ctx.send(f"Role {role.name} is already allowed to execute globalban.")

    @commands.command()
    @commands.is_owner()
    async def globalbanset(self, ctx, channel: discord.TextChannel):
        """Set a specific channel to log global bans."""
        self.loggingchannel = channel
        await ctx.send(f"Global ban logs will be sent to {channel.mention}.")

    @commands.command()
    async def unban(self, ctx, user: discord.User):
        """Unban a user from the global ban list."""
        if str(user.id) in self.globalbans:
            del self.globalbans[str(user.id)]
            self.savebans()
            await ctx.send(f"{user} has been unglobally banned.")
        else:
            await ctx.send(f"{user} is not globally banned.")

    @commands.command()
    @commands.is_owner()
    async def syncglobalbans(self, ctx):
        """Sync global bans across servers."""
        for guild in self.bot.guilds:
            for user_id in self.globalbans:
                member = guild.get_member(int(user_id))
                if member:
                    await member.ban(reason=f"Global ban: {self.globalbans[user_id]['reason']}")
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
