import os
import asyncio
import aiohttp
from aiohttp import web  # Yeh line sabse zaroori hai
from pyrogram import Client, filters, idle
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

API_ID = int(os.environ.get("API_ID", 0))
API_HASH = os.environ.get("API_HASH", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
ADMIN_ID = int(os.environ.get("ADMIN_ID", 0))

# Main Bot Client
app = Client(
    "otp_manager_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    in_memory=True
)

USER_ACCOUNTS = {}
USER_STATE = {}

def get_main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Login via Session", callback_data="add_login")],
        [InlineKeyboardButton("📂 Manage Accounts", callback_data="list_accounts")],
        [InlineKeyboardButton("🗑️ Delete Account", callback_data="delete_menu")]
    ])

@app.on_message(filters.command("start"))
async def start_cmd(client, message: Message):
    global ADMIN_ID
    user_id = message.from_user.id

    if ADMIN_ID == 0:
        ADMIN_ID = user_id
        print(f"⚠️ ADMIN_ID automatically set to: {ADMIN_ID}")

    if user_id != ADMIN_ID:
        await message.reply_text("⛔ Aap is bot ko use nahi kar sakte.")
        return

    USER_STATE.pop(user_id, None)
    await message.reply_text(
        "🚀 **Advanced OTP & Account Manager Bot (Active)**\n\n"
        "Welcome Admin! Niche options chunein:",
        reply_markup=get_main_keyboard()
    )

@app.on_callback_query()
async def callback_handler(client, callback_query: CallbackQuery):
    if callback_query.from_user.id != ADMIN_ID:
        await callback_query.answer("⛔ Access Denied!", show_alert=True)
        return

    user_id = callback_query.from_user.id
    data = callback_query.data

    if data == "add_login":
        USER_STATE[user_id] = "awaiting_session"
        await callback_query.message.edit_text(
            "🔑 **Session Login:**\n\n"
            "Kripya apna poora **Pyrogram String Session** yahan bhejain:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« Back", callback_data="go_back")]])
        )

    elif data == "list_accounts":
        if not USER_ACCOUNTS:
            await callback_query.answer("⚠️ Abhi tak koi account add nahi hai!", show_alert=True)
            return

        buttons = []
        for acc_id, acc_data in USER_ACCOUNTS.items():
            buttons.append([InlineKeyboardButton(f"📱 +{acc_data['phone']} | {acc_data['name']}", callback_data=f"manage_acc_{acc_id}")])
        buttons.append([InlineKeyboardButton("« Back", callback_data="go_back")])

        await callback_query.message.edit_text(
            "📂 **Active Accounts Panel:**\n\nKisi bhi account ki details ke liye us par click karein:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    elif data.startswith("manage_acc_"):
        acc_id = int(data.split("_")[2])
        if acc_id in USER_ACCOUNTS:
            acc = USER_ACCOUNTS[acc_id]
            text = (
                f"👤 **Account Details:**\n\n"
                f"• **Name:** {acc['name']}\n"
                f"• **Username:** @{acc['username'] if acc['username'] else 'None'}\n"
                f"• **Phone:** +{acc['phone']}\n"
                f"• **ID:** `{acc_id}`\n\n"
                f"Status: **Online & Listening for OTP 🟢**"
            )
            buttons = [
                [InlineKeyboardButton("📩 Check Latest OTP", callback_data=f"get_otp_{acc_id}")],
                [InlineKeyboardButton("📤 Export Session", callback_data=f"exp_sess_{acc_id}")],
                [InlineKeyboardButton("« Back to Accounts", callback_data="list_accounts")]
            ]
            await callback_query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))
        else:
            await callback_query.answer("❌ Account nahi mila.", show_alert=True)

    elif data.startswith("get_otp_"):
        acc_id = int(data.split("_")[2])
        if acc_id in USER_ACCOUNTS:
            acc = USER_ACCOUNTS[acc_id]
            try:
                last_msg = "Telegram (777000) se abhi tak koi message nahi mila."
                async for msg in acc["client"].get_chat_history(777000, limit=1):
                    if msg.text:
                        last_msg = msg.text
                
                await callback_query.message.edit_text(
                    f"📩 **Latest OTP for +{acc['phone']}:**\n\n{last_msg}",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« Back", callback_data=f"manage_acc_{acc_id}")]])
                )
            except Exception as e:
                await callback_query.answer(f"Error: {str(e)}", show_alert=True)

    elif data.startswith("exp_sess_"):
        acc_id = int(data.split("_")[2])
        if acc_id in USER_ACCOUNTS:
            session_str = USER_ACCOUNTS[acc_id]["session"]
            await callback_query.message.edit_text(
                f"📤 **Session String for +{USER_ACCOUNTS[acc_id]['phone']}:**\n\n`{session_str}`",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« Back", callback_data=f"manage_acc_{acc_id}")]])
            )

    elif data == "delete_menu":
        if not USER_ACCOUNTS:
            await callback_query.answer("⚠️ Delete karne ke liye koi account nahi hai!", show_alert=True)
            return

        buttons = []
        for acc_id, acc_data in USER_ACCOUNTS.items():
            buttons.append([InlineKeyboardButton(f"❌ Delete: +{acc_data['phone']}", callback_data=f"del_acc_{acc_id}")])
        buttons.append([InlineKeyboardButton("« Back", callback_data="go_back")])

        await callback_query.message.edit_text(
            "🗑️ **Delete Account Panel:**\n\nJis account ko remove karna ho us par click karein:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    elif data.startswith("del_acc_"):
        acc_id = int(data.split("_")[2])
        if acc_id in USER_ACCOUNTS:
            try:
                await USER_ACCOUNTS[acc_id]["client"].stop()
            except:
                pass
            del USER_ACCOUNTS[acc_id]
            await callback_query.answer("✅ Account successfully remove kar diya gaya!", show_alert=True)
            
            if USER_ACCOUNTS:
                buttons = []
                for a_id, a_data in USER_ACCOUNTS.items():
                    buttons.append([InlineKeyboardButton(f"❌ Delete: +{a_data['phone']}", callback_data=f"del_acc_{a_id}")])
                buttons.append([InlineKeyboardButton("« Back", callback_data="go_back")])
                await callback_query.message.edit_text("🗑️ **Delete Account Panel:**", reply_markup=InlineKeyboardMarkup(buttons))
            else:
                await callback_query.message.edit_text("👋 **Main Menu:**", reply_markup=get_main_keyboard())
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
    if message.from_user.id != ADMIN_ID:
        return

    user_id = message.from_user.id
    state = USER_STATE.get(user_id)

    if state == "awaiting_session":
        session_string = message.text.strip()
        USER_STATE.pop(user_id, None)
        
        status_msg = await message.reply_text("⏳ Session verify ho raha hai, kripya intezaar karein...")

        try:
            user_client = Client(
                name=f"usr_{os.urandom(4).hex()}",
                api_id=API_ID,
                api_hash=API_HASH,
                session_string=session_string,
                in_memory=True
            )
            await user_client.start()
            me = await user_client.get_me()

            USER_ACCOUNTS[me.id] = {
                "client": user_client,
                "phone": me.phone_number,
                "name": me.first_name,
                "username": me.username,
                "session": session_string
            }

            await status_msg.edit_text(
                f"✅ **Account Successfully Login Ho Gaya!**\n\n"
                f"👤 **Name:** {me.first_name}\n"
                f"🆔 **ID:** `{me.id}`\n"
                f"📱 **Phone:** +{me.phone_number}\n\n"
                f"Ab is account par aane wale sare OTPs is bot par auto-forward honge.",
                reply_markup=get_main_keyboard()
            )

            @user_client.on_message(filters.chat(777000))
            async def otp_listener(u_cli, otp_msg: Message):
                if otp_msg.text:
                    await client.send_message(
                        chat_id=ADMIN_ID,
                        text=f"🚨 **New OTP Received!**\n\n📱 Account: `+{me.phone_number}`\n\n{otp_msg.text}"
                    )

        except Exception as e:
            error_text = str(e)
            if "unpack requires a buffer" in error_text or "string" in error_text.lower():
                err_msg = "❌ **Invalid Session String!**\nAapne jo session string di hai woh adhoori ya galat hai. Kripya poori sahi Pyrogram session string copy karke dobara bhejein."
            else:
                err_msg = f"❌ **Login Fail Ho Gaya:**\n`{error_text}`"

            await status_msg.edit_text(
                err_msg,
                reply_markup=get_main_keyboard()
            )

async def handle_web(request):
    return web.Response(text="Bot is running smoothly on Render!")

async def main():
    async with aiohttp.ClientSession() as session:
        async with session.get(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook?drop_pending_updates=true") as resp:
            print("Webhook cleared status:", resp.status)

    web_app = web.Application()
    web_app.router.add_get("/", handle_web)
    runner = web.AppRunner(web_app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"Web server started on port {port}")

    await app.start()
    print("Bot is up and running successfully!")
    await idle()

if __name__ == "__main__":
    asyncio.run(main())
