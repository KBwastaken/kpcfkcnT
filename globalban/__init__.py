import discord
from discord.ext import commands
import logging

# Set up logging configuration
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

intents = discord.Intents.default()
intents.bans = True  # Make sure to have ban intent enabled

bot = commands.Bot(command_prefix='.', intents=intents)

# Function to initialize the bot
def setup(bot):
    log.info("Initializing bot...")
    bot.load_extension('globalban')  # Load the globalban extension

# Setup the bot
setup(bot)
