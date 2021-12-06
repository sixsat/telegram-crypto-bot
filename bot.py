import logging
import os

from telegram.ext import CallbackContext, CommandHandler, MessageHandler, Updater
from telegram.ext.filters import Filters

import bot_responses as BR

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)


def main():
    api_key = get_api_key()

    # Setup bot
    updater = Updater(token=api_key, use_context=True)
    dispatcher = updater.dispatcher

    # Response to command input (start with /)
    dispatcher.add_handler(CommandHandler("help", BR.help_command))
    dispatcher.add_handler(CommandHandler("start", BR.start_command))

    # Response to message input
    dispatcher.add_handler(MessageHandler(Filters.text, BR.handle_message))

    # Handle error
    dispatcher.add_error_handler(error_handler)

    # Start the bot
    print("Starting Bot...")
    updater.start_polling()
    updater.idle()


def error_handler(update, context: CallbackContext):
    logging.error(msg="Exception while handling an update:", exc_info=context.error)


def get_api_key():

    # Look for API key file
    if not os.path.exists("api_key.txt"):
        raise Exception("API key not found")

    # Read API key file
    with open("api_key.txt", "r") as f:
        return f.read()


if __name__ == "__main__":
    main()
