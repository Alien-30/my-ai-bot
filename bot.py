import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import discord
from google import genai
from google.genai import types

# --- 1. Dummy Web Server (To keep Render Web Service happy) ---
class SimpleHandler(BaseHTTPRequestHandler):

  def do_GET(self):
    self.send_response(200)
    self.end_headers()
    self.wfile.write(b'ThalaAI is online and running!')


def run_server():
  port = int(os.environ.get('PORT', 10000))
  server = HTTPServer(('0.0.0.0', port), SimpleHandler)
  server.serve_forever()


# Start the dummy server in a background thread so it doesn't block Discord
threading.Thread(target=run_server, daemon=True).start()

# --- 2. Discord Bot Logic ---
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

ai_client = genai.Client()
PREFIX = 'thala'
chat_sessions = {}


@client.event
async def on_ready():
  print(f'Logged in as {client.user}')


@client.event
async def on_message(message):
  if message.author == client.user:
    return

  clean_content = ''
  is_triggered = False

  if message.content.lower().startswith(PREFIX):
    clean_content = message.content[len(PREFIX) :].strip()
    is_triggered = True
  elif client.user.mentioned_in(message) or isinstance(
      message.channel, discord.DMChannel
  ):
    clean_content = message.content.replace(f'<@{client.user.id}>', '').strip()
    is_triggered = True

  if is_triggered:
    if not clean_content:
      await message.reply('Hello! How can I help you today?')
      return

    channel_id = message.channel.id
    if channel_id not in chat_sessions:
      chat_sessions[channel_id] = ai_client.chats.create(
          model='gemini-2.5-flash',
          config=types.GenerateContentConfig(
              system_instruction=(
                  'Your name is ThalaAI. You are a private Discord server'
                  ' assistant. Never mention Google or Gemini unless'
                  ' specifically asked. Keep your answers concise, helpful,'
                  ' and tailored to Discord chatting.'
              )
          ),
      )

    chat = chat_sessions[channel_id]
    async with message.channel.typing():
      try:
        response = chat.send_message(clean_content)
        reply_text = response.text
        if len(reply_text) > 2000:
          reply_text = reply_text[:1997] + '...'
        await message.reply(reply_text)
      except Exception as e:
        print(f'Error: {e}')
        if channel_id in chat_sessions:
          del chat_sessions[channel_id]
        await message.reply(
            'Oops! Something went wrong or memory reset. Try again!'
        )


client.run(os.environ['DISCORD_BOT_TOKEN'])