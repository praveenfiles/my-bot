# -----------------------
# Integrations (Imports)
# -----------------------
import logging
import asyncio
import requests
import random
import instaloader
import time
import re
import json
from datetime import datetime
from urllib.parse import quote
from uuid import uuid4
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    ContextTypes,
    filters,
)
from telegram.constants import ChatType, ChatMemberStatus
from telegram.error import TelegramError

# -----------------------
# Configuration & Setup
# -----------------------
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Replace these with your actual credentials
TOKEN = "7895074632:AAFeT_5iKhjnugeRsVNIiu--Xkk5cfhUisc"  # Get from BotFather
OWNER_ID = 7757666324  # Your Telegram user ID
IG_USERNAME = "camilajack34"  # For .ig command
IG_PASSWORD = "AXkKKx@uK5Y5_jp"
YOUTUBE_API_KEY = "AIzaSyA0HJGCZMN5tV3udKmm6Sq7mA9qL3PFg_g"
WORDNIK_API_KEY = "YOUR_WORDNIK_API_KEY"

# For broadcast rate-limiting: .bdc only once every 30 minutes
last_broadcast_time = 0
group_chats = set()  # Track group IDs for broadcasting

# -----------------------
# Fun Data
# -----------------------
PICKUP_LINES = [
    "Are you Google? Because you have everything I'm searching for. 😘",
    "Do you believe in love at first sight, or should I walk by again? 😉",
    "Is your name Wi-Fi? Because I'm feeling a connection! 📶",
    "Are you a magician? Because everyone else disappears when you're around. 🪄",
    "Do you have a map? I keep getting lost in your eyes. 🗺️",
    "Is your smile made of gold? Because it’s absolutely a treasure! 💛",
    "Are you an angel? Because heaven is missing one, and I think I just found her. 😇",
    "Is your heart a prison? Because I’m ready to be locked up forever. 🔒",
    "Are you a star? Because you light up my universe! 🌟",
    "Do you have a Band-Aid? Because I just scraped my knee falling for you. 🩹"
]
DIRTY_PICKUP_LINES = [
    "Are you an electrician? Because you’re lighting up my circuits. ⚡️",
    "Is your body a volcano? Because you’re making me erupt! 🌋",
    "Are you a campfire? Because you’re hot and I want s’more. 🔥",
    "Is your name Netflix? Because I could binge you all night. 📺",
    "Are you a thief? Because you’ve stolen my heart! 💋",
    "Is your skin made of copper? Because you’re absolutely a treasure! 💎",
    "Are you a light bulb? Because you’re turning me on! 💡",
    "Is your name coffee? Because you keep me up all night! ☕",
    "Are you a rocket? Because you’re blasting my heart into orbit! 🚀"
]
AUTO_REPLY_PARAGRAPHS = [
    "{username}, you're causing chaos like a storm in a teacup! 😜",
    "{username}, slow down, you're moving faster than a rocket! 🚀",
    "{username}, did you borrow that confidence from a superhero? 💪",
    "{username}, your vibes are louder than a rock concert! 🎸",
    "{username}, chill, you're making the chat too hot to handle! 🔥",
    "{username}, are you a tornado? Because you're spinning everyone around! 🌪️",
    "{username}, your energy is more electric than a thunderstorm! ⚡️",
    "{username}, stop stealing the spotlight, you dazzling star! ✨",
    "{username}, you're noisier than a parade in full swing! 🎉",
    "{username}, calm down, you're outshining the sun! ☀️",
    "{username}, are you a wildfire? Because you're spreading chaos everywhere! 🔥",
    "{username}, your antics are wilder than a rollercoaster! 🎢",
    "{username}, tone it down, you're louder than a siren! 🚨",
    "{username}, are you a comet? Because you're crashing through the chat! ☄️",
    "{username}, relax, you're stirring up more trouble than a gremlin! 😈",
    "{username}, are you a glitch? Because you're messing up the whole server! 🖥️",
    "{username}, your chaos level is higher than a cat on a laser pointer! 🐱",
    "{username}, did you steal the drama script? Because you're the star of the show! 🎭",
    "{username}, you're buzzing around like a bee in a candy store! 🐝",
    "{username}, ease up, you're making the chat vibrate like a phone on silent! 📳",
    "{username}, are you a prankster? Because you're pulling all the strings! 🃏",
    "{username}, your energy is like a Wi-Fi signal—everywhere and uncontrollable! 📡",
    "{username}, stop acting like you own the chat, you keyboard warrior! ⌨️",
    "{username}, you're louder than a foghorn at a silent retreat! 📢",
    "{username}, are you a popcorn machine? Because you're popping off nonstop! 🍿",
    "{username}, chill out, you're more hyper than a squirrel on espresso! 🐿️",
    "{username}, you're causing more ruckus than a monkey in a banana shop! 🐒",
    "{username}, are you a disco ball? Because you're throwing sparkles everywhere! 🪩",
    "{username}, tone it down, you're wilder than a storm in a teapot! 🌩️",
    "{username}, you're zipping around like a pinball in a machine! 🎰",
    "{username}, are you a runaway train? Because you're derailing the whole chat! 🚂",
    "{username}, settle down, you're more dramatic than a soap opera! 📺",
    "{username}, you're sparking more chaos than a short-circuited robot! 🤖",
    "{username}, are you a firecracker? Because you're exploding all over the place! 🎆",
    "{username}, cool it, you're louder than a jackhammer at dawn! 🔨"
]

# -----------------------
# Bot State
# -----------------------
class BotState:
    def __init__(self):
        self.auto_reply_active = False
        self.auto_reply_target_id = None
        self.auto_reply_index = 0
        self.auto_reply_count = None
        self.auto_reply_sent = 0
        self.muted_users = set()
        self.quiet_chats = set()
        self.okie_list = set()

bot_state = BotState()

# -----------------------
# Instagram Functions
# -----------------------
def fetch_instagram_info_instaloader(username):
    L = instaloader.Instaloader()
    session_file = f"{IG_USERNAME}.session"
    try:
        L.load_session_from_file(IG_USERNAME, filename=session_file)
    except Exception:
        try:
            L.login(IG_USERNAME, IG_PASSWORD)
            L.save_session_to_file(filename=session_file)
        except Exception as login_error:
            return f"❌ Error logging in to Instagram: {login_error}"
    try:
        profile = instaloader.Profile.from_username(L.context, username)
        creation_year = profile.date_joined.year if hasattr(profile, "date_joined") and profile.date_joined else "Unknown"
        profile_url = f"https://www.instagram.com/{profile.username}/"
        info = (
            "📸 **Instagram Profile Info** 📸\n"
            "═══════════════════════\n"
            "👤 Username: {}\n"
            "🔹 Full Name: {}\n"
            "📌 Bio: {}\n"
            "👥 Followers: {}\n"
            "🔄 Following: {}\n"
            "🖼️ Posts: {}\n"
            "📅 Account Created: {}\n"
            "🔗 Profile: {}\n"
            "═══════════════════════"
        ).format(
            profile.username,
            profile.full_name,
            profile.biography[:300],
            profile.followers,
            profile.followees,
            profile.mediacount,
            creation_year,
            profile_url
        )
        return info
    except Exception as e:
        return f"❌ Error fetching profile info: {e}"

# Instagram reset constants
E = 'STATUS~1'
W = 'XMLHttpRequest'
V = '936619743392459'
U = 'same-origin'
T = 'cors'
S = 'empty'
R = '*/*'
Q = 'x-requested-with'
P = 'x-ig-www-claim'
O = 'x-ig-app-id'
N = 'sec-fetch-site'
M = 'sec-fetch-mode'
L = 'sec-fetch-dest'
K = 'referer'
J = 'accept-language'
I = 'accept'
H = 'email_or_username'
F = 'csrftoken'
G = 'User-Agent'

def instagram_reset_web(email_or_username):
    url = 'https://www.instagram.com/api/v1/web/accounts/account_recovery_send_ajax/'
    csrf_token = 'umwHlWf6r3AGDowkZQb47m'
    cookies = {
        F: csrf_token,
        'datr': '_D1dZ0DhNw8dpOJHN-59ONZI',
        'ig_did': 'C0CBB4B6-FF17-4C4A-BB83-F3879B996720',
        'mid': 'Z109_AALAAGxFePISIe2H_ZcGwTD',
        'wd': '1157x959'
    }
    headers = {
        I: R,
        J: 'en-US,en;q=0.5',
        'content-type': 'application/x-www-form-urlencoded',
        'origin': 'https://www.instagram.com',
        'priority': 'u=1, i',
        K: 'https://www.instagram.com/accounts/password/reset/?source=fxcal&hl=en',
        'sec-ch-ua': '"Brave";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
        'sec-ch-ua-full-version-list': '"Brave";v="131.0.0.0", "Chromium";v="131.0.0.0", "Not_A Brand";v="24.0.0.0"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-model': '""',
        'sec-ch-ua-platform': '"Windows"',
        'sec-ch-ua-platform-version': '"10.0.0"',
        L: S,
        M: T,
        N: U,
        'sec-gpc': '1',
        G: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'x-asbd-id': '129477',
        'x-csrftoken': csrf_token,
        O: V,
        P: '0',
        'x-instagram-ajax': '1018880011',
        Q: W,
        'x-web-session-id': 'ag36cv:1ko17s:9bxl9b'
    }
    data = {H: email_or_username, 'flow': 'fxcal'}
    try:
        response = requests.post(url, cookies=cookies, headers=headers, data=data)
        response_json = response.json()
        if response_json.get('status') == 'fail':
            if response_json.get('error_type') == 'rate_limit_error':
                return "❌ TRY USING VPN. IP LIMITED."
            elif 'message' in response_json and isinstance(response_json['message'], list):
                return "❌ Check the username or email again."
            else:
                return f"❌ An error occurred: {response_json.get('message', 'Unknown error')}"
        elif response_json.get('status') == 'ok':
            return f"✅ Message: {response_json.get('message', 'Password reset sent successfully')}"
        else:
            return f"❌ Unexpected response: {response_json}"
    except json.JSONDecodeError:
        return "❌ Failed to parse the response as JSON."
    except Exception as e:
        return f"❌ An unexpected error occurred: {str(e)}"

def instagram_reset_mobile(username):
    try:
        username = username.split('@gmail.com')[0]
    except:
        pass
    profile_url = f"https://www.instagram.com/api/v1/users/web_profile_info/?username={username}"
    headers = {
        I: R,
        'accept-encoding': 'gzip',
        J: 'en-US;q=0.9,en;q=0.7',
        K: f"https://www.instagram.com/{username}",
        L: S,
        M: T,
        N: U,
        O: V,
        P: '0',
        Q: W
    }
    response = requests.get(profile_url, headers=headers).json()
    try:
        user_id = response['data']['user']['id']
    except:
        return f"❌ FAILED TO SEND THE PASSWORD RESET TO @{username}"
    reset_url = 'https://i.instagram.com/api/v1/accounts/send_password_reset/'
    headers = {
        G: 'Instagram 6.12.1 Android (30/11; 480dpi; 1080x2004; HONOR; ANY-LX2; HNANY-Q1; qcom; ar_EG_#u-nu-arab)',
        'Cookie': 'mid=YwsgcAABAAGsRwCKCbYCaUO5xej3; csrftoken=u6c8M4zaneeZBfR5scLVY43lYSIoUhxL',
        'Cookie2': '$Version=1',
        'Accept-Language': 'ar-EG, en-US',
        'X-IG-Connection-Type': 'MOBILE(LTE)',
        'X-IG-Capabilities': 'AQ==',
        'Accept-Encoding': 'gzip'
    }
    data = {'user_id': user_id, 'device_id': str(uuid4())}
    response = requests.post(reset_url, headers=headers, data=data).json()
    try:
        obfuscated_email = response['obfuscated_email']
        return f"✅ PASSWORD RESET LINK SENT TO @{username} AT {obfuscated_email}"
    except:
        return f"❌ FAILED TO SEND THE PASSWORD RESET TO @{username}"

def instagram_reset(username_or_email):
    result = instagram_reset_web(username_or_email)
    if "✅" in result:
        return result
    mobile_result = instagram_reset_mobile(username_or_email)
    return mobile_result

# -----------------------
# Helper Functions
# -----------------------
def fetch_definition(word):
    if WORDNIK_API_KEY == "YOUR_WORDNIK_API_KEY":
        return "❌ Wordnik API key not set."
    try:
        url = f"https://api.wordnik.com/v4/word.json/{word}/definitions"
        params = {"limit": 1, "includeRelated": "false", "useCanonical": "true", "api_key": WORDNIK_API_KEY}
        response = requests.get(url, params=params).json()
        if isinstance(response, list) and response:
            return response[0].get("text", "No definition available.")
        else:
            return "No definition found."
    except Exception as e:
        return f"❌ Error fetching definition: {e}"

def duckduckgo_search(query):
    url = f"https://api.duckduckgo.com/?q={quote(query)}&format=json&no_redirect=1"
    try:
        data = requests.get(url).json()
        abstract = data.get("AbstractText", "")
        heading = data.get("Heading", "")
        if abstract:
            return f"{heading}\n\n{abstract}"
        else:
            return "No instant answer found for your query."
    except Exception as e:
        return f"❌ Error performing search: {e}"

async def send_unsplash_image(update, context, query):
    try:
        image_url = f"https://source.unsplash.com/featured/?{quote(query)}"
        await context.bot.send_photo(
            chat_id=update.effective_chat.id,
            photo=image_url,
            caption=f"🖼️ Image result for '{query}'"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Error sending image: {e}")

def get_crypto_price(crypto):
    url = f"https://api.coingecko.com/api/v3/simple/price?ids={crypto}&vs_currencies=usd"
    try:
        response = requests.get(url).json()
        return f"${response[crypto]['usd']:.2f} USD"
    except Exception:
        return "Price not available."

async def check_bot_admin(chat, bot_id, permissions_needed, update):
    try:
        bot_member = await chat.get_member(bot_id)
        if bot_member.status not in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
            await update.message.reply_text(
                f"🤖 I need admin privileges with: {', '.join(permissions_needed)}"
            )
            return False
        return True
    except TelegramError as e:
        logger.error(f"Bot admin check failed: {e}")
        await update.message.reply_text("⚠️ Error checking my admin status")
        return False

# -----------------------
# Event Handlers
# -----------------------
async def handle_new_chat_members(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        group_chats.add(update.effective_chat.id)

async def handle_left_chat_member(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        group_chats.discard(update.effective_chat.id)

# -----------------------
# Command Handlers
# -----------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    banner = (
        "𝐈𝐍𝐓𝐑𝐎 𝐎𝐅 𝐏𝐑𝐀𝐕𝐄𝐄𝐍 \n"
        "═══════════════════════════════════════\n"
        "🔥 𝐎𝐖𝐍𝐄𝐑 : @𝐏𝐲𝐎𝐛𝐬𝐜𝐮𝐫𝐚\n"
        "📩 𝐒𝐮𝐩𝐩𝐨𝐫𝐭 :  𝐏𝐫𝐚𝐯𝐞𝐞𝐧 \n"
        "📢 𝐂𝐡𝐚𝐧𝐧𝐞𝐥 : @𝐏𝐫𝐚𝐯𝐞𝐞𝐧𝐅𝐢𝐥𝐞𝐬\n"
        "═══════════════════════════════════════\n"
        "🚀 Packed with powerful features to manage groups, fetch info, and have fun!\n"
        "📜 Use .cmds to see all commands.\n"
        "═══════════════════════════════════════\n"
        "💡 **Tip**: Reply to a user for commands like .mute, .kick, or .chud!"
    )
    await update.message.reply_text(banner)

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "⚡ **SELF BOT BY PRAVEEN** ⚡\n"
         "🔥 𝐎𝐖𝐍𝐄𝐑 : @𝐏𝐲𝐎𝐛𝐬𝐜𝐮𝐫𝐚\n"
        "📩 𝐒𝐮𝐩𝐩𝐨𝐫𝐭 :  𝐏𝐫𝐚𝐯𝐞𝐞𝐧 \n"
        "📢 𝐂𝐡𝐚𝐧𝐧𝐞𝐥 : @𝐏𝐫𝐚𝐯𝐞𝐞𝐧𝐅𝐢𝐥𝐞𝐬\n"
       
    )

async def ig(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info(f"IG command received: text='{update.message.text}', args={context.args}")
    username = None
    if context.args:
        username = context.args[0]
    else:
        command_text = update.message.text.strip()
        if command_text.startswith('.ig '):
            username = command_text[len('.ig '):].strip()
    
    if not username:
        await update.message.reply_text("❌ Usage: .ig <instagram_username>")
        return
    
    await update.message.reply_text("🔍 Fetching Instagram info, please wait...")
    loop = asyncio.get_event_loop()
    info = await loop.run_in_executor(None, fetch_instagram_info_instaloader, username)
    await update.message.reply_text(info)

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info(f"Reset command received: text='{update.message.text}', args={context.args}")
    target = None
    if context.args:
        target = context.args[0]
    else:
        command_text = update.message.text.strip()
        if command_text.startswith('.reset '):
            target = command_text[len('.reset '):].strip()
    
    if not target:
        await update.message.reply_text("❌ Usage: .reset <email_or_username>")
        return
    
    await update.message.reply_text(f"🔄 Resetting Instagram password for: {target}")
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, instagram_reset, target)
    await update.message.reply_text(result)

async def define(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info(f"Define command received: text='{update.message.text}', args={context.args}")
    word = None
    if context.args:
        word = context.args[0]
    else:
        command_text = update.message.text.strip()
        if command_text.startswith('.define '):
            word = command_text[len('.define '):].strip()
    
    if not word:
        await update.message.reply_text("❌ Usage: .define <word>")
        return
    
    definition = fetch_definition(word)
    await update.message.reply_text(f"📚 Definition of {word}:\n{definition}")

async def mute(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("🔒 Only the bot owner can use this command!")
        return
    if update.effective_chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
        await update.message.reply_text("❌ This command works only in groups!")
        return
    if not await check_bot_admin(update.effective_chat, context.bot.id, ["Restrict Members"], update):
        return
    target_user_id = None
    target_username = None
    if update.message.reply_to_message:
        target_user_id = update.message.reply_to_message.from_user.id
        target_username = f"@{update.message.reply_to_message.from_user.username}" if update.message.reply_to_message.from_user.username else update.message.reply_to_message.from_user.first_name
    elif context.args and context.args[0].isdigit():
        target_user_id = int(context.args[0])
    if not target_user_id:
        await update.message.reply_text("⚠️ Reply to a message or provide a user ID: .mute <user_id>")
        return
    try:
        await update.effective_chat.restrict_member(
            target_user_id,
            permissions={
                'can_send_messages': False,
                'can_send_media_messages': False,
                'can_send_polls': False,
                'can_send_other_messages': False,
                'can_add_web_page_previews': False
            }
        )
        bot_state.muted_users.add(target_user_id)
        await update.message.reply_text(f"🔇 Muted user {target_username or target_user_id}")
        if bot_state.auto_reply_active and target_user_id == bot_state.auto_reply_target_id:
            insult = random.choice(AUTO_REPLY_PARAGRAPHS).format(username=target_username or f"User_{target_user_id}")
            await update.message.reply_text(insult)
    except TelegramError as e:
        logger.error(f"Failed to mute user: {e}")
        await update.message.reply_text(f"⚠️ Error muting user: {e}")

async def unmute(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("🔒 Only the bot owner can use this command!")
        return
    if update.effective_chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
        await update.message.reply_text("❌ This command works only in groups!")
        return
    if not await check_bot_admin(update.effective_chat, context.bot.id, ["Restrict Members"], update):
        return
    target_user_id = None
    target_username = None
    if update.message.reply_to_message:
        target_user_id = update.message.reply_to_message.from_user.id
        target_username = f"@{update.message.reply_to_message.from_user.username}" if update.message.reply_to_message.from_user.username else update.message.reply_to_message.from_user.first_name
    elif context.args and context.args[0].isdigit():
        target_user_id = int(context.args[0])
    if not target_user_id:
        await update.message.reply_text("⚠️ Reply to a message or provide a user ID: .unmute <user_id>")
        return
    try:
        await update.effective_chat.restrict_member(
            target_user_id,
            permissions={
                'can_send_messages': True,
                'can_send_media_messages': True,
                'can_send_polls': True,
                'can_send_other_messages': True,
                'can_add_web_page_previews': True
            }
        )
        if target_user_id in bot_state.muted_users:
            bot_state.muted_users.remove(target_user_id)
        await update.message.reply_text(f"🔊 Unmuted user {target_username or target_user_id}")
    except TelegramError as e:
        logger.error(f"Failed to unmute user: {e}")
        await update.message.reply_text(f"⚠️ Error unmuting user: {e}")

async def mid(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "ℹ️ **PRAVEEN's Information** ℹ️\n"
        "═══════════════════════\n"
        "👑 Owner: Praveen"
        "📩 Contact: @Pyobscura\n"
        "📢 Channel: @PraveenFile\n"
        "═══════════════════════"
    )

async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("🔒 Only the bot owner can use this command!")
        return
    if update.effective_chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
        await update.message.reply_text("❌ This command works only in groups!")
        return
    if not await check_bot_admin(update.effective_chat, context.bot.id, ["Ban Members"], update):
        return
    target_user_id = None
    target_username = None
    if update.message.reply_to_message:
        target_user_id = update.message.reply_to_message.from_user.id
        target_username = f"@{update.message.reply_to_message.from_user.username}" if update.message.reply_to_message.from_user.username else update.message.reply_to_message.from_user.first_name
    elif context.args and context.args[0].isdigit():
        target_user_id = int(context.args[0])
    if not target_user_id:
        await update.message.reply_text("⚠️ Reply to a message or provide a user ID: .ban <user_id>")
        return
    try:
        await update.effective_chat.ban_member(target_user_id)
        await update.message.reply_text(f"🚫 Banned user {target_username or target_user_id}")
        if bot_state.auto_reply_active and target_user_id == bot_state.auto_reply_target_id:
            insult = random.choice(AUTO_REPLY_PARAGRAPHS).format(username=target_username or f"User_{target_user_id}")
            await update.message.reply_text(insult)
    except TelegramError as e:
        logger.error(f"Failed to ban user: {e}")
        await update.message.reply_text(f"⚠️ Error banning user: {e}")

async def unban(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("🔒 Only the bot owner can use this command!")
        return
    if update.effective_chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
        await update.message.reply_text("❌ This command works only in groups!")
        return
    if not await check_bot_admin(update.effective_chat, context.bot.id, ["Ban Members"], update):
        return
    target_user_id = None
    target_username = None
    if update.message.reply_to_message:
        target_user_id = update.message.reply_to_message.from_user.id
        target_username = f"@{update.message.reply_to_message.from_user.username}" if update.message.reply_to_message.from_user.username else update.message.reply_to_message.from_user.first_name
    elif context.args and context.args[0].isdigit():
        target_user_id = int(context.args[0])
    if not target_user_id:
        await update.message.reply_text("⚠️ Reply to a message or provide a user ID: .unban <user_id>")
        return
    try:
        await update.effective_chat.unban_member(target_user_id)
        await update.message.reply_text(f"✅ Unbanned user {target_username or target_user_id}")
    except TelegramError as e:
        logger.error(f"Failed to unban user: {e}")
        await update.message.reply_text(f"⚠️ Error unbanning user: {e}")

async def quiet(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("🔒 Only the bot owner can use this command!")
        return
    if update.effective_chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
        await update.message.reply_text("❌ This command works only in groups!")
        return
    if not await check_bot_admin(update.effective_chat, context.bot.id, ["Restrict Members"], update):
        return
    try:
        bot_state.quiet_chats.add(update.effective_chat.id)
        await update.message.reply_text("🤫 Group is now quiet. New messages will be deleted.")
    except TelegramError as e:
        logger.error(f"Error making group quiet: {e}")
        await update.message.reply_text(f"⚠️ Error: {e}")

async def relief(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("🔒 Only the bot owner can use this command!")
        return
    if update.effective_chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
        await update.message.reply_text("❌ This command works only in groups!")
        return
    try:
        if update.effective_chat.id in bot_state.quiet_chats:
            bot_state.quiet_chats.remove(update.effective_chat.id)
        await update.message.reply_text("😌 Group restrictions lifted.")
    except TelegramError as e:
        logger.error(f"Error lifting restrictions: {e}")
        await update.message.reply_text(f"⚠️ Error: {e}")

async def okie(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("🔒 Only the bot owner can use this command!")
        return
    if not update.message.reply_to_message:
        await update.message.reply_text("⚠️ Reply to a user's message to whitelist them.")
        return
    target_user_id = update.message.reply_to_message.from_user.id
    target_username = f"@{update.message.reply_to_message.from_user.username}" if update.message.reply_to_message.from_user.username else update.message.reply_to_message.from_user.first_name
    bot_state.okie_list.add(target_user_id)
    await update.message.reply_text(f"👍 User {target_username} added to whitelist (won't be auto-deleted).")

async def nah(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("🔒 Only the bot owner can use this command!")
        return
    if not update.message.reply_to_message:
        await update.message.reply_text("⚠️ Reply to a user's message to remove from whitelist.")
        return
    target_user_id = update.message.reply_to_message.from_user.id
    target_username = f"@{update.message.reply_to_message.from_user.username}" if update.message.reply_to_message.from_user.username else update.message.reply_to_message.from_user.first_name
    if target_user_id in bot_state.okie_list:
        bot_state.okie_list.remove(target_user_id)
        await update.message.reply_text(f"👎 User {target_username} removed from whitelist (will be auto-deleted).")
    else:
        await update.message.reply_text("⚠️ User is not in the whitelist.")

async def uff(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("🔒 Only the bot owner can use this command!")
        return
    if bot_state.okie_list:
        names = []
        for uid in bot_state.okie_list:
            try:
                user = await context.bot.get_chat_member(update.effective_chat.id, uid)
                username = f"@{user.user.username}" if user.user.username else user.user.first_name
                names.append(f"{username} ({uid})")
            except Exception:
                names.append(f"User_{uid} ({uid})")
        names_joined = "\n".join(names)
        await update.message.reply_text(
            "📢 **Whitelisted Users** 📢\n"
            "═══════════════════════\n"
            f"{names_joined}\n"
            "═══════════════════════"
        )
    else:
        await update.message.reply_text("No users are whitelisted.")

async def kick(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("🔒 Only the bot owner can use this command!")
        return
    if update.effective_chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
        await update.message.reply_text("❌ This command works only in groups!")
        return
    if not await check_bot_admin(update.effective_chat, context.bot.id, ["Ban Members"], update):
        return
    target_user_id = None
    target_username = None
    if update.message.reply_to_message:
        target_user_id = update.message.reply_to_message.from_user.id
        target_username = f"@{update.message.reply_to_message.from_user.username}" if update.message.reply_to_message.from_user.username else update.message.reply_to_message.from_user.first_name
    elif context.args and context.args[0].isdigit():
        target_user_id = int(context.args[0])
    if not target_user_id:
        await update.message.reply_text("⚠️ Reply to a message or provide a user ID: .kick <user_id>")
        return
    try:
        await update.effective_chat.ban_member(target_user_id)
        await update.effective_chat.unban_member(target_user_id)
        await update.message.reply_text(f"🦵 Kicked user {target_username or target_user_id}")
        if bot_state.auto_reply_active and target_user_id == bot_state.auto_reply_target_id:
            insult = random.choice(AUTO_REPLY_PARAGRAPHS).format(username=target_username or f"User_{target_user_id}")
            await update.message.reply_text(insult)
    except TelegramError as e:
        logger.error(f"Failed to kick user: {e}")
        await update.message.reply_text(f"⚠️ Error kicking user: {e}")

async def asleep(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("🔒 Only the bot owner can use this command!")
        return
    await update.message.reply_text("😴 Status set to Asleep.")

async def awake(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("🔒 Only the bot owner can use this command!")
        return
    await update.message.reply_text("🌞 Status set to Awake.")

async def busy(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("🔒 Only the bot owner can use this command!")
        return
    await update.message.reply_text("🏃 Status set to Busy.")

async def free(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("🔒 Only the bot owner can use this command!")
        return
    await update.message.reply_text("🕊️ Status set to Free.")

async def delete(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("🔒 Only the bot owner can use this command!")
        return
    if not update.message.reply_to_message:
        await update.message.reply_text("⚠️ Reply to a message to delete it.")
        return
    try:
        await update.message.reply_to_message.delete()
        await update.message.reply_text("🗑️ Message deleted.")
    except TelegramError as e:
        logger.error(f"Error deleting message: {e}")
        await update.message.reply_text(f"⚠️ Error deleting message: {e}")

async def purge(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("🔒 Only the bot owner can use this command!")
        return
    logger.info(f"Purge command received: text='{update.message.text}', args={context.args}")
    count = None
    if context.args and context.args[0].isdigit():
        count = int(context.args[0])
    else:
        command_text = update.message.text.strip()
        if command_text.startswith('.purge '):
            arg = command_text[len('.purge '):].strip()
            if arg.isdigit():
                count = int(arg)
    
    if not count:
        await update.message.reply_text("❌ Usage: .purge <number_of_messages>")
        return
    
    try:
        async for message in update.effective_chat.get_messages(limit=count):
            await message.delete()
        await update.message.reply_text(f"🧹 Purged {count} messages.")
    except TelegramError as e:
        logger.error(f"Error purging messages: {e}")
        await update.message.reply_text(f"⚠️ Error purging messages: {e}")

async def pusd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info(f"PUSD command received: text='{update.message.text}', args={context.args}")
    amount = None
    if context.args and context.args[0].replace('.', '', 1).isdigit():
        amount = float(context.args[0])
    else:
        command_text = update.message.text.strip()
        if command_text.startswith('.pusd '):
            arg = command_text[len('.pusd '):].strip()
            if arg.replace('.', '', 1).isdigit():
                amount = float(arg)
    
    if not amount:
        await update.message.reply_text("❌ Usage: .pusd <amount_in_usd>")
        return
    
    try:
        response = requests.get("https://open.er-api.com/v6/latest/USD").json()
        if response.get("result") == "success":
            inr_rate = response["rates"].get("INR")
            converted = amount * inr_rate
            await update.message.reply_text(
                f"💵 {amount} USD ≈ {converted:.2f} INR (1 USD = {inr_rate} INR)"
            )
        else:
            await update.message.reply_text("⚠️ Error fetching exchange rate data.")
    except Exception as e:
        logger.error(f"Error converting USD: {e}")
        await update.message.reply_text(f"⚠️ Error: {e}")

async def spam(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("🔒 Only the bot owner can use this command!")
        return
    logger.info(f"Spam command received: text='{update.message.text}', args={context.args}")
    count = None
    msg = None
    if context.args and context.args[0].isdigit():
        count = int(context.args[0])
        msg = " ".join(context.args[1:]) if len(context.args) > 1 else "Spam!"
    else:
        command_text = update.message.text.strip()
        if command_text.startswith('.spam '):
            parts = command_text[len('.spam '):].strip().split(' ', 1)
            if parts[0].isdigit():
                count = int(parts[0])
                msg = parts[1] if len(parts) > 1 else "Spam!"
    
    if not count:
        await update.message.reply_text("❌ Usage: .spam <count> <message>")
        return
    
    for _ in range(count):
        await update.message.reply_text(msg)
        await asyncio.sleep(0.5)
    await update.message.reply_text("📣 Spam complete.")

async def gc(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("🔒 Only the bot owner can use this command!")
        return
    logger.info(f"GC command received: text='{update.message.text}', args={context.args}")
    group_name = None
    users = []
    if context.args:
        group_name = context.args[0]
        users = context.args[1:] if len(context.args) > 1 else []
    else:
        command_text = update.message.text.strip()
        if command_text.startswith('.gc '):
            parts = command_text[len('.gc '):].strip().split(' ', 1)
            group_name = parts[0]
            users = parts[1].split() if len(parts) > 1 else []
    
    if not group_name:
        await update.message.reply_text("❌ Usage: .gc <group_name> [usernames...]")
        return
    
    try:
        chat = await context.bot.create_group_chat(title=group_name, users=users)
        group_chats.add(chat.id)
        await update.message.reply_text(
            f"👥 Group '{group_name}' created with users: {', '.join(users) if users else 'None'}."
        )
    except TelegramError as e:
        logger.error(f"Error creating group: {e}")
        await update.message.reply_text(f"⚠️ Error creating group: {e}")

async def close(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("🔒 Only the bot owner can use this command!")
        return
    if update.effective_chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
        await update.message.reply_text("❌ This command works only in groups!")
        return
    try:
        await update.effective_chat.delete()
        group_chats.discard(update.effective_chat.id)
        await update.message.reply_text("🔒 Group closed.")
    except TelegramError as e:
        logger.error(f"Error closing group: {e}")
        await update.message.reply_text(f"⚠️ Error closing group: {e}")

async def pline(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(f"😉 {random.choice(PICKUP_LINES)}")

async def dline(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(f"😏 {random.choice(DIRTY_PICKUP_LINES)}")

async def cnt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info(f"Cnt command received: text='{update.message.text}', args={context.args}")
    seconds = None
    if context.args and context.args[0].isdigit():
        seconds = int(context.args[0])
    else:
        command_text = update.message.text.strip()
        if command_text.startswith('.cnt '):
            arg = command_text[len('.cnt '):].strip()
            if arg.isdigit():
                seconds = int(arg)
    
    if not seconds:
        await update.message.reply_text("❌ Usage: .cnt <time_in_seconds>")
        return
    
    message = await update.message.reply_text(f"⏳ Countdown: {seconds} seconds remaining")
    for i in range(seconds - 1, -1, -1):
        await message.edit_text(f"⏳ Countdown: {i} seconds remaining")
        await asyncio.sleep(1)
    await message.edit_text("⌛ Countdown finished!")

async def calc(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info(f"Calc command received: text='{update.message.text}', args={context.args}")
    expression = None
    if context.args:
        expression = " ".join(context.args)
    else:
        command_text = update.message.text.strip()
        if command_text.startswith('.calc '):
            expression = command_text[len('.calc '):].strip()
    
    if not expression:
        await update.message.reply_text("❌ Usage: .calc <expression>")
        return
    
    try:
        result = eval(expression, {"__builtins__": {}})
        await update.message.reply_text(f"➗ Result: {result}")
    except Exception as e:
        logger.error(f"Error evaluating expression: {e}")
        await update.message.reply_text(f"⚠️ Error evaluating expression: {e}")

async def btc(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(f"₿ Bitcoin (BTC) Price: {get_crypto_price('bitcoin')}")

async def ltc(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(f"🪙 Litecoin (LTC) Price: {get_crypto_price('litecoin')}")

async def ton(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(f"💎 Toncoin (TON) Price: {get_crypto_price('toncoin')}")

async def stock(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        url = "https://financialmodelingprep.com/api/v3/stock_market/gainers?apikey=demo"
        data = requests.get(url).json()
        if data and isinstance(data, list) and data:
            top_stock = data[0]
            ticker = top_stock.get("ticker", "N/A")
            company = top_stock.get("companyName", "N/A")
            price = top_stock.get("price", "N/A")
            change = top_stock.get("changes", "N/A")
            percentage = top_stock.get("changesPercentage", "N/A")
            await update.message.reply_text(
                "📈 **Top Gainer of the Day** 📈\n"
                "═══════════════════════\n"
                f"🏷️ Ticker: {ticker}\n"
                f"🏢 Company: {company}\n"
                f"💰 Price: ${price}\n"
                f"📊 Change: {change} ({percentage})\n"
                "═══════════════════════"
            )
        else:
            await update.message.reply_text("⚠️ Could not retrieve stock data.")
    except Exception as e:
        logger.error(f"Error fetching stock data: {e}")
        await update.message.reply_text(f"⚠️ Error fetching stock data: {e}")

async def dm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("🔒 Only the bot owner can use this command!")
        return
    logger.info(f"DM command received: text='{update.message.text}', args={context.args}")
    if not update.message.reply_to_message:
        await update.message.reply_text("❌ Usage: .dm <message_text> (reply to a user's message)")
        return
    dm_text = None
    if context.args:
        dm_text = " ".join(context.args)
    else:
        command_text = update.message.text.strip()
        if command_text.startswith('.dm '):
            dm_text = command_text[len('.dm '):].strip()
    
    if not dm_text:
        await update.message.reply_text("❌ Usage: .dm <message_text> (reply to a user's message)")
        return
    
    target_user_id = update.message.reply_to_message.from_user.id
    target_username = f"@{update.message.reply_to_message.from_user.username}" if update.message.reply_to_message.from_user.username else update.message.reply_to_message.from_user.first_name
    try:
        await context.bot.send_message(target_user_id, dm_text)
        await update.message.reply_text(f"📩 DM sent to {target_username}.")
    except TelegramError as e:
        logger.error(f"Error sending DM: {e}")
        await update.message.reply_text(f"⚠️ Error sending DM: {e}")

async def cspam(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("🔒 Only the bot owner can use this command!")
        return
    logger.info(f"Cspam command received: text='{update.message.text}', args={context.args}")
    if not update.message.reply_to_message:
        await update.message.reply_text("❌ Usage: .cspam <count> (reply to a message)")
        return
    count = None
    if context.args and context.args[0].isdigit():
        count = int(context.args[0])
    else:
        command_text = update.message.text.strip()
        if command_text.startswith('.cspam '):
            arg = command_text[len('.cspam '):].strip()
            if arg.isdigit():
                count = int(arg)
    
    if not count:
        await update.message.reply_text("❌ Usage: .cspam <count> (reply to a message)")
        return
    
    target_message = update.message.reply_to_message.text
    for _ in range(count):
        await update.message.reply_text(target_message)
        await asyncio.sleep(0.5)
    await update.message.reply_text("🔁 Copy-spam complete.")

async def chud(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("🔒 Only the bot owner can use this command!")
        return
    target_user_id = None
    target_username = None
    count = None
    if update.message.reply_to_message:
        target_user_id = update.message.reply_to_message.from_user.id
        target_username = f"@{update.message.reply_to_message.from_user.username}" if update.message.reply_to_message.from_user.username else update.message.reply_to_message.from_user.first_name
    elif context.args and context.args[0].isdigit():
        target_user_id = int(context.args[0])
        if len(context.args) > 1 and context.args[1].isdigit():
            count = int(context.args[1])
    if not target_user_id:
        await update.message.reply_text("⚠️ Reply to a message or provide a user ID: .chud <user_id> [count]")
        return
    bot_state.auto_reply_active = True
    bot_state.auto_reply_target_id = target_user_id
    bot_state.auto_reply_index = 0
    bot_state.auto_reply_count = count
    bot_state.auto_reply_sent = 0
    await update.message.reply_text(
        f"🤖 Auto-reply activated for {target_username or target_user_id}{' for ' + str(count) + ' messages' if count else ''}!"
    )

async def soja(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("🔒 Only the bot owner can use this command!")
        return
    bot_state.auto_reply_active = False
    bot_state.auto_reply_target_id = None
    await update.message.reply_text("🛑 Auto-reply stopped! 🤣")

async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("🏓 Pong!")

async def time_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    await update.message.reply_text(f"⏰ Current time: {current_time}")

async def weather(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info(f"Weather command received: text='{update.message.text}', args={context.args}")
    location = None
    if context.args:
        location = " ".join(context.args)
    else:
        command_text = update.message.text.strip()
        if command_text.startswith('.weather '):
            location = command_text[len('.weather '):].strip()
    
    if not location:
        await update.message.reply_text("❌ Usage: .weather <location>")
        return
    
    try:
        weather = requests.get(f"http://wttr.in/{quote(location)}?format=3").text
        await update.message.reply_text(f"🌦️ {weather}")
    except Exception as e:
        logger.error(f"Error fetching weather: {e}")
        await update.message.reply_text(f"⚠️ Error fetching weather: {e}")

async def wiki(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info(f"Wiki command received: text='{update.message.text}', args={context.args}")
    query = None
    if context.args:
        query = "_".join(context.args)
    else:
        command_text = update.message.text.strip()
        if command_text.startswith('.wiki '):
            query = command_text[len('.wiki '):].strip().replace(' ', '_')
    
    if not query:
        await update.message.reply_text("❌ Usage: .wiki <search_query>")
        return
    
    url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{query}"
    try:
        response = requests.get(url).json()
        if 'extract' in response:
            title = response.get('title', 'No Title')
            extract = response.get('extract')
            await update.message.reply_text(
                f"📖 **{title}**\n"
                "═══════════════════════\n"
                f"{extract}\n"
                "═══════════════════════"
            )
        else:
            await update.message.reply_text("⚠️ No summary available for that topic.")
    except Exception as e:
        logger.error(f"Error fetching Wikipedia summary: {e}")
        await update.message.reply_text(f"⚠️ Error fetching Wikipedia summary: {e}")

async def quote(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        response = requests.get("https://api.quotable.io/random").json()
        quote_text = response.get("content", "No quote found.")
        author = response.get("author", "Unknown")
        await update.message.reply_text(
            f"💬 \"{quote_text}\"\n"
            "═══════════════════════\n"
            f"~ {author}"
        )
    except Exception as e:
        logger.error(f"Error fetching quote: {e}")
        await update.message.reply_text(f"⚠️ Error fetching quote: {e}")

async def joke(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        headers = {"Accept": "application/json"}
        response = requests.get("https://icanhazdadjoke.com/", headers=headers).json()
        joke = response.get("joke", "No joke found.")
        await update.message.reply_text(f"😂 {joke}")
    except Exception as e:
        logger.error(f"Error fetching joke: {e}")
        await update.message.reply_text(f"⚠️ Error fetching joke: {e}")

async def flip(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    result = random.choice(["Heads", "Tails"])
    await update.message.reply_text(f"🪙 Coin flip result: {result}")

async def roll(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info(f"Roll command received: text='{update.message.text}', args={context.args}")
    try:
        if context.args and len(context.args) == 2 and context.args[0].isdigit() and context.args[1].isdigit():
            low = int(context.args[0])
            high = int(context.args[1])
            result = random.randint(low, high)
            await update.message.reply_text(f"🎲 Rolled a dice between {low} and {high}: {result}")
        else:
            command_text = update.message.text.strip()
            if command_text.startswith('.roll '):
                args = command_text[len('.roll '):].strip().split()
                if len(args) == 2 and args[0].isdigit() and args[1].isdigit():
                    low = int(args[0])
                    high = int(args[1])
                    result = random.randint(low, high)
                    await update.message.reply_text(f"🎲 Rolled a dice between {low} and {high}: {result}")
                    return
            result = random.randint(1, 6)
            await update.message.reply_text(f"🎲 Rolled a dice (1-6): {result}")
    except Exception as e:
        logger.error(f"Error rolling dice: {e}")
        await update.message.reply_text(f"⚠️ Error rolling dice: {e}")

async def remind(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info(f"Remind command received: text='{update.message.text}', args={context.args}")
    delay = None
    reminder_message = None
    if context.args and context.args[0].isdigit():
        delay = int(context.args[0])
        reminder_message = " ".join(context.args[1:]) if len(context.args) > 1 else "Reminder!"
    else:
        command_text = update.message.text.strip()
        if command_text.startswith('.remind '):
            parts = command_text[len('.remind '):].strip().split(' ', 1)
            if parts[0].isdigit():
                delay = int(parts[0])
                reminder_message = parts[1] if len(parts) > 1 else "Reminder!"
    
    if not delay:
        await update.message.reply_text("❌ Usage: .remind <time_in_seconds> <reminder_message>")
        return
    
    await update.message.reply_text(f"⏳ Reminder set for {delay} seconds from now.")
    async def reminder_task(chat_id, delay, message):
        await asyncio.sleep(delay)
        try:
            await context.bot.send_message(chat_id, f"⏰ Reminder: {message}")
        except Exception as e:
            logger.error(f"Error sending reminder: {e}")
    asyncio.create_task(reminder_task(update.effective_chat.id, delay, reminder_message))

async def search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info(f"Search command received: text='{update.message.text}', args={context.args}")
    query = None
    if context.args:
        query = " ".join(context.args)
    else:
        command_text = update.message.text.strip()
        if command_text.startswith('.search '):
            query = command_text[len('.search '):].strip()
    
    if not query:
        await update.message.reply_text("❌ Usage: .search <query>")
        return
    
    result_text = duckduckgo_search(query)
    await update.message.reply_text(f"🔍 {result_text}")

async def yt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info(f"YT command received: text='{update.message.text}', args={context.args}")
    query = None
    if context.args:
        query = " ".join(context.args)
    else:
        command_text = update.message.text.strip()
        if command_text.startswith('.yt '):
            query = command_text[len('.yt '):].strip()
    
    if not query:
        await update.message.reply_text("❌ Usage: .yt <query>")
        return
    
    if YOUTUBE_API_KEY != "YOUR_YOUTUBE_API_KEY":
        try:
            yt_url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&q={quote(query)}&key={YOUTUBE_API_KEY}&maxResults=1"
            response = requests.get(yt_url).json()
            items = response.get("items", [])
            if items:
                snippet = items[0]["snippet"]
                title = snippet.get("title", "No title")
                description = snippet.get("description", "No description")
                thumbnails = snippet.get("thumbnails", {})
                thumbnail_url = thumbnails.get("high", {}).get("url", "No thumbnail")
                await update.message.reply_text(
                    "▶️ **YouTube Result** ▶️\n"
                    "═══════════════════════\n"
                    f"📹 Title: {title}\n"
                    f"📝 Description: {description}\n"
                    f"🖼️ Thumbnail: {thumbnail_url}\n"
                    "═══════════════════════"
                )
            else:
                await update.message.reply_text("⚠️ No video results found.")
        except Exception as e:
            logger.error(f"Error fetching YouTube data: {e}")
            await update.message.reply_text(f"⚠️ Error fetching YouTube data: {e}")
    else:
        search_url = f"https://www.youtube.com/results?search_query={quote(query)}"
        await update.message.reply_text(f"▶️ YouTube API key not set. Search URL:\n{search_url}")

async def gimage(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info(f"Gimage command received: text='{update.message.text}', args={context.args}")
    query = None
    if context.args:
        query = " ".join(context.args)
    else:
        command_text = update.message.text.strip()
        if command_text.startswith('.gimage '):
            query = command_text[len('.gimage '):].strip()
    
    if not query:
        await update.message.reply_text("❌ Usage: .gimage <query>")
        return
    
    await send_unsplash_image(update, context, query)

async def bdc(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global last_broadcast_time
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("🔒 Only the bot owner can use this command!")
        return
    now = time.time()
    if now - last_broadcast_time < 1800:
        await update.message.reply_text("❌ You can only broadcast once every 30 minutes.")
        return
    if not update.message.reply_to_message or not update.message.reply_to_message.text:
        await update.message.reply_text("❌ Reply to a message with text to broadcast.")
        return
    broadcast_text = "📢 **BROADCAST MESSAGE** 📢\n" + update.message.reply_to_message.text
    count = 0
    failed = 0
    for chat_id in group_chats:
        try:
            sent_message = await context.bot.send_message(chat_id, broadcast_text)
            count += 1
            try:
                await sent_message.pin(disable_notification=True)
            except TelegramError as pin_err:
                logger.warning(f"Could not pin message in {chat_id}: {pin_err}")
        except TelegramError as send_err:
            logger.warning(f"Failed to broadcast to {chat_id}: {send_err}")
            failed += 1
    last_broadcast_time = now
    await update.message.reply_text(
        f"✅ Broadcast sent to {count} groups.\n"
        f"⚠️ Failed to send to {failed} groups."
    )

async def mention_all(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
        await update.message.reply_text("❌ This command works only in groups!")
        return
    if not await check_bot_admin(update.effective_chat, context.bot.id, ["View Members", "Send Messages"], update):
        return
    try:
        member = await update.effective_chat.get_member(update.effective_user.id)
        if member.status not in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
            await update.message.reply_text("🔒 Only admins can use this command!")
            return
    except TelegramError as e:
        logger.error(f"Admin check failed: {e}")
        await update.message.reply_text("⚠️ Error verifying admin status")
        return
    message_text = ' '.join(context.args) if context.args else "Attention everyone!"
    all_members = []
    try:
        async for member in update.effective_chat.get_members():
            if not member.user.is_bot and member.user.id != context.bot.id:
                all_members.append(member)
    except TelegramError as e:
        logger.error(f"Member fetch error: {e}")
        await update.message.reply_text(
            "⚠️ Failed to fetch members!\n"
            "1. Make sure I'm an ADMIN\n"
            "2. I need 'View Members' permission\n"
            "3. Try removing and re-adding me"
        )
        return
    if not all_members:
        await update.message.reply_text("No active members found to mention!")
        return
    mentions = []
    for member in all_members[:1000]:
        if member.user.username:
            mentions.append(f"@{member.user.username}")
        else:
            mentions.append(f"[{member.user.first_name}](tg://user?id={member.user.id})")
    await update.message.reply_text(f"📢 {message_text}\n\n⏳ Processing {len(mentions)} mentions...")
    batch_size = 10
    success_count = 0
    for i in range(0, len(mentions), batch_size):
        batch = mentions[i:i + batch_size]
        try:
            await update.message.reply_text(
                ' '.join(batch),
                parse_mode='Markdown',
                disable_notification=True
            )
            success_count += len(batch)
        except TelegramError as e:
            logger.warning(f"Failed to send batch: {e}")
            continue
    await update.message.reply_text(f"✅ Successfully mentioned {success_count}/{len(mentions)} members!")

async def pin_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("🔒 Only the bot owner can use this command!")
        return
    if update.effective_chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
        await update.message.reply_text("❌ This command works only in groups!")
        return
    if not await check_bot_admin(update.effective_chat, context.bot.id, ["Pin Messages"], update):
        return
    if not update.message.reply_to_message:
        await update.message.reply_text("⚠️ Please reply to the message you want to pin!")
        return
    try:
        await update.message.reply_to_message.pin()
        await update.message.reply_text("✅ Message pinned successfully!")
    except TelegramError as e:
        logger.error(f"Failed to pin message: {e}")
        await update.message.reply_text(f"⚠️ Error pinning message: {e}")

async def cmds(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "📜 **Praveen's Self-Bot Commands** 📜\n"
        "═══════════════════════════════════════\n"
        "⚡ .start    → Welcome message\n"
        "👑 .admin    → Owner details\n"
        "📸 .ig <username>    → Instagram profile info\n"
        "🔄 .reset <email/username>    → Instagram password reset\n"
        "📚 .define <word>    → Word definition\n"
        "🔇 .mute <user_id>    → Mute a user (reply/ID)\n"
        "🔊 .unmute <user_id>    → Unmute a user (reply/ID)\n"
        "ℹ️ .mid    → Praveen's info\n"
        "🚫 .ban <user_id>    → Ban a user (reply/ID)\n"
        "✅ .unban <user_id>    → Unban a user (reply/ID)\n"
        "🤫 .quiet    → Delete new messages in group\n"
        "😌 .relief    → Stop deleting messages\n"
        "👍 .okie    → Whitelist a user (reply)\n"
        "👎 .nah    → Remove from whitelist (reply)\n"
        "📢 .uff    → List whitelisted users\n"
        "🦵 .kick <user_id>    → Kick a user (reply/ID)\n"
        "😴 .asleep    → Set status to Asleep\n"
        "🌞 .awake    → Set status to Awake\n"
        "🏃 .busy    → Set status to Busy\n"
        "🕊️ .free    → Set status to Free\n"
        "🗑️ .del    → Delete a replied message\n"
        "🧹 .purge <num>    → Purge messages\n"
        "💵 .pusd <amount>    → Convert USD to INR\n"
        "📣 .spam <count> <msg>    → Spam a message\n"
        "👥 .gc <name> [users]    → Create group\n"
        "🔒 .close    → Close group\n"
        "😉 .pline    → Pickup line\n"
        "😏 .dline    → Dirty pickup line\n"
        "⏳ .cnt <sec>    → Countdown timer\n"
        "➗ .calc <expr>    → Calculator\n"
        "₿ .btc    → Bitcoin price\n"
        "🪙 .ltc    → Litecoin price\n"
        "💎 .ton    → Toncoin price\n"
        "📈 .stock    → Top gainer stock\n"
        "📩 .dm <msg>    → Send DM (reply)\n"
        "🔁 .cspam <count>    → Copy-spam a message (reply)\n"
        "🤖 .chud <user_id> [count]    → Auto-reply insults (reply/ID)\n"
        "🛑 .soja    → Stop auto-reply\n"
        "🏓 .ping    → Pong test\n"
        "⏰ .time    → Current time\n"
        "🌦️ .weather <location>    → Weather info\n"
        "📖 .wiki <query>    → Wikipedia summary\n"
        "💬 .quote    → Inspirational quote\n"
        "😂 .joke    → Random joke\n"
        "🪙 .flip    → Coin flip\n"
        "🎲 .roll [low high]    → Roll dice\n"
        "⏰ .remind <sec> <msg>    → Set reminder\n"
        "🔍 .search <query>    → DuckDuckGo search\n"
        "▶️ .yt <query>    → YouTube search\n"
        "🖼️ .gimage <query>    → Unsplash image\n"
        "📢 .bdc    → Broadcast message (reply)\n"
        "📣 .mention [msg]    → Mention all members\n"
        "📌 .pin    → Pin a message (reply)\n"
        "═══════════════════════════════════════\n"
        "💡 **Tip**: Reply to a user for .mute, .kick, .chud, etc."
    )

async def auto_reply_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if (
        bot_state.auto_reply_active
        and bot_state.auto_reply_target_id
        and update.effective_user.id == bot_state.auto_reply_target_id
    ):
        if bot_state.auto_reply_count is not None and bot_state.auto_reply_sent >= bot_state.auto_reply_count:
            bot_state.auto_reply_active = False
            bot_state.auto_reply_target_id = None
            return
        username = f"@{update.effective_user.username}" if update.effective_user.username else update.effective_user.first_name
        paragraph = random.choice(AUTO_REPLY_PARAGRAPHS).format(username=username)
        bot_state.auto_reply_index += 1
        bot_state.auto_reply_sent += 1
        await update.message.reply_text(paragraph)

async def mute_filter(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id in bot_state.muted_users and update.effective_user.id != OWNER_ID:
        try:
            await update.message.delete()
        except TelegramError as e:
            logger.error(f"Error deleting message from muted user {update.effective_user.id}: {e}")

async def quiet_filter(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if (
        update.effective_chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]
        and update.effective_chat.id in bot_state.quiet_chats
        and update.effective_user.id != OWNER_ID
        and update.effective_user.id not in bot_state.okie_list
    ):
        try:
            await update.message.delete()
        except TelegramError as e:
            logger.error(f"Failed to delete message in quiet chat {update.effective_chat.id}: {e}")

# -----------------------
# Main Function
# -----------------------
def main():
    application = ApplicationBuilder().token(TOKEN).build()

    # -----------------------
    # Command Handlers
    # -----------------------
    application.add_handler(MessageHandler(filters.Regex(r'^\.start\b.*'), start))
    application.add_handler(MessageHandler(filters.Regex(r'^\.admin\b.*'), admin))
    application.add_handler(MessageHandler(filters.Regex(r'^\.ig\b.*'), ig))
    application.add_handler(MessageHandler(filters.Regex(r'^\.reset\b.*'), reset))
    application.add_handler(MessageHandler(filters.Regex(r'^\.define\b.*'), define))
    application.add_handler(MessageHandler(filters.Regex(r'^\.mute\b.*'), mute))
    application.add_handler(MessageHandler(filters.Regex(r'^\.unmute\b.*'), unmute))
    application.add_handler(MessageHandler(filters.Regex(r'^\.mid\b.*'), mid))
    application.add_handler(MessageHandler(filters.Regex(r'^\.ban\b.*'), ban))
    application.add_handler(MessageHandler(filters.Regex(r'^\.unban\b.*'), unban))
    application.add_handler(MessageHandler(filters.Regex(r'^\.quiet\b.*'), quiet))
    application.add_handler(MessageHandler(filters.Regex(r'^\.relief\b.*'), relief))
    application.add_handler(MessageHandler(filters.Regex(r'^\.okie\b.*'), okie))
    application.add_handler(MessageHandler(filters.Regex(r'^\.nah\b.*'), nah))
    application.add_handler(MessageHandler(filters.Regex(r'^\.uff\b.*'), uff))
    application.add_handler(MessageHandler(filters.Regex(r'^\.kick\b.*'), kick))
    application.add_handler(MessageHandler(filters.Regex(r'^\.asleep\b.*'), asleep))
    application.add_handler(MessageHandler(filters.Regex(r'^\.awake\b.*'), awake))
    application.add_handler(MessageHandler(filters.Regex(r'^\.busy\b.*'), busy))
    application.add_handler(MessageHandler(filters.Regex(r'^\.free\b.*'), free))
    application.add_handler(MessageHandler(filters.Regex(r'^\.del\b.*'), delete))
    application.add_handler(MessageHandler(filters.Regex(r'^\.purge\b.*'), purge))
    application.add_handler(MessageHandler(filters.Regex(r'^\.pusd\b.*'), pusd))
    application.add_handler(MessageHandler(filters.Regex(r'^\.spam\b.*'), spam))
    application.add_handler(MessageHandler(filters.Regex(r'^\.gc\b.*'), gc))
    application.add_handler(MessageHandler(filters.Regex(r'^\.close\b.*'), close))
    application.add_handler(MessageHandler(filters.Regex(r'^\.pline\b.*'), pline))
    application.add_handler(MessageHandler(filters.Regex(r'^\.dline\b.*'), dline))
    application.add_handler(MessageHandler(filters.Regex(r'^\.cnt\b.*'), cnt))
    application.add_handler(MessageHandler(filters.Regex(r'^\.calc\b.*'), calc))
    application.add_handler(MessageHandler(filters.Regex(r'^\.btc\b.*'), btc))
    application.add_handler(MessageHandler(filters.Regex(r'^\.ltc\b.*'), ltc))
    application.add_handler(MessageHandler(filters.Regex(r'^\.ton\b.*'), ton))
    application.add_handler(MessageHandler(filters.Regex(r'^\.stock\b.*'), stock))
    application.add_handler(MessageHandler(filters.Regex(r'^\.dm\b.*'), dm))
    application.add_handler(MessageHandler(filters.Regex(r'^\.cspam\b.*'), cspam))
    application.add_handler(MessageHandler(filters.Regex(r'^\.chud\b.*'), chud))
    application.add_handler(MessageHandler(filters.Regex(r'^\.soja\b.*'), soja))
    application.add_handler(MessageHandler(filters.Regex(r'^\.ping\b.*'), ping))
    application.add_handler(MessageHandler(filters.Regex(r'^\.time\b.*'), time_cmd))
    application.add_handler(MessageHandler(filters.Regex(r'^\.weather\b.*'), weather))
    application.add_handler(MessageHandler(filters.Regex(r'^\.wiki\b.*'), wiki))
    application.add_handler(MessageHandler(filters.Regex(r'^\.quote\b.*'), quote))
    application.add_handler(MessageHandler(filters.Regex(r'^\.joke\b.*'), joke))
    application.add_handler(MessageHandler(filters.Regex(r'^\.flip\b.*'), flip))
    application.add_handler(MessageHandler(filters.Regex(r'^\.roll\b.*'), roll))
    application.add_handler(MessageHandler(filters.Regex(r'^\.remind\b.*'), remind))
    application.add_handler(MessageHandler(filters.Regex(r'^\.search\b.*'), search))
    application.add_handler(MessageHandler(filters.Regex(r'^\.yt\b.*'), yt))
    application.add_handler(MessageHandler(filters.Regex(r'^\.gimage\b.*'), gimage))
    application.add_handler(MessageHandler(filters.Regex(r'^\.bdc\b.*'), bdc))
    application.add_handler(MessageHandler(filters.Regex(r'^\.mention\b.*'), mention_all))
    application.add_handler(MessageHandler(filters.Regex(r'^\.pin\b.*'), pin_message))
    application.add_handler(MessageHandler(filters.Regex(r'^\.cmds\b.*'), cmds))

    # -----------------------
    # Event Handlers
    # -----------------------
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, handle_new_chat_members))
    application.add_handler(MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER, handle_left_chat_member))

    # -----------------------
    # Filter Handlers
    # -----------------------
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, auto_reply_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, mute_filter))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, quiet_filter))

    # -----------------------
    # Start the Bot
    # -----------------------
    application.run_polling()

    
def print_laptop_art():
    art = r"""
██████╗░░█████╗░████████╗
██╔══██╗██╔══██╗╚══██╔══╝
██████╦╝██║░░██║░░░██║░░░
██╔══██╗██║░░██║░░░██║░░░
██████╦╝╚█████╔╝░░░██║░░░
╚═════╝░░╚════╝░░░░╚═╝░░░  """
    print(art)

print_laptop_art()

if __name__ == '__main__':
    main()
    