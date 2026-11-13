import os
import asyncio
from aiohttp import web
from pyrogram import Client, filters, idle
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

API_ID = int(os.environ.get("API_ID", 0))
API_HASH = os.environ.get("API_HASH", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")

app = Client("otp_manager_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Memory mein accounts store karne ke liye
USER_ACCOUNTS = {}
USER_STATE = {}

def get_main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Login via Session", callback_data="add_login")],
        [InlineKeyboardButton("📂 My Accounts", callback_data="list_accounts")],
        [InlineKeyboardButton("🗑️ Delete Account", callback_data="delete_menu")]
    ])

@app.on_message(filters.command("start"))
async def start_cmd(client, message: Message):
    USER_STATE.pop(message.from_user.id, None)
    await message.reply_text(
        "👋 **Welcome to OTP Manager Bot!**\n\n"
        "Niche diye gaye buttons ka use karke apne accounts manage karein:",
        reply_markup=get_main_keyboard()
    )

@app.on_callback_query()
async def callback_handler(client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    data = callback_query.data

    if data == "add_login":
        USER_STATE[user_id] = "awaiting_session"
        await callback_query.message.edit_text(
            "🔑 **Session Login:**\n\nKripya apna Pyrogram String Session yahan bhejain:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« Back", callback_data="go_back")]])
        )

    elif data == "list_accounts":
        accounts = USER_ACCOUNTS.get(user_id, {})
        if not accounts:
            await callback_query.answer("⚠️ Aapne abhi tak koi account add nahi kiya hai!", show_alert=True)
            return

        buttons = []
        for acc_id, acc_data in accounts.items():
            buttons.append([InlineKeyboardButton(f"📱 +{acc_data['phone']} ({acc_data['name']})", callback_data=f"get_otp_{acc_id}")])
        buttons.append([InlineKeyboardButton("« Back", callback_data="go_back")])

        await callback_query.message.edit_text(
            "📂 **Aapke Added Accounts:**\n\nJis account ka status dekhna ho, us par click karein:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    elif data.startswith("get_otp_"):
        acc_id = int(data.split("_")[2])
        accounts = USER_ACCOUNTS.get(user_id, {})
        if acc_id in accounts:
            acc_data = accounts[acc_id]
            await callback_query.answer(f"✅ Account active hai: +{acc_data['phone']}\nOfficial Telegram service (777000) se aane wale OTPs yahin aayenge.", show_alert=True)
        else:
            await callback_query.answer("❌ Account nahi mila ya disconnect ho gaya.", show_alert=True)

    elif data == "delete_menu":
        accounts = USER_ACCOUNTS.get(user_id, {})
        if not accounts:
            await callback_query.answer("⚠️ Delete karne ke liye koi account available nahi hai!", show_alert=True)
            return

        buttons = []
        for acc_id, acc_data in accounts.items():
            buttons.append([InlineKeyboardButton(f"❌ Delete: +{acc_data['phone']}", callback_data=f"del_acc_{acc_id}")])
        buttons.append([InlineKeyboardButton("« Back", callback_data="go_back")])

        await callback_query.message.edit_text(
            "🗑️ **Delete Account:**\n\nJis account ko remove karna ho, us par click karein:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    elif data.startswith("del_acc_"):
        acc_id = int(data.split("_")[2])
        accounts = USER_ACCOUNTS.get(user_id, {})
        if acc_id in accounts:
            try:
                await accounts[acc_id]["client"].stop()
            except:
                pass
            del accounts[acc_id]
            await callback_query.answer("✅ Account successfully delete kar diya gaya!", show_alert=True)
            
            if accounts:
                buttons = []
                for a_id, a_data in accounts.items():
                    buttons.append([InlineKeyboardButton(f"❌ Delete: +{a_data['phone']}", callback_data=f"del_acc_{a_id}")])
                buttons.append([InlineKeyboardButton("« Back", callback_data="go_back")])
                await callback_query.message.edit_text("🗑️ **Delete Account:**", reply_markup=InlineKeyboardMarkup(buttons))
            else:
                await callback_query.message.edit_text("👋 **Menu:**", reply_markup=get_main_keyboard())
        else:
            await callback_query.answer("❌ Account nahi mila.", show_alert=True)

    elif data == "go_back":
        USER_STATE.pop(user_id, None)
        await callback_query.message.edit_text(
            "👋 **Main Menu:**",
            reply_markup=get_main_keyboard()
        )

@app.on_message(filters.text & ~filters.command(["start"]))
async def handle_text_messages(client, message: Message):
    user_id = message.from_user.id
    state = USER_STATE.get(user_id)

    if state == "awaiting_session":
        session_string = message.text.strip()
        USER_STATE.pop(user_id, None)
        
        status_msg = await message.reply_text("⏳ Session connect ho raha hai, kripya intezaar karein...")

        try:
            user_client = Client(
                name=f"usr_{user_id}_{os.urandom(4).hex()}",
                api_id=API_ID,
                api_hash=API_HASH,
                session_string=session_string,
                in_memory=True
            )
            await user_client.start()
            me = await user_client.get_me()

            if user_id not in USER_ACCOUNTS:
                USER_ACCOUNTS[user_id] = {}

            USER_ACCOUNTS[user_id][me.id] = {
                "client": user_client,
                "phone": me.phone_number,
                "name": me.first_name
            }

            await status_msg.edit_text(
                f"✅ **Account Successfully Login Ho Gaya!**\n\n"
                f"👤 **Name:** {me.first_name}\n"
                f"🆔 **ID:** `{me.id}`\n"
                f"📱 **Phone:** +{me.phone_number}",
                reply_markup=get_main_keyboard()
            )

            @user_client.on_message(filters.chat(777000))
            async def otp_listener(u_cli, otp_msg: Message):
                if otp_msg.text:
                    await client.send_message(
                        chat_id=user_id,
                        text=f"🚨 **New OTP Received!**\n\n📱 Account: `+{me.phone_number}`\n\n{otp_msg.text}"
                    )

        except Exception as e:
            await status_msg.edit_text(
                f"❌ **Login Fail Ho Gaya:**\n`{str(e)}`",
                reply_markup=get_main_keyboard()
            )

# Render Port Binding ke liye Web Server
async def handle(request):
    return web.Response(text="Bot is running successfully!")

async def main():
    # Web server start karein
    web_app = web.Application()
    web_app.router.add_get("/", handle)
    runner = web.AppRunner(web_app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"Web server started on port {port}")

    # Pyrogram Bot start karein
    await app.start()
    print("Bot started successfully and listening for messages!")
    
    # Bot ko active rakhne ke liye idle() use karein
    await idle()

if __name__ == "__main__":
    asyncio.run(main())
