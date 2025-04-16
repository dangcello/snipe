import discord
import asyncio
from discord.ext import commands
from collections import defaultdict
import json
import os

TOKEN = os.getenv("DISCORD_BOT_TOKEN")

if not TOKEN:
    raise ValueError("DISCORD_BOT_TOKEN is missing! Set it in Railway environment variables.")

DATA_FILE = "leaderboard.json"

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            data = json.load(f)
            print(f"📂 Loaded data: {data}")  # Debug log
            return data
    else:
        print("⚠️ No leaderboard.json found, creating a new one.")
        return {"image_count": {}, "tagged_count": {}}  # Empty leaderboard


def save_data():
    print(f"📁 Saving data... {dict(image_count)}")  # Debug log
    with open(DATA_FILE, "w") as f:
        json.dump({
            "image_count": dict(image_count),
            "tagged_count": dict(tagged_count)
        }, f)


# Load existing data at startup
data = load_data()
image_count = defaultdict(int, data["image_count"])
tagged_count = defaultdict(int, data["tagged_count"])

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

SNIPED_CHANNEL_NAME = "snipped"

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")

    # Reset counts before recalculating from history
    global image_count, tagged_count
    image_count.clear()
    tagged_count.clear()

    for guild in bot.guilds:
        for channel in guild.text_channels:
            if channel.name == SNIPED_CHANNEL_NAME:
                print(f"📂 Rescanning past messages in #{channel.name}...")

                async for message in channel.history(limit=10000):
                    process_message(message)
                
                save_data()  # Save recalculated leaderboard

                print("✅ Past messages reprocessed! Leaderboard corrected.")

def process_message(message):
    """Helper function to process messages for leaderboard"""
    print(f"📥 Processing message from {message.author}...")  # Debug log

    # Check if message contains image attachments
    for attachment in message.attachments:
        if any(attachment.filename.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp']):
            image_count[message.author.id] += 1
            print(f"✅ {message.author} uploaded an image. Total: {image_count[message.author.id]}")  # Debug log

    # Check if the message tags users (excluding bot messages)
    if message.mentions and not message.author.bot and not message.reference:
        for user in message.mentions:
            tagged_count[user.id] += 1
            print(f"✅ {user} was tagged. Total: {tagged_count[user.id]}")  # Debug log


@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if message.channel.name == SNIPED_CHANNEL_NAME:
        # Store previous count
        prev_count = image_count[message.author.id]

        # Process the message
        process_message(message)

        # Only send a message if an image count increased
        if image_count[message.author.id] > prev_count:
            save_data()
            await message.channel.send(f"{message.author.mention} Sniped Someone! Leaderboard updated.")
    
    await bot.process_commands(message)


@bot.event
async def on_message_edit(before, after):
    """Track edited messages (optional)"""
    if before.channel.name == SNIPED_CHANNEL_NAME:
        process_message(after)
        save_data()

@bot.command()
async def leaderboard(ctx):
    """Shows the full leaderboard for kills and deaths"""
    if not image_count and not tagged_count:
        await ctx.send("No data available yet!")
        return

    kills_sorted = sorted(image_count.items(), key=lambda x: x[1], reverse=True)
    deaths_sorted = sorted(tagged_count.items(), key=lambda x: x[1], reverse=True)

    leaderboard_msg = "**🔪 Kills Leaderboard 🔪**\n"
    for idx, (user_id, count) in enumerate(kills_sorted, start=1):
        user = bot.get_user(user_id) or f"Unknown User ({user_id})"
        leaderboard_msg += f"{idx}. {user} - {count} kills\n"

    leaderboard_msg += "\n**💀 Deaths Leaderboard 💀**\n"
    for idx, (user_id, count) in enumerate(deaths_sorted, start=1):
        user = bot.get_user(user_id) or f"Unknown User ({user_id})"
        leaderboard_msg += f"{idx}. {user} - {count} deaths\n"

    # Split if message is longer than 2000 characters
    chunks = [leaderboard_msg[i:i+2000] for i in range(0, len(leaderboard_msg), 2000)]
    for chunk in chunks:
        await ctx.send(chunk)
        await asyncio.sleep(1)  # Delay to avoid hitting rate limit

@bot.command()
@commands.has_permissions(manage_messages=True)  # Only users with manage_messages permission can execute this
async def set_kills(ctx, user: discord.User, kills: int):
    """Manually set the kills (images uploaded) count for a user"""
    image_count[user.id] = kills
    save_data()
    await ctx.send(f"✅ {user} now has {kills} kills (images uploaded)!")

@bot.command()
@commands.has_permissions(manage_messages=True)  # Only users with manage_messages permission can execute this
async def set_deaths(ctx, user: discord.User, deaths: int):
    """Manually set the deaths (tags) count for a user"""
    tagged_count[user.id] = deaths
    save_data()
    await ctx.send(f"✅ {user} now has {deaths} deaths (tags)!")


@bot.command()
async def reset_leaderboard(ctx):
    """Resets the leaderboard"""
    global image_count, tagged_count
    image_count.clear()
    tagged_count.clear()
    save_data()
    await ctx.send("Leaderboard has been reset!")


# Run the bot
bot.run(TOKEN)
