import io
import matplotlib.pyplot as plt
import pandas as pd
import requests

from datetime import datetime, timedelta

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
    buffer.seek(0)

    return buffer


def set_interval(interval):
    global INTERVAL
    INTERVAL = interval


def symbol_lookup_binance(symbol):
    """Lookup for symbol via Binance API"""

    # Contact API
    try:
        url = f"https://api.binance.com/api/v3/ticker/24hr?symbol={symbol}"
        response = requests.get(url)
    except requests.RequestException:
        return None

    # Parse response
    try:
        quote = response.json()

        if "-" in quote["priceChangePercent"]:
            # Add red circle emoji
            quote["priceChangePercent"] = f"{quote['priceChangePercent']}%\U0001F534"
        else:
            # Add green circle emoji
            quote["priceChangePercent"] = f"{quote['priceChangePercent']}%\U0001F7E2"
        
        return {
            "symbol": quote['symbol'],
            "change": quote['priceChangePercent'],
            "high": quote['highPrice'],
            "low": quote['lowPrice'],
            "price": quote['lastPrice']
        }
    except (KeyError, TypeError, ValueError):
        return None


def token_price_chart_arken(token, symbol):
    """Lookup for prices via Arken API and return price chart image"""

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
