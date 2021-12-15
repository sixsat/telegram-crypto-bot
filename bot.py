import logging
import os

from telegram import Update
from telegram.ext import CallbackContext, CommandHandler, Filters, MessageHandler, Updater

import bot_responses as BR

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)


def main():
    api_key = get_api_key()

    # Setup bot
    updater = Updater(token=api_key, use_context=True)
    dispatcher = updater.dispatcher

    # Response to command input
    dispatcher.add_handler(CommandHandler("help", BR.help_command))
    dispatcher.add_handler(CommandHandler("interval", BR.set_interval_command))
    dispatcher.add_handler(CommandHandler("start", BR.start_command))
    dispatcher.add_handler(CommandHandler("watchlist", BR.watchlist_binance_command))

    # Response to message input
    dispatcher.add_handler(MessageHandler(Filters.text, BR.handle_message))

    # Handle error
    dispatcher.add_error_handler(error_handler)

    # Start the bot
    print("Starting Bot...")
    updater.start_polling()
    updater.idle()


def error_handler(update: Update, context: CallbackContext):
    logging.error(
        msg=f"Exception while handling an update: {update}",
        exc_info=context.error
    )


def get_api_key():

    # Ensure API key file exists
    if not os.path.exists("api_key.txt"):
        raise Exception("API key not found")

    with open("api_key.txt", "r") as f:
        return f.read()


if __name__ == "__main__":
    main()
