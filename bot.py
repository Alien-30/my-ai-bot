import os
import discord
from google import genai

# Initialize Discord client with message content intent
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# Initialize Google Gemini client
ai_client = genai.Client()

# Set your custom prefix
PREFIX = 'thala'

# Dictionary to store chat sessions per channel so the bot remembers history
chat_sessions = {}


@client.event
async def on_ready():
  print(f'Logged in as {client.user} (ID: {client.user.id})')
  print('------')


@client.event
async def on_message(message):
  # Don't respond to the bot itself
  if message.author == client.user:
    return

  clean_content = ''
  is_triggered = False

  # Check if message starts with the prefix (case-insensitive)
  if message.content.lower().startswith(PREFIX):
    clean_content = message.content[len(PREFIX) :].strip()
    is_triggered = True

  # Or check if someone pinged the bot or sent a DM
  elif client.user.mentioned_in(message) or isinstance(
      message.channel, discord.DMChannel
  ):
    clean_content = message.content.replace(f'<@{client.user.id}>', '').strip()
    is_triggered = True

  if is_triggered:
    if not clean_content:
      await message.reply('Hello! How can I help you today?')
      return

    # Get the unique channel ID so memory is tracked per channel/thread
    channel_id = message.channel.id

    # If a chat session doesn't exist for this channel yet, create one with history enabled
    if channel_id not in chat_sessions:
      chat_sessions[channel_id] = ai_client.chats.create(model='gemini-2.5-flash')

    chat = chat_sessions[channel_id]

    # Show typing indicator while generating response
    async with message.channel.typing():
      try:
        # Send message keeping the context/history of the chat session
        response = chat.send_message(clean_content)

        reply_text = response.text

        if len(reply_text) > 2000:
          reply_text = reply_text[:1997] + '...'

        await message.reply(reply_text)

      except Exception as e:
        print(f'Error: {e}')
        # If session errors out or expires, reset it safely
        if channel_id in chat_sessions:
          del chat_sessions[channel_id]
        await message.reply(
            'Oops! Something went wrong or memory reset. Try again!'
        )


client.run(os.environ['DISCORD_BOT_TOKEN'])
