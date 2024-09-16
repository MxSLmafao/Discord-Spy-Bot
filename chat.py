import discord
import asyncio
import os
from dotenv import load_dotenv
import aioconsole
import yaml
from datetime import datetime, timedelta

# Load the .env file and its variables
load_dotenv()

# Get the bot token from the .env file
bot_token = os.getenv("DISCORD_TOKEN")

# Load the config.yml file
with open("config.yml", "r") as file:
    config = yaml.safe_load(file)

admin_user_ids = config.get('admin_user_id', [])  # Load admin user IDs from config.yml

# Ensure that the token is loaded correctly
if not bot_token:
    raise ValueError("Bot token not found. Please check your /tokens/.env file and ensure it contains 'DISCORD_TOKEN'.")

intents = discord.Intents.default()
intents.message_content = True  # Enable message content access
intents.guilds = True  # Enable guild (server) related events
intents.messages = True  # Enable message events
intents.reactions = True  # Enable reactions

client = discord.Client(intents=intents)

selected_channel = None  # This will hold the channel the user selects
pause_display = False  # This controls whether new messages are displayed
current_mode = None  # This will store the current mode (read, chat, both)

@client.event
async def on_ready():
    print(f'Logged in as {client.user} (ID: {client.user.id})')
    print('------')

    # List all guilds (servers) the bot is in
    await select_guild()

@client.event
async def on_message(message):
    if message.channel == selected_channel and not pause_display:
        if message.author != client.user:
            print(f"{message.author.display_name}: {message.content}")
    
    # Handle the $rm command
    if message.content.startswith('$rm'):
        await handle_rm(message)

async def handle_rm(message):
    """List suggestions and allow the user to delete one by selecting a number."""
    # Check if the user has admin permissions
    if str(message.author.id) not in admin_user_ids:
        await message.channel.send("You don't have permission to use this command.")
        return

    suggestion_channel = client.get_channel(suggestion_channel_id)
    
    if suggestion_channel is None:
        await message.channel.send("Unable to find the suggestion channel.")
        return
    
    # Fetch the last 100 suggestions
    suggestions = []
    async for msg in suggestion_channel.history(limit=100):
        if msg.author == client.user and msg.embeds:
            suggestions.append(msg)

    if not suggestions:
        await message.channel.send("No suggestions found.")
        return
    
    # List suggestions with numbers
    list_message = "Suggestions:\n"
    for i, suggestion_msg in enumerate(suggestions, start=1):
        embed = suggestion_msg.embeds[0]
        list_message += f"{i}. {embed.description}\n"
    
    await message.channel.send(list_message)
    
    # Ask the user which suggestion to delete
    await message.channel.send("Enter the number of the suggestion to delete:")

    def check(m):
        return m.author == message.author and m.content.isdigit()

    try:
        response = await client.wait_for('message', check=check, timeout=30.0)
        suggestion_num = int(response.content) - 1

        if 0 <= suggestion_num < len(suggestions):
            await suggestions[suggestion_num].delete()
            await message.channel.send(f"Suggestion {suggestion_num + 1} has been deleted.")
        else:
            await message.channel.send("Invalid selection.")
    except asyncio.TimeoutError:
        await message.channel.send("You took too long to respond.")

# Monitor channel in read-only mode
async def monitor_channel():
    """Continuously listen for new messages in the selected channel and display them."""
    async for message in selected_channel.history(limit=10, oldest_first=False):
        if message.author != client.user:
            print(f"{message.author.display_name}: {message.content}")

# Monitor channel for both mode (view and send messages alternately)
async def monitor_channel_both_mode():
    """ Continuously listen for new messages in the selected channel and display them unless paused. """
    global pause_display
    async for message in selected_channel.history(limit=10, oldest_first=False):
        if message.author != client.user:
            print(f"{message.author.display_name}: {message.content}")

# Toggle chat input in both mode
async def toggle_chat_in_both_mode():
    """ Alternates between message display and input in Both Mode."""
    global pause_display
    while True:
        # Display a message to ask for input asynchronously
        await aioconsole.ainput("Press Enter to send a message...")

        pause_display = True  # Pause message display

        message_content = await aioconsole.ainput("Enter your message (or type 'exit' to quit, or press 'c' to change mode): ")
        if message_content.lower() == "exit":
            print("Exiting...")
            await client.close()
            break
        elif message_content.lower() == 'c':
            print("Switching mode...")
            await switch_mode()  # Trigger mode switch
        else:
            await selected_channel.send(message_content)
            print(f"Message sent to {selected_channel.name}")
            pause_display = False  # Resume message display

# Send messages in chat mode
async def send_messages():
    """Allow the user to send messages by typing in the console."""
    while True:
        await aioconsole.ainput("Press Enter to send a message...")
        message_content = await aioconsole.ainput("Enter your message (or type 'exit' to quit, or press 'c' to change mode): ")
        if message_content.lower() == "exit":
            print("Exiting...")
            await client.close()
            break
        elif message_content.lower() == 'c':
            print("Switching mode...")
            await switch_mode()  # Trigger mode switch
        else:
            await selected_channel.send(message_content)
            print(f"Message sent to {selected_channel.name}")

async def check_permissions(channel):
    permissions = channel.permissions_for(channel.guild.me)  # Get bot's permissions for the channel
    if not permissions.read_messages or not permissions.read_message_history:
        print(f"Bot doesn't have permission to read messages in {channel.name}")
        return False
    return True

# Show messages from past 10 minutes or the last 20 messages if none found
async def show_past_messages():
    """Fetch and display messages from the past 10 minutes, with a fallback to last 20 messages."""
    if not await check_permissions(selected_channel):
        print("Cannot fetch messages due to lack of permissions.")
        await select_guild()  # Proceed to next guild selection
        return
    
    print("Fetching messages from the past 10 minutes...")
    now = datetime.utcnow()
    ten_minutes_ago = now - timedelta(minutes=10)

    # Fetch messages from the last 10 minutes
    messages_in_past_10min = []
    async for message in selected_channel.history(limit=100, after=ten_minutes_ago):
        messages_in_past_10min.append(message)

    # Check if any messages were found in the last 10 minutes
    if messages_in_past_10min:
        for message in messages_in_past_10min:
            print(f"{message.author.display_name}: {message.content}")
    else:
        print("No messages in the past 10 minutes. Fetching the last 20 messages...")
        async for message in selected_channel.history(limit=20):
            print(f"{message.author.display_name}: {message.content}")
    
    print("Finished displaying messages.")
    await select_guild()

async def select_guild():
    """Prompt the user to select a guild."""
    guilds = client.guilds
    for index, guild in enumerate(guilds, start=1):
        print(f"{index}. {guild.name} (ID: {guild.id})")

    # Ask the user to choose a guild by number
    guild_number = int(await aioconsole.ainput("Enter the number of the guild to join: ")) - 1
    selected_guild = guilds[guild_number]
    print(f"Selected guild: {selected_guild.name}")

    # Now list all text channels in the selected guild
    await select_channel(selected_guild)

async def select_channel(guild):
    """Prompt the user to select a channel."""
    global selected_channel
    text_channels = guild.text_channels
    for index, channel in enumerate(text_channels, start=1):
        print(f"{index}. {channel.name} (ID: {channel.id})")

    # Ask the user to choose a channel by number
    channel_number = int(await aioconsole.ainput("Enter the number of the channel to chat in: ")) - 1
    selected_channel = text_channels[channel_number]
    print(f"Selected channel: {selected_channel.name}")

    # Ask for mode after channel selection
    await switch_mode()

async def switch_mode():
    """Function to allow user to switch between modes: Read, Chat, Both, Past."""
    global current_mode
    print("Choose mode:")
    print("1. Read Mode (only view messages)")
    print("2. Chat Mode (only send messages)")
    print("3. Both Mode (view and send messages alternately)")
    print("4. Past Mode (view messages from the past 10 minutes)")

    mode_choice = int(await aioconsole.ainput("Enter the mode number (1, 2, 3, or 4): "))
    
    if mode_choice == 1:
        current_mode = "read"
        print("Switched to Read Mode...")
        await monitor_channel()
    elif mode_choice == 2:
        current_mode = "chat"
        print("Switched to Chat Mode...")
        await send_messages()
    elif mode_choice == 3:
        current_mode = "both"
        print("Switched to Both Mode...")
        await asyncio.gather(monitor_channel_both_mode(), toggle_chat_in_both_mode())  # Start both
    elif mode_choice == 4:
        current_mode = "past"
        print("Switched to Past Mode...")
        await show_past_messages()
    else:
        print("Invalid mode selected.")
        await switch_mode()

# Start the bot using the token from the .env file
client.run(bot_token)
