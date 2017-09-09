from telegram import MAX_MESSAGE_LENGTH, ParseMode
from telegram.ext import CommandHandler, RegexHandler
from telegram.ext.dispatcher import run_async
from telegram.utils.helpers import escape_markdown

from tg_bot import dispatcher
import tg_bot.modules.sql.notes_sql as sql
from tg_bot.modules.helper_funcs import markdown_parser
from tg_bot.config import Development as Config


def get(bot, update, notename, show_none=True):
    chat_id = update.effective_chat.id
    note = sql.get_note(chat_id, notename)
    if note:
        if note.is_reply:
            bot.forward_message(chat_id=chat_id, from_chat_id=Config.MESSAGE_DUMP or chat_id, message_id=note.value)
        else:
            update.effective_message.reply_text(note.value, parse_mode=ParseMode.MARKDOWN,
                                                disable_web_page_preview=True)
        return
    elif show_none:
        update.effective_message.reply_text("This note doesn't exist")


@run_async
def cmd_get(bot, update, args):
    if len(args) >= 1:
        notename = args[0]
        get(bot, update, notename, show_none=True)
    else:
        update.effective_message.reply_text("Get rekt")


@run_async
def hash_get(bot, update):
    message = update.effective_message.text
    fst_word = message.split()[0]
    no_hash = fst_word[1:]
    get(bot, update, no_hash, show_none=False)


def save(bot, update):
    chat_id = update.effective_chat.id
    text = update.effective_message.text
    args = text.split(None, 2)  # use python's maxsplit to separate Cmd, note_name, and data

    if len(args) >= 3:
        notename = args[1]
        txt = args[2]

        # Ensure backticks arent removed by telegram
        counter = len(txt) - len(text)  # set correct offset relative to command + notename
        for ent in update.effective_message.entities:
            if ent.type == 'code':  # if code, add backticks
                start = ent.offset + counter
                end = ent.length + start
                txt = txt[:start] + '`' + txt[start: end] + '`' + txt[end:]
                counter += 2

        sql.add_note_to_db(chat_id, notename, markdown_parser(txt), is_reply=False)
        update.effective_message.reply_text("yas! added " + notename)

    elif update.effective_message.reply_to_message and len(args) >= 2:
        notename = args[1]
        msg = update.effective_message.reply_to_message

        if Config.MESSAGE_DUMP:
            msg = bot.forward_message(chat_id=Config.MESSAGE_DUMP, from_chat_id=chat_id, message_id=msg.message_id)

        sql.add_note_to_db(chat_id, notename, msg.message_id, is_reply=True)
        update.effective_message.reply_text("yas! added replied message " + notename)

    else:
        update.effective_message.reply_text("Dude, theres no note")


def clear(bot, update, args):
    chat_id = update.effective_chat.id
    notename = args[0]

    sql.rm_note(chat_id, notename)
    update.effective_message.reply_text("Successfully removed note")


def list_notes(bot, update):
    chat_id = update.effective_chat.id
    note_list = sql.get_all_chat_notes(chat_id)

    msg = "*Notes in chat:*\n"
    for note in note_list:
        note_name = escape_markdown(" - {}\n".format(note.name))
        if len(msg) + len(note_name) > MAX_MESSAGE_LENGTH:
            update.effective_message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)
            msg = ""
        msg += note_name

    if msg == "*Notes in chat:*\n":
        update.effective_message.reply_text("No notes in this chat!")

    elif len(msg) != 0:
        update.effective_message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)


__help__ = """
 - /get  <notename>: get the note with this notename
 - #<notename>: same as /get
 - /save <notename> <notedata>: saves notedata as a note with name notename
 - /save <notename>: save the replied message as a note with name notename
 - /notes or /saved: list all saved notes in this chat
 - /clear <notename>: clear note with this name
"""

GET_HANDLER = CommandHandler("get", cmd_get, pass_args=True)
HASH_GET_HANDLER = RegexHandler(r"^#([^\s])+", hash_get)

SAVE_HANDLER = CommandHandler("save", save)
DELETE_HANDLER = CommandHandler("clear", clear, pass_args=True)

LIST_HANDLER = CommandHandler("notes", list_notes)
LIST_HANDLER2 = CommandHandler("saved", list_notes)

dispatcher.add_handler(GET_HANDLER)
dispatcher.add_handler(SAVE_HANDLER)
dispatcher.add_handler(LIST_HANDLER)
dispatcher.add_handler(LIST_HANDLER2)
dispatcher.add_handler(DELETE_HANDLER)
dispatcher.add_handler(HASH_GET_HANDLER)