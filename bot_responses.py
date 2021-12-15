import io
import matplotlib.pyplot as plt
import os
import pandas as pd
import requests

from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import CallbackContext

# Interval of candlestick chart
INTERVAL = "1H"

# Supported networks
NETWORKS = ["bsc", "ethereum", "polygon", "avalanche", "arbitrum"]


def get_timeframe(interval):
    if interval == "15M":
        return 15.0
    elif interval == "30M":
        return 30.0
    elif interval == "1H":
        return 60.0
    elif interval == "4H":
        return 240.0
    elif interval == "1D":
        return 1440.0
    elif interval == "1W":
        return 10080.0


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
    
    # Check for command
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


def plot_candlestick_chart(df, symbol):
    plt.figure(figsize=[6.8, 6.0], facecolor="#fdf1db")
    plt.axes(facecolor="#fdf1db")
    plt.grid(zorder=0)

    up = df[df.close >= df.open] # Closing price >= opening price
    down = df[df.close < df.open] # Closing price < opening price

    # Candlestick color
    up_color = "green"
    down_color = "red"

    # Candlestick width
    width = get_timeframe(INTERVAL) / 2000
    width2 = width / 6

    # Plot up price
    plt.bar(up.index, up.close - up.open, width, bottom=up.open, color=up_color, zorder=3)
    plt.bar(up.index, up.high - up.close, width2, bottom=up.close, color=up_color, zorder=3)
    plt.bar(up.index, up.low - up.open, width2, bottom=up.open, color=up_color, zorder=3)

    # Plot down price
    plt.bar(down.index, down.close - down.open, width, bottom=down.open, color=down_color, zorder=3)
    plt.bar(down.index, down.high - down.open, width2, bottom=down.open, color=down_color, zorder=3)
    plt.bar(down.index, down.low - down.close, width2, bottom=down.close, color=down_color, zorder=3)

    plt.xticks(rotation=30)

    plt.title(f"{symbol} (interval: {INTERVAL})")
    plt.ylabel("Price (USD)")

    # Create binary stream
    buffer = io.BytesIO()

    plt.savefig(buffer, format="png")

    # Change stream position to the start of the stream
    buffer.seek(0)

    return buffer


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
            global INTERVAL
            INTERVAL = interval

            context.bot.send_message(
                chat_id=chat_id, text=f"Interval is set to {interval}"
            )


def start_command(update: Update, context: CallbackContext):
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Send token address to get started, or /help for more information"
    )


def token_price_chart_arken(token, symbol):
    """Lookup for prices via Arken API and create price chart"""

    timeframe = get_timeframe(INTERVAL) * 50 # Number of candlesticks (max)
    end_time = datetime.now()

    # Convert datetime to Unix time
    start_time = int(datetime.timestamp(end_time - timedelta(minutes=timeframe)))
    end_time = int(datetime.timestamp(end_time))

    # Contact API
    try:
        for network in NETWORKS:
            url = f"https://api.arken.finance/chart/{network}/{token}?from={start_time}&interval=T{INTERVAL}&to={end_time}"
            response = requests.get(url)

            if response.status_code == 200: # Successful response
                break
    except requests.RequestException:
        return None

    # Parse response
    try:
        prices = response.json()["chartBars"] # Open-high-low-close price, timestamp and volume

        # Format data
        prices_dict = {key: [dic[key] for dic in prices] for key in prices[0]}
        
        # Create and format Dataframe
        prices_df = pd.DataFrame(prices_dict, dtype=float)
        prices_df = prices_df.rename(columns={"timestamp":"datetime"})
        prices_df["datetime"] = prices_df["datetime"].apply(lambda x: datetime.fromtimestamp(int(x)))
        prices_df.set_index("datetime", inplace=True)

        return plot_candlestick_chart(prices_df, symbol)

    except (KeyError, TypeError, ValueError):
        return None


def token_lookup_arken(token):
    """Lookup for token via Arken API"""

    # Contact API
    try:
        for network in NETWORKS:
            url_token = f"https://api.arken.finance/v2/token/{network}/{token}"
            url_price = f"https://api.arken.finance/v2/token/price/{network}/{token}"
            response_token = requests.get(url_token)
            response_price = requests.get(url_price)

            if response_token.status_code == 200: # Successful response
                break
    except requests.RequestException:
        return None
    
    # Parse response
    try:
        token = response_token.json()
        price = response_price.json()
        return {
            "chain": token["chain"],
            "symbol": token["symbol"],
            "price": price["price"],
            "website": token["officialWebsite"]
        }
    except (KeyError, TypeError, ValueError):
        return None


def watchlist_binance_command(update: Update, context: CallbackContext):
    """
    Lookup for/add/remove symbols in watchlist
    (Lookup via Binance API)
    """
    
    chat_id = update.effective_chat.id
    argc = len(context.args)
    url = "https://api.binance.com/api/v3/ticker/24hr?symbol={}"

    # If no argument, loop over watchlist and lookup for each symbol
    if argc == 0:

        # Ensure watchlist file exists
        if not os.path.exists("watchlist.txt"):
            context.bot.send_message(
                chat_id=chat_id,
                text="Watchlist file not found\n"
                     "Make sure you already create \"watchlist.txt\""
            )
        else:
            with open("watchlist.txt", "r") as f:

                # Check if file is already at EOF
                if len(f.readline()) == 0:
                    context.bot.send_message(
                        chat_id=chat_id, text="Watchlist is empty"
                    )
                else:
                    f.seek(0)
                    for line in f:
                        line = line.strip().upper()

                        # Contact API
                        response = requests.get(url.format(line))

                        # Check for successful response
                        if response.status_code == 200:

                            # Parse response
                            try:
                                response = response.json()

                                if "-" in response["priceChangePercent"]:
                                    # Add red circle emoji
                                    response["priceChangePercent"] = f"{response['priceChangePercent']}%\U0001F534"
                                else:
                                    # Add green circle emoji
                                    response["priceChangePercent"] = f"{response['priceChangePercent']}%\U0001F7E2"

                                context.bot.send_message(
                                    chat_id=chat_id,
                                    text=f"Symbol: {response['symbol']}\n"
                                         f"24h Change: {response['priceChangePercent']}\n"
                                         f"24h High: {response['highPrice']}\n"
                                         f"24h Low: {response['lowPrice']}\n"
                                         f"Price: {response['lastPrice']}"
                                )
                            except (KeyError, TypeError, ValueError) as e:
                                context.bot.send_message(
                                    chat_id=chat_id,
                                    text="Couldn't parse the response"
                                )
                                raise e

                        # Handle invalid symbol
                        else:
                            context.bot.send_message(
                                chat_id=chat_id,
                                text=f"\"{line}\" is an invalid symbol"
                            )

    # If 2 arguments, check for valid argument and...
    elif argc == 2:
        arg = context.args[0].lower()
        symbol = context.args[1].upper()

        # ...add symbol to watchlist or...
        if arg == "add":
            if not os.path.exists("watchlist.txt"):
                context.bot.send_message(
                    chat_id=chat_id,
                    text="Watchlist file not found\n"
                         "Make sure you already create \"watchlist.txt\""
                )
            else:
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
            if not os.path.exists("watchlist.txt"):
                context.bot.send_message(
                    chat_id=chat_id,
                    text="Watchlist file not found\n"
                         "Make sure you already create \"watchlist.txt\""
                )
            elif symbol == "ALL":
                with open("watchlist.txt", "r+") as f:
                    if len(f.readline()) == 0:
                        context.bot.send_message(
                            chat_id=chat_id,
                            text="Watchlist is already empty"
                        )
                    else:

                        # Clear all contents in watchlist
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
