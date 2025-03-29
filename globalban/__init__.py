import discord
from discord.ext import commands, tasks
import logging
import asyncio
import yaml

# Set up logging configuration
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

intents = discord.Intents.default()
intents.bans = True  # Make sure to have ban intent enabled

bot = commands.Bot(command_prefix='.', intents=intents)

# Set up the global ban list file path
ban_list_file = "global_ban_list.yaml"

# Initialize the global banned users list
banned_users = []

# Helper function to load the ban list from the file
def load_ban_list():
    global banned_users
    try:
        with open(ban_list_file, 'r') as f:
            banned_users = yaml.safe_load(f) or []
    except FileNotFoundError:
        banned_users = []

# Helper function to save the ban list to the file
def save_ban_list():
    with open(ban_list_file, 'w') as f:
        yaml.safe_dump(banned_users, f)

# Function to check if a user is globally banned
def is_globally_banned(user_id):
    return user_id in [ban_entry['user_id'] for ban_entry in banned_users]

# Initialize bot when it's ready
@bot.event
async def on_ready():
    load_ban_list()
    log.info(f"Logged in as {bot.user}")
    log.info(f"Global ban list loaded with {len(banned_users)} bans.")
