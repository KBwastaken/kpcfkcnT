import logging
import discord
from discord.ext import commands
from dotenv import load_dotenv
import os

# Load environment variables from the .env file
load_dotenv()

# Retrieve the bot token from the environment
TOKEN = os.getenv("DISCORD_TOKEN")

# Set up logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

# Define intents for the bot
intents = discord.Intents.default()
intents.bans = True  # Ensure the bot has permission to access ban events

# Initialize the bot
bot = commands.Bot(command_prefix='.', intents=intents)

# Function to run the bot
if __name__ == "__main__":
    if TOKEN is None:
        log.error("Bot token is missing. Please set the DISCORD_TOKEN environment variable.")
    else:
        bot.run(TOKEN)
