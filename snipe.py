import discord
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

    for guild in bot.guilds:
        for channel in guild.text_channels:
            if channel.name == SNIPED_CHANNEL_NAME:
                print(f"📂 Scanning past messages in #{channel.name}...")

                async for message in channel.history(limit=10000):
                    process_message(message)
                
                # Save updated counts after processing all messages
                save_data()

                print("✅ Past messages processed and leaderboard updated!")


def process_message(message):
    """Helper function to process messages for leaderboard"""
    print(f"📥 Processing message from {message.author}...")  # Debug log

    # Check if message contains image attachments
    for attachment in message.attachments:
        if any(attachment.filename.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp']):
            image_count[message.author.id] += 1
            print(f"✅ {message.author} uploaded an image. Total: {image_count[message.author.id]}")  # Debug log

    # Check if the message tags users
    if message.mentions:
        for user in message.mentions:
            tagged_count[user.id] += 1
            print(f"✅ {user} was tagged. Total: {tagged_count[user.id]}")  # Debug log


@bot.event
async def on_message(message):
    if message.author.bot:
        return
    if message.channel.name == SNIPED_CHANNEL_NAME:
        process_message(message)
        save_data()
        await message.channel.send(f"{message.author.mention} uploaded an image! Leaderboard updated.")
    await bot.process_commands(message)

@bot.event
async def on_message_edit(before, after):
    """Track edited messages (optional)"""
    if before.channel.name == SNIPED_CHANNEL_NAME:
        process_message(after)
        save_data()

@bot.command()
async def leaderboard(ctx):
    """Shows the leaderboard for image posts and tags"""
    if not image_count:
        await ctx.send("No one has uploaded any images yet!")
        return

    image_sorted = sorted(image_count.items(), key=lambda x: x[1], reverse=True)
    tagged_sorted = sorted(tagged_count.items(), key=lambda x: x[1], reverse=True)

    leaderboard_msg = "**📸 Image Leaderboard 📸**\n"
    for idx, (user_id, count) in enumerate(image_sorted[:10], start=1):
        user = bot.get_user(user_id) or f"Unknown User ({user_id})"
        leaderboard_msg += f"{idx}. {user} - {count} images\n"

    leaderboard_msg += "\n**🏷️ Tagged Leaderboard 🏷️**\n"
    for idx, (user_id, count) in enumerate(tagged_sorted[:10], start=1):
        user = bot.get_user(user_id) or f"Unknown User ({user_id})"
        leaderboard_msg += f"{idx}. {user} - {count} times tagged\n"

    await ctx.send(leaderboard_msg)

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
