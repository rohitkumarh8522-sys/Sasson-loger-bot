import os
import asyncio
import urllib.request
from aiohttp import web
from pyrogram import Client, filters, idle
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

API_ID = int(os.environ.get("API_ID", 0))
API_HASH = os.environ.get("API_HASH", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
ADMIN_ID = int(os.environ.get("ADMIN_ID", 0))  # Sirf aapka Telegram ID

# Purana koi webhook laga ho toh usko hatane ke liye (Isi wajah se bot response nahi deta)
try:
    urllib.request.urlopen(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook?drop_pending_updates=true")
except Exception as e:
    print(f"Webhook clear warning: {e}")

# Main Bot Client (in_memory=True taaki Render par koi file error na aaye)
app = Client(
    "otp_manager_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    in_memory=True
)

USER_ACCOUNTS = {}
USER_STATE = {}

def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID

def get_main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Login via Session", callback_data="add_login")],
        [InlineKeyboardButton("📂 My Accounts", callback_data="list_accounts")],
        [InlineKeyboardButton("🗑️ Delete Account", callback_data="delete_menu")]
    ])

@app.on_message(filters.command("start"))
async def start_cmd(client, message: Message):
    user_id = message.from_user.id
    if not is_admin(user_id):
        await message.reply_text("⛔ **Access Denied!** Ye bot sirf Admin ke liye hai.")
        return

    USER_STATE.pop(user_id, None)
    await message.reply_text(
        "👋 **Welcome Admin!**\n\n"
        "Niche diye gaye buttons se apne accounts manage karein:",
        reply_markup=get_main_keyboard()
    )

@app.on_callback_query()
async def callback_handler(client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    if not is_admin(user_id):
        await callback_query.answer("⛔ Access Denied! Sirf Admin use kar sakta hai.", show_alert=True)
        return

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
            await callback_query.answer("⚠️ Abhi tak koi account add nahi kiya gaya hai!", show_alert=True)
            return

        buttons = []
        for acc_id, acc_data in accounts.items():
            buttons.append([InlineKeyboardButton(f"📱 +{acc_data['phone']} ({acc_data['name']})", callback_data=f"get_otp_{acc_id}")])
        buttons.append([InlineKeyboardButton("« Back", callback_data="go_back")])

        await callback_query.message.edit_text(
            "📂 **Added Accounts List:**\n\nJis account ka latest OTP check karna ho us par click karein:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    elif data.startswith("get_otp_"):
        acc_id = int(data.split("_")[2])
        accounts = USER_ACCOUNTS.get(user_id, {})
        if acc_id in accounts:
            acc_data = accounts[acc_id]
            u_cli = acc_data["client"]
            try:
                # Official Telegram chat (777000) se last message fetch karna
                last_msg = None
                async for msg in u_cli.get_chat_history(777000, limit=1):
                    last_msg = msg.text
                
                if last_msg:
                    await callback_query.message.edit_text(
                        f"📩 **Latest OTP / Message for +{acc_data['phone']}:**\n\n{last_msg}",
                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« Back to Accounts", callback_data="list_accounts")]])
                    )
                else:
                    await callback_query.answer(f"✅ +{acc_data['phone']} Active hai! Naya OTP aate hi yahin milega.", show_alert=True)
            except Exception as e:
                await callback_query.answer(f"✅ +{acc_data['phone']} Active hai! Naya OTP aate hi yahin aayega.", show_alert=True)
        else:
            await callback_query.answer("❌ Account nahi mila ya disconnect ho gaya.", show_alert=True)

    elif data == "delete_menu":
        accounts = USER_ACCOUNTS.get(user_id, {})
        if not accounts:
            await callback_query.answer("⚠️ Delete karne ke liye koi account nahi hai!", show_alert=True)
            return

        buttons = []
        for acc_id, acc_data in accounts.items():
            buttons.append([InlineKeyboardButton(f"❌ Delete: +{acc_data['phone']}", callback_data=f"del_acc_{acc_id}")])
        buttons.append([InlineKeyboardButton("« Back", callback_data="go_back")])

        await callback_query.message.edit_text(
            "🗑️ **Delete Account:**\n\nJis account ko hatana ho us par click karein:",
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
            await callback_query.answer("✅ Account delete ho gaya!", show_alert=True)
            
            if accounts:
                buttons = []
                for a_id, a_data in accounts.items():
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
    user_id = message.from_user.id
    if not is_admin(user_id):
        return

    state = USER_STATE.get(user_id)
    if state == "awaiting_session":
        session_string = message.text.strip()
        USER_STATE.pop(user_id, None)
        
        status_msg = await message.reply_text("⏳ Session connect ho raha hai...")

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
                f"✅ **Account Login Ho Gaya!**\n\n"
                f"👤 **Name:** {me.first_name}\n"
                f"🆔 **ID:** `{me.id}`\n"
                f"📱 **Phone:** +{me.phone_number}",
                reply_markup=get_main_keyboard()
            )

            # Live OTP Listener
            @user_client.on_message(filters.chat(777000))
            async def otp_listener(u_cli, otp_msg: Message):
                if otp_msg.text:
                    await client.send_message(
                        chat_id=user_id,
                        text=f"🚨 **New OTP Received!**\n\n📱 Account: `+{me.phone_number}`\n\n{otp_msg.text}"
                    )

        except Exception as e:
            await status_msg.edit_text(
                f"❌ **Login Fail:**\n`{str(e)}`",
                reply_markup=get_main_keyboard()
            )

async def handle(request):
    return web.Response(text="Bot is Live and Running!")

async def main():
    web_app = web.Application()
    web_app.router.add_get("/", handle)
    runner = web.AppRunner(web_app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"Web server running on port {port}")

    await app.start()
    me = await app.get_me()
    print(f"Bot @{me.username} is ONLINE and ready!")
    await idle()

if __name__ == "__main__":
    asyncio.run(main())
