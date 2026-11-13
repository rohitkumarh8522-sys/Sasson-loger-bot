import os
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.errors import FloodWait

API_ID = int(os.environ.get("API_ID", 0))
API_HASH = os.environ.get("API_HASH", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
ADMIN_ID = int(os.environ.get("ADMIN_ID", 0))

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
    if message.from_user.id != ADMIN_ID:
        await message.reply_text("⛔ Aap is bot ko use nahi kar sakte.")
        return

    USER_STATE.pop(message.from_user.id, None)
    await message.reply_text(
        "🚀 **Advanced OTP & Account Manager**\n\n"
        "Welcome Admin! Niche diye gaye buttons ka use karein:",
        reply_markup=get_main_keyboard()
    )

@app.on_callback_query()
async def callback_handler(client, callback_query: CallbackQuery):
    if callback_query.from_user.id != ADMIN_ID:
        await callback_query.answer("⛔ Ye bot sirf Admin ke liye hai!", show_alert=True)
        return

    user_id = callback_query.from_user.id
    data = callback_query.data

    if data == "add_login":
        USER_STATE[user_id] = "awaiting_session"
        await callback_query.message.edit_text(
            "🔑 **Session Login:**\n\nKripya apna poora Pyrogram String Session yahan bhejain:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« Back", callback_data="go_back")]])
        )

    elif data == "list_accounts":
        if not USER_ACCOUNTS:
            await callback_query.answer("⚠️ Abhi tak koi account add nahi kiya gaya hai!", show_alert=True)
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
                [InlineKeyboardButton("📤 Export Session String", callback_data=f"exp_sess_{acc_id}")],
                [InlineKeyboardButton("« Back to Accounts", callback_data="list_accounts")]
            ]
            await callback_query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))
        else:
            await callback_query.answer("❌ Account nahi mila.", show_alert=True)

    elif data.startswith("get_otp_"):
        acc_id = int(data.split("_")[2])
        if acc_id in USER_ACCOUNTS:
            acc_data = USER_ACCOUNTS[acc_id]
            u_cli = acc_data["client"]
            try:
                last_msg = "Telegram (777000) se abhi tak koi message nahi mila."
                async for msg in u_cli.get_chat_history(777000, limit=1):
                    if msg.text:
                        last_msg = msg.text
                
                await callback_query.message.edit_text(
                    f"📩 **Latest OTP for +{acc_data['phone']}:**\n\n{last_msg}",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« Back", callback_data=f"manage_acc_{acc_id}")]])
                )
            except Exception as e:
                await callback_query.answer(f"✅ Account active hai. Error: {str(e)}", show_alert=True)
        else:
            await callback_query.answer("❌ Account nahi mila.", show_alert=True)

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
            await callback_query.answer("⚠️ Delete karne ke liye koi account available nahi hai!", show_alert=True)
            return

        buttons = []
        for acc_id, acc_data in USER_ACCOUNTS.items():
            buttons.append([InlineKeyboardButton(f"❌ Delete: +{acc_data['phone']}", callback_data=f"del_acc_{acc_id}")])
        buttons.append([InlineKeyboardButton("« Back", callback_data="go_back")])

        await callback_query.message.edit_text(
            "🗑️ **Delete Account:**\n\nJis account ko hatana ho, us par click karein:",
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
            await callback_query.answer("✅ Account successfully delete kar diya gaya!", show_alert=True)
            
            if USER_ACCOUNTS:
                buttons = []
                for a_id, a_data in USER_ACCOUNTS.items():
                    buttons.append([InlineKeyboardButton(f"❌ Delete: +{a_data['phone']}", callback_data=f"del_acc_{a_id}")])
                buttons.append([InlineKeyboardButton("« Back", callback_data="go_back")])
                await callback_query.message.edit_text("🗑️ **Delete Account:**", reply_markup=InlineKeyboardMarkup(buttons))
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
        
        status_msg = await message.reply_text("⏳ Session verify ho raha hai aur account connect kiya ja raha hai...")

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

# Safe Startup with FloodWait protection
async def main():
    while True:
        try:
            print("Starting bot client...")
            await app.start()
            print("Bot started successfully!")
            break
        except FloodWait as e:
            print(f"FloodWait encountered! Sleeping for {e.value} seconds...")
            await asyncio.sleep(e.value)
        except Exception as e:
            print(f"Error starting bot: {e}")
            await asyncio.sleep(10)

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    from pyrogram import idle
    loop.run_until_complete(idle())
