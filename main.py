from config import TOKEN, BOTNAME, CLIENT_ID, CL_SECRET, MY_ID
import logging
from html import escape

import pickledb
import re
from telegram import ParseMode, TelegramError, Update
from telegram.ext import Updater, MessageHandler, CommandHandler, Filters
from telegram.ext.dispatcher import run_async
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import pprint
root = logging.getLogger()
root.setLevel(logging.INFO)
scope = "user-read-playback-state,user-modify-playback-state"
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id = CLIENT_ID,
                                               client_secret = CL_SECRET,
                                               redirect_uri= "http://127.0.0.1:8080/",
                                               scope=scope))
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
help_text = (
    "Starting"
)

logger = logging.getLogger(__name__)
print(TOKEN)

@run_async
def send_async(context, *args, **kwargs):
    context.bot.send_message(*args, **kwargs)

# Create database object
db = pickledb.load("bot.db", True)
if not db.get("chats"):
    db.set("chats", [])

db.set(str("MY_ID") + "_adm", MY_ID)

def empty_message(update, context):

    # Keep chatlist
    chats = db.get("chats")

    if update.message.chat.id not in chats:
        chats.append(update.message.chat.id)
        db.set("chats", chats)
        logger.info("I have been added to %d chats" % len(chats))

    if update.message.new_chat_members:
        for new_member in update.message.new_chat_members:
            # Bot was added to a group chat
            if new_member.username == BOTNAME:
                logger.info("Add in a new grop")
                return
            # Another user joined the chat
            else:
                return welcome(update, context, new_member)
def help(update, context):
    """ Prints help text """

    chat_id = update.message.chat.id
    chat_str = str(chat_id)
    send_async(
            context,
            chat_id=chat_id,
            text=help_text,
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True,
    )

def check(update, context, override_lock=None):
    """
    Perform some checks on the update. If checks were successful, returns True,
    else sends an error message to the chat and returns False.
    """
    chat_id = update.message.chat_id
    chat_str = str(chat_id)

    if chat_id > 0:
        send_async(
            context, chat_id=chat_id, text="Please add me to a group first!",
        )
        return False

    locked = override_lock if override_lock is not None else db.get(chat_str + "_lck")

    if locked and db.get(chat_str + "_adm") != update.message.from_user.id:
        return False
    return True

def error(update, context, **kwargs):
    """ Error handling """
    error = context.error

    try:
        if isinstance(error, TelegramError) and (
            error.message == "Unauthorized"
            or error.message == "Have no rights to send a message"
            or "PEER_ID_INVALID" in error.message
        ):
            chats = db.get("chats")
            chats.remove(update.message.chat_id)
            db.set("chats", chats)
            logger.info("Removed chat_id %s from chat list" % update.message.chat_id)
        else:
            logger.error("An error (%s) occurred: %s" % (type(error), error.message))
    except:
        pass

# Welcome a user to the chat
def welcome(update, context, new_member):
    """ Welcomes a user to the chat """
    message = update.message
    chat_id = message.chat.id
    logger.info(
        "%s joined to chat %d (%s)",
        escape(new_member.first_name),
        chat_id,
        escape(message.chat.title),
    )
    text = db.get(str(chat_id))
    print(text)
    # Use default message if there's no custom one set
    if text is False:
        text = "Hello $username! Welcome to $title 😊"

    # Replace placeholders and send message
    text = text.replace("$username", new_member.first_name)
    text = text.replace("$title", message.chat.title)
    send_async(context, chat_id=chat_id, text=text, parse_mode=ParseMode.HTML)

def song(update, context):
    actual_song= sp.current_playback()
    act = str(actual_song)
    regex = r"(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'\".,<>?«»“”‘’]))"
    url = re.findall(regex, act)
    print(url[11][0])
    send_async(context, chat_id=update.message.chat.id, text=url[11][0])

def main() -> None:
    # Create the Updater and pass it your bot's token.
    updater = Updater(TOKEN, workers=10, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", help))

    # Get the dispatcher to register handlers

    dp.add_handler(CommandHandler("start", help))
    dp.add_handler(CommandHandler("help", help))
    dp.add_handler(CommandHandler("song", song))
    dp.add_handler(MessageHandler(Filters.status_update, empty_message))
    dp.add_error_handler(error)
   # Start the Bot
    updater.start_polling(timeout=30)

    updater.idle()

if __name__ == '__main__':
    main()