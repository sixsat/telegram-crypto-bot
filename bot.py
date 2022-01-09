import logging
import os

from helpers import (
    set_interval,
    symbol_lookup_binance,
    token_price_chart_arken,
    token_lookup_arken
)

from telegram import Update

from telegram.ext import (
    CallbackContext,
    CommandHandler,
    Filters,
    MessageHandler,
    Updater
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)


def main():
    api_key = get_api_key()

    # Setup bot
    updater = Updater(token=api_key, use_context=True)
    dispatcher = updater.dispatcher

    # Response to command input
    dispatcher.add_handler(CommandHandler("help", help_command))
    dispatcher.add_handler(CommandHandler("interval", set_interval_command))
    dispatcher.add_handler(CommandHandler("start", start_command))
    dispatcher.add_handler(CommandHandler("watchlist", watchlist_binance_command))

    # Response to message input
    dispatcher.add_handler(MessageHandler(Filters.text, handle_message))

    # Handle error
    dispatcher.add_error_handler(error_handler)

    # Start the bot
    print("Starting Bot...")
    updater.start_polling()
    updater.idle()


def error_handler(update, context: CallbackContext):
    logging.error(
        msg=f"Exception while handling an update:",
        exc_info=context.error
    )


def get_api_key():

    # Ensure API key file exists
    if not os.path.exists("api_key.txt"):
        raise Exception("API key not found")

    with open("api_key.txt", "r") as f:
        return f.read().strip()


def handle_message(update: Update, context: CallbackContext):
    """Check input message and response to user"""

    chat_id = update.effective_chat.id
    text = str(update.message.text)
    text_length = len(text)

    # Check for token address
    if text_length == 42 and int(text, base=16):

        # Lookup for token
        token_data = token_lookup_arken(text)

        # Handle invalid token
        if token_data is None:
            context.bot.send_message(
                chat_id=chat_id, text="Invalid token address"
            )
        else:
            context.bot.send_message(
                chat_id=chat_id,
                text=f"Network: {token_data['chain']}\n"
                     f"Symbol: {token_data['symbol']}\n"
                     f"Price: ${token_data['price']:.5f}\n"
                     f"Website: {token_data['website']}"
            )

            # Get price chart image
            price_chart = token_price_chart_arken(text, token_data["symbol"])

            if price_chart is not None:
                context.bot.send_photo(chat_id=chat_id, photo=price_chart)
                price_chart.close()
            else:
                context.bot.send_message(
                    chat_id=chat_id,
                    text="Couldn't get the price chart image"
                )
    
    # Handle invalid command
    elif text[0][0] == "/":
        context.bot.send_message(
            chat_id=chat_id, text="Unrecognized command, try /help"
        )
    else:
        context.bot.send_message(
            chat_id=chat_id, text="Invalid token address"
        )


def help_command(update: Update, context: CallbackContext):
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Available commands:\n\n"
             "/help -> This message\n"
             "/interval [interval] -> set interval (15m, 30m, 1h, 4h, 1d, 1w)\n"
             "/start -> Start message\n"
             "/watchlist -> Lookup for each symbol in watchlist\n"
             "/watchlist add [symbol] -> add symbol (e.g. btcusdt) to watchlist\n"
             "/watchlist rm [symbol] -> remove symbol (e.g.ethbtc) from watchlist or \"all\" to clear watchlist\n\n"
             "Send me:\n\n"
             "token_address -> Fetch token data and price chart"
    )


def set_interval_command(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id

    # Ensure proper usage
    if len(context.args) != 1:
        context.bot.send_message(
            chat_id=chat_id, text="Usage: /interval [interval]"
        )
    else:
        interval = context.args[0].upper()

        # Ensure valid interval
        if interval not in ["15M", "30M", "1H", "4H", "1D", "1W"]:
            context.bot.send_message(
                chat_id=chat_id,
                text="Invalid interval, try: 15m, 30m, 1h, 4h, 1d, 1w"
            )
        else:
            set_interval(interval)
            context.bot.send_message(
                chat_id=chat_id, text=f"Interval is set to {interval}"
            )


def start_command(update: Update, context: CallbackContext):
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Send token address to get started, or /help for more information"
    )


def watchlist_binance_command(update: Update, context: CallbackContext):
    """Lookup/add/remove symbols in watchlist"""
    
    chat_id = update.effective_chat.id
    argc = len(context.args)

    # Ensure watchlist file exists
    if not os.path.exists("watchlist.txt"):
        context.bot.send_message(
            chat_id=chat_id,
            text="Watchlist file not found\n"
                 "Make sure you already create \"watchlist.txt\""
        )

    # If no argument, read watchlist and lookup for each symbol
    elif argc == 0:
        with open("watchlist.txt", "r") as f:

            # Handle empty file
            if len(f.readline()) == 0:
                context.bot.send_message(
                    chat_id=chat_id, text="Watchlist is empty"
                )
            else:
                f.seek(0)
                for line in f:
                    symbol = line.strip().upper()
                    symbol_data = symbol_lookup_binance(symbol)

                    # Handle invalid symbol
                    if symbol_data is None:
                        context.bot.send_message(
                            chat_id=chat_id,
                            text=f"\"{symbol}\" is an invalid symbol"
                        )
                    else:
                        context.bot.send_message(
                            chat_id=chat_id,
                            text=f"Symbol: {symbol_data['symbol']}\n"
                                 f"24h Change: {symbol_data['change']}\n"
                                 f"24h High: {symbol_data['high']}\n"
                                 f"24h Low: {symbol_data['low']}\n"
                                 f"Price: {symbol_data['price']}"
                        )

    # If 2 arguments, check for valid argument and...
    elif argc == 2:
        arg = context.args[0].lower()
        symbol = context.args[1].upper()

        # ...add symbol to watchlist or...
        if arg == "add":
            with open("watchlist.txt", "r+") as f:
                if len(f.readline()) == 0:
                    f.write(f"{symbol}\n")

                    context.bot.send_message(
                        chat_id=chat_id,
                        text=f"Successfully add \"{symbol}\" to watchlist"
                    )
                else:
                    f.seek(0)

                    # Handle duplicate symbol
                    if symbol in [line.strip().upper() for line in f.readlines()]:
                        context.bot.send_message(
                            chat_id=chat_id,
                            text=f"\"{symbol}\" is already exists"
                        )
                    else:
                        f.write(f"{symbol}\n")

                        context.bot.send_message(
                            chat_id=chat_id,
                            text=f"Successfully add \"{symbol}\" to watchlist"
                        )

        # ...remove symbol from watchlist
        elif arg == "rm":
            if symbol == "ALL":
                with open("watchlist.txt", "r+") as f:
                    if len(f.readline()) == 0:
                        context.bot.send_message(
                            chat_id=chat_id,
                            text="Watchlist is already empty"
                        )
                    else:
                        f.truncate(0)

                        context.bot.send_message(
                            chat_id=chat_id,
                            text="Watchlist is now empty"
                        )
            else:
                success = False

                with open("watchlist.txt", "r") as f:
                    if len(f.readline()) == 0:
                        context.bot.send_message(
                            chat_id=chat_id,
                            text="Watchlist is already empty"
                        )
                    else:
                        f.seek(0)
                        lines = [line.strip().upper() for line in f.readlines()]

                        # Handle symbol not in watchlist
                        if symbol not in lines:
                            context.bot.send_message(
                                chat_id=chat_id,
                                text=f"No \"{symbol}\" in watchlist"
                            )
                        else:
                            with open("temp.txt", "w") as out_f:
                                for line in lines:
                                    if line != symbol:
                                        out_f.write(f"{line}\n")
                                success = True

                if success:
                    os.replace("temp.txt", "watchlist.txt")

                    context.bot.send_message(
                        chat_id=chat_id,
                        text=f"Successfully remove \"{symbol}\" from watchlist"
                    )
                else:
                    context.bot.send_message(
                        chat_id=chat_id,
                        text=f"Fail to remove \"{symbol}\" from watchlist"
                    )

        # Handle invalid argument
        else:
            context.bot.send_message(
                chat_id=chat_id,
                text=f"Invalid argument, try \"add\" or \"rm\""
            )

    # Handle invalid usage
    else:
        context.bot.send_message(
            chat_id=chat_id,
            text="Usage:\n"
                 "/watchlist\n"
                 "/watchlist add [symbol]\n"
                 "/watchlist rm [symbol]"
        )


if __name__ == "__main__":
    main()
