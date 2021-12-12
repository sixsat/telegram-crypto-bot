import io
import matplotlib.pyplot as plt
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
        return 15
    elif interval == "30M":
        return 30
    elif interval == "1H":
        return 60
    elif interval == "4H":
        return 240
    elif interval == "1D":
        return 1440
    elif interval == "1W":
        return 10080


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
                    text="Couldn't get the image of price chart"
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
             "/interval [interval] -> set interval (15M, 30M, 1H, 4H, 1D, 1W)\n"
             "/start -> Start message\n\n"
             "Text me:\n\n"
             "token_address -> Fetch token data and price chart"
    )


def plot_candlestick_chart(df, symbol):
    plt.figure(facecolor="#c0c0c0")

    up = df[df.close >= df.open] # Closing price >= opening price
    down = df[df.close < df.open] # Closing price < opening price

    # Define candlestick color
    up_color = "green"
    down_color = "red"

    # Define candlestick width
    width = .2
    width2 = .02

    # Plot up price
    plt.bar(up.index, up.close - up.open, width, bottom=up.open, color=up_color)
    plt.bar(up.index, up.high - up.close, width2, bottom=up.close, color=up_color)
    plt.bar(up.index, up.low - up.open, width2, bottom=up.open, color=up_color)

    # Plot down price
    plt.bar(down.index, up.close - up.open, width, bottom=down.open, color=down_color)
    plt.bar(down.index, up.high - up.open, width2, bottom=down.open, color=down_color)
    plt.bar(down.index, up.low - up.close, width2, bottom=down.close, color=down_color)

    plt.xticks(rotation=45)

    plt.title(symbol)
    plt.xlabel("Datetime")
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
                text="Invalid interval, try: 15M, 30M, 1H, 4H, 1D, 1W"
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

    timeframe = get_timeframe(INTERVAL) * 50 # Number of candlesticks
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
        
        # Create and format dataframe
        prices_df = pd.DataFrame(prices_dict, dtype=float)
        prices_df = prices_df.rename(columns={"timestamp":"datetime"})
        prices_df["datetime"] = prices_df["datetime"].apply(lambda x: datetime.fromtimestamp(int(x)))
        prices_df.set_index("datetime", inplace=True)

        return plot_candlestick_chart(prices_df, symbol)

    except (KeyError, TypeError, ValueError) as e:
        print(e.with_traceback, e)
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
