import discord
import asyncio
import os
from dotenv import load_dotenv
import aioconsole

# Load the .env file and its variables
load_dotenv()

# Get the bot token from the .env file
bot_token = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True  # Enable message content access
intents.guilds = True  # Enable guild (server) related events
intents.messages = True  # Enable message events

client = discord.Client(intents=intents)

selected_channel = None  # This will hold the channel the user selects
pause_display = False  # This controls whether new messages are displayed
current_mode = None  # This will store the current mode (read, chat, both)


@client.event
async def on_ready():
    print(f'Logged in as {client.user} (ID: {client.user.id})')
    print('------')

    # List all guilds (servers) the bot is in
    guilds = client.guilds
    for index, guild in enumerate(guilds, start=1):
        print(f"{index}. {guild.name} (ID: {guild.id})")

    # Ask the user to choose a guild by number
    guild_number = int(await aioconsole.ainput("Enter the number of the guild to join: ")) - 1
    selected_guild = guilds[guild_number]
    print(f"Selected guild: {selected_guild.name}")

    # Now list all text channels in the selected guild
    text_channels = selected_guild.text_channels
    for index, channel in enumerate(text_channels, start=1):
        print(f"{index}. {channel.name} (ID: {channel.id})")
    
    # Ask the user to choose a channel by number
    channel_number = int(await aioconsole.ainput("Enter the number of the channel to chat in: ")) - 1
    global selected_channel
    selected_channel = text_channels[channel_number]
    print(f"Selected channel: {selected_channel.name}")

    # Set up the mode switching and message handling tasks
    await switch_mode()

async def switch_mode():
    """Function to allow user to switch between modes: Read, Chat, Both."""
    global current_mode
    print("Choose mode:")
    print("1. Read Mode (only view messages)")
    print("2. Chat Mode (only send messages)")
    print("3. Both Mode (view and send messages alternately)")

    mode_choice = int(await aioconsole.ainput("Enter the mode number (1, 2, or 3): "))
    
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
    else:
        print("Invalid mode selected.")
        await switch_mode()

async def monitor_channel_both_mode():
    """ Continuously listen for new messages in the selected channel and display them unless paused. """
    global pause_display
    async for message in selected_channel.history(limit=10, oldest_first=False):
        if message.author != client.user:
            print(f"{message.author.display_name}: {message.content}")

    @client.event
    async def on_message(message):
        """ Display new messages in 'Both Mode' unless paused."""
        if message.channel == selected_channel and message.author != client.user and not pause_display:
            print(f"{message.author.display_name}: {message.content}")

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

async def send_messages():
    """ Allow the user to send messages by typing in the console. """
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


async def monitor_channel():
    """ Continuously listen for new messages in the selected channel and display them. """
    async for message in selected_channel.history(limit=0, oldest_first=False):
        pass  # Clear any past messages to start fresh

    @client.event
    async def on_message(message):
        """ Display new messages as they come in. """
        if message.channel == selected_channel and message.author != client.user:
            print(f"{message.author.display_name}: {message.content}")


# Start the bot using the token from the .env file
client.run(bot_token)
