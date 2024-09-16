import discord
from discord.ext import commands
import asyncio
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Get the token from the .env file
TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Dictionary to store which voice channel the user joined
user_voice_channels = {}

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

@bot.command(name="join")
async def join_channel(ctx, *, channel_identifier: str):
    """Join a voice channel by ID or #name"""
    guild = ctx.guild

    # Try to find by ID
    channel = discord.utils.get(guild.voice_channels, id=int(channel_identifier)) if channel_identifier.isdigit() else None

    # Try to find by name if not found by ID
    if not channel:
        channel = discord.utils.get(guild.voice_channels, name=channel_identifier.strip('#'))

    if channel:
        voice_client = await channel.connect()
        user_voice_channels[ctx.author.id] = voice_client
        await ctx.send(f"Joined {channel.name}!")
    else:
        await ctx.send(f"Could not find a voice channel by ID or name: {channel_identifier}")

@bot.command(name="choose")
async def choose_audio(ctx, audio_file: str):
    """Play the selected audio file in the joined channel"""
    user_id = ctx.author.id

    # Check if the user has joined a voice channel
    if user_id not in user_voice_channels:
        await ctx.send("You need to join a voice channel first using !join.")
        return

    voice_client = user_voice_channels[user_id]

    # Play the audio file
    if not os.path.exists(audio_file):
        await ctx.send(f"Audio file {audio_file} does not exist.")
        return

    # Check if the bot is already playing something
    if voice_client.is_playing():
        voice_client.stop()

    voice_client.play(discord.FFmpegPCMAudio(audio_file))

    # Wait until the audio is finished
    while voice_client.is_playing():
        await asyncio.sleep(1)

    # Disconnect after the audio is finished
    await voice_client.disconnect()
    del user_voice_channels[user_id]
    await ctx.send(f"Finished playing {audio_file} and left the voice channel.")


bot.run(TOKEN)
