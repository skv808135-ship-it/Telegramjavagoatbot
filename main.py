import os
import telebot
from flask import Flask, request
from openai import OpenAI

# 1. Fetch tokens from Environment Variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
HF_TOKEN = os.getenv("HF_TOKEN")

if not BOT_TOKEN or not HF_TOKEN:
    raise ValueError("BOT_TOKEN and HF_TOKEN must be set in environment variables.")

# 2. Initialize Telegram Bot and Flask App
bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# 3. Initialize Hugging Face OpenAI Client
client = OpenAI(
    base_url="https://router.huggingface.co/v1",
    api_key=HF_TOKEN,
)

# 4. Webhook Setup (Automatically configured when running on Render)
RENDER_URL = os.getenv("RENDER_EXTERNAL_URL")
if RENDER_URL:
    # Render automatically provides RENDER_EXTERNAL_URL. 
    # We use it to set the webhook dynamically on startup.
    bot.remove_webhook()
    bot.set_webhook(url=f"{RENDER_URL}/{BOT_TOKEN}")

# --- Bot Message Handlers ---

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "Hello! I am an AI chatbot powered by DeepSeek. Send me a message to get started!")

@bot.message_handler(func=lambda message: True)
def chat_with_ai(message):
    try:
        # Show a 'typing...' indicator in Telegram
        bot.send_chat_action(message.chat.id, 'typing')
        
        # Call Hugging Face API just like your JS snippet
        chat_completion = client.chat.completions.create(
            model="deepseek-ai/DeepSeek-R1:novita",
            messages=[
                {
                    "role": "user",
                    "content": message.text,
                }
            ],
        )
        
        # Extract the AI's response
        reply = chat_completion.choices[0].message.content
        
        # Telegram has a 4096 character limit per message. 
        # DeepSeek R1 often generates long <think> tags, so we split if necessary.
        if len(reply) > 4096:
            for i in range(0, len(reply), 4096):
                bot.send_message(message.chat.id, reply[i:i+4096])
        else:
            bot.reply_to(message, reply)
            
    except Exception as e:
        bot.reply_to(message, f"Sorry, I encountered an error: {str(e)}")

# --- Flask Routes ---

# Route to listen for Telegram Webhooks
@app.route('/' + BOT_TOKEN, methods=['POST'])
def webhook_handler():
    json_string = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return "!", 200

# Simple health check route for Render
@app.route("/")
def index():
    return "Telegram Bot is running smoothly!", 200

# --- Local Testing Fallback ---
if __name__ == "__main__":
    if not RENDER_URL:
        # If running locally (not on Render), fallback to polling
        print("Running locally in polling mode...")
        bot.remove_webhook()
        bot.infinity_polling()
