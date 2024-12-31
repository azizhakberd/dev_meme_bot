#!/usr/bin/env python3
from os import path
import sys
from datetime import datetime
from typing import Optional
import json

from telegram import Update, ParseMode, Chat, User
from telegram.ext import Updater, CommandHandler, MessageHandler, CallbackContext
from telegram.ext.filters import Filters
from telegram.message import Message
from telegram.utils.helpers import escape_markdown
import database

print("reading config")
CURDIR = path.dirname(sys.argv[0])
CONFPATH = path.join(CURDIR, './config.json')
if not path.exists(CONFPATH):
	with open(CONFPATH, 'w', encoding='utf-8') as f:
		config = {
			'token': 'Your token goes here',
			'private_chat_id': -1001218939335,
			'private_chat_username': 'devs_chat',
			'database_path': 'memebot.db'
		}
		json.dump(config, f, indent=2)
		print(f'Config was created in {CONFPATH}, please edit it')
		sys.exit(0)

with open(CONFPATH, encoding='utf-8') as f:
	CONFIG = json.load(f)

private_chat_id = CONFIG['private_chat_id']
private_chat_username = CONFIG['private_chat_username']
DB_PATH = path.join(CURDIR, CONFIG['database_path'])

print('loading/creating database')
db = database.UserDB(DB_PATH)

print("initializing commands")
updater = Updater(CONFIG["token"])


def escape_md(txt: str) -> str:
	return escape_markdown(txt, 2)


def get_mention(user: User):
	return user.mention_markdown_v2()


def on_command(name: str):  # some python magic
	def add_it(func):
		updater.dispatcher.add_handler(CommandHandler(name, func))
		return func
	return add_it


def on_message(filters):
	def add_it(func):
		updater.dispatcher.add_handler(MessageHandler(filters, func))
		return func
	return add_it


def filter_chat(chat_id: int, chat: str):
	'''
	chat_id: id of a chat
	chat: @<chat> without @
	'''
	def decorator(function):
		def wrapper(update: Update, context: CallbackContext):
			if update.message.chat_id != chat_id:
				update.message.chat.send_message(
					f'''This feature only works in chat @{escape_md(chat)}

If you want to use this bot outside that group, please contact the developer: \
[@RiedleroD](tg://user?id=388037461)''',
					parse_mode=ParseMode.MARKDOWN_V2
				)
				return
			function(update, context)
		return wrapper
	return decorator


@on_command("ping")
def ping(update: Update, _context: CallbackContext):
	dt = datetime.now(update.message.date.tzinfo)-update.message.date
	update.message.reply_text(f'Ping is {dt.total_seconds():.2f}s')


@on_message(Filters.status_update.new_chat_members)
@filter_chat(private_chat_id, private_chat_username)
def new_chat_member(update: Update, _context: CallbackContext):
	handles = ", ".join(map(get_mention, update.message.new_chat_members))
	update.message.reply_text(
		f"""{handles},
いらっしゃいませ\\! \\[Welcome\\!\\]
Welcome to this chat\\! Please read the rules\\.
Добро пожаловать в чат\\! Прочти правила, пожалуйста\\.
このチャットへようこそ！ ルールをお読みください。

[rules](https://t\\.me/dev\\_meme/3667)""",
		parse_mode=ParseMode.MARKDOWN_V2
	)


def is_admin(chat: Chat, user: User) -> bool:
	# might wanna cache admins
	status = chat.get_member(user.id).status
	return status in ('creator', 'administrator')


def get_reply_target(message: Message, sendback: Optional[str] = None) -> Optional[User]:
	'''
	Returns the user that is supposed to be warned. It might be a bot.
	Returns None if no warn target.
	'''
	if message.reply_to_message is not None:
		if message.reply_to_message.sender_chat
			return message.reply_to_message.sender_chat
		else
			return message.reply_to_message.from_user
	if sendback is not None:
		message.reply_text(
			f'Please reply to a message with /{sendback}',
			parse_mode=ParseMode.MARKDOWN_V2
		)
	return None


def check_admin_to_user_action(message: Message, command: str) -> Optional[User]:
	'''
	It sends message if admin to user action is not possible and returns None
	Returns user if it's possible.
	'''
	if not is_admin(message.chat, message.from_user):
		message.reply_text('You are not an admin', parse_mode=ParseMode.MARKDOWN_V2)
		return None
	target = get_reply_target(message, command)
	if target is None:
		return None
	if target.is_bot:
		message.reply_text(f'/{command} isn\'t usable on bots', parse_mode=ParseMode.MARKDOWN_V2)
		return None
	return target


@on_command("warn")
@filter_chat(private_chat_id, private_chat_username)
def warn_member(update: Update, _context: CallbackContext):
	target = check_admin_to_user_action(update.message, 'warn')
	if target is None:
		return

	warns = db.get_warns(target.id) + 1
	db.set_warns(target.id, warns)
	update.message.chat.send_message(
		f'*{get_mention(target)}* recieved a warn\\! Now they have {warns} warns',
		parse_mode=ParseMode.MARKDOWN_V2)


@on_command("unwarn")
@filter_chat(private_chat_id, private_chat_username)
def unwarn_member(update: Update, _context: CallbackContext):
	target = check_admin_to_user_action(update.message, 'unwarn')
	if target is None:
		return

	warns = db.get_warns(target.id)
	if warns > 0:
		warns -= 1
	db.set_warns(target.id, warns)
	reply = f'*{get_mention(target)}* has been a good hooman\\! '
	if warns == 0:
		reply += 'Now they don\'t have any warns'
	else:
		reply += f'Now they have {warns} warns'
	update.message.chat.send_message(reply, parse_mode=ParseMode.MARKDOWN_V2)


@on_command("clearwarns")
@filter_chat(private_chat_id, private_chat_username)
def clear_member_warns(update: Update, _context: CallbackContext):
	target = check_admin_to_user_action(update.message, 'clearwarns')
	if target is None:
		return

	db.set_warns(target.id, 0)
	update.message.chat.send_message(
		f"*{get_mention(target)}*'s warns were cleared",
		parse_mode=ParseMode.MARKDOWN_V2
	)


@on_command("warns")
@filter_chat(private_chat_id, private_chat_username)
def get_member_warns(update: Update, _context: CallbackContext):
	target = get_reply_target(update.message)
	if target is None or target.id == update.message.from_user.id:
		warns = db.get_warns(update.message.from_user.id)
		update.message.reply_text(
			f'You have {"no" if warns == 0 else warns} warns',
			parse_mode=ParseMode.MARKDOWN_V2
		)
		return
	warns = db.get_warns(target.id)
	if target.is_bot:
		update.message.reply_text("Bots don't have warns", parse_mode=ParseMode.MARKDOWN_V2)
		return

	update.message.reply_text(
		f'*{escape_md(target.full_name)}* has {"no" if warns == 0 else warns} warns',
		parse_mode=ParseMode.MARKDOWN_V2
	)


@on_command("trust")
@filter_chat(private_chat_id, private_chat_username)
def add_trusted_user(update: Update, _context: CallbackContext):
	target = check_admin_to_user_action(update.message, 'trust')
	if target is None:
		return

	trusted = db.get_trusted(target.id)
	if trusted:
		update.message.chat.send_message(
			f'*{get_mention(target)}* is already trusted, silly',
			parse_mode=ParseMode.MARKDOWN_V2)
	else:
		db.set_trusted(target.id, True)
		if is_admin(update.message.chat, target):
			update.message.chat.send_message(
				f'*{get_mention(target)}* is already a moderater, but sure lmao',
				parse_mode=ParseMode.MARKDOWN_V2)
		else:
			update.message.chat.send_message(
				f'*{get_mention(target)}* is now amongst the ranks of the **Trusted Users**\\!',
				parse_mode=ParseMode.MARKDOWN_V2)


@on_command("untrust")
@filter_chat(private_chat_id, private_chat_username)
def del_trusted_user(update: Update, _context: CallbackContext):
	target = check_admin_to_user_action(update.message, 'untrust')
	if target is None:
		return

	trusted = db.get_trusted(target.id)
	if not trusted:
		update.message.chat.send_message(
			f'*{get_mention(target)}* wasn\'t trusted in the first place',
			parse_mode=ParseMode.MARKDOWN_V2)
	else:
		db.set_trusted(target.id, False)
		if is_admin(update.message.chat, target):
			update.message.chat.send_message(
				f'*{get_mention(target)}* is a moderater, but sure lmao',
				parse_mode=ParseMode.MARKDOWN_V2)
		else:
			update.message.chat.send_message(
				f'*{get_mention(target)}* has fallen off hard, no cap on god frfr',
				parse_mode=ParseMode.MARKDOWN_V2)


@on_command("votekick")
@on_command("kickvote")
@filter_chat(private_chat_id, private_chat_username)
def votekick(update: Update, context: CallbackContext):
	target = get_reply_target(update.message, 'votekick')
	if target is None:
		return
	voter = update.message.from_user
	# what if the voter is also a channel ?
	if update.message.sender_chat
		voter = update.message.sender_chat
	chat = update.message.chat

	
	if not (db.get_trusted(voter.id) or is_admin(chat, voter)):
		update.message.reply_text(
			'Only trusted users can votekick someone\\. Sucks to suck 🤷',
			parse_mode=ParseMode.MARKDOWN_V2)
	elif target.username == 'dev_meme' # pardon the hardcoded name of the channel
		update.message.reply_text(
			'Never shall mortals be allowed to rebel against their own creators',
			parse_mode=ParseMode.MARKDOWN_V2)
	elif db.get_trusted(target.id):
		update.message.reply_text(
			'You can\'t votekick another trusted user',
			parse_mode=ParseMode.MARKDOWN_V2)
	elif is_admin(chat, target):
		update.message.reply_text(
			'You can\'t votekick an admin',
			parse_mode=ParseMode.MARKDOWN_V2)
	else:
		db.add_votekick(voter.id, target.id)
		votes = db.get_votekicks(target.id)
		appendix = "\nthat constitutes a ban\\!" if votes >= 3 else ""
		update.message.reply_text(
			f'User {get_mention(target)} now has {votes}/3 votes against them\\.{appendix}',
			parse_mode=ParseMode.MARKDOWN_V2)
		if votes >= 3:
			context.bot.ban_chat_member(chat_id=chat.id, user_id=target.id)
			# NOTE: bot API doesn't support deleting all messages by a user, so we only delete the last
			# message. Thi is irreversible, but /votekick has worked well and hasn't been abused so far. As
			# it's mostly used to combat spam, enabling this seems fine.
			update.message.reply_to_message.delete()


print("starting polling")
updater.start_polling()
print("online")
updater.idle()
