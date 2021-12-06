import requests

from telegram import Update
from telegram.ext import CallbackContext


def handle_message(update: Update, context: CallbackContext):

    # Format message
    text = str(update.message.text).lower()

    # Response to user
    response = responses(text)
    context.bot.send_message(chat_id=update.effective_chat.id, text=response)


def help_command(update: Update, context: CallbackContext):
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Available commands:\n\n"
             "/help -> This message\n"
             "/start -> Start message\n\n"
             "Text me:\n\n"
             "token_address -> Fetch token data"
    )


def responses(input_text):
    input_text_length = len(input_text)

    # Case token address
    if input_text_length == 42 and int(input_text, 16):

        # Look up for token
        data = token_lookup_arken(input_text)

        # Handle invalid token
        if data is None:
            return "Invalid symbol"
        
        return f"Network: {data['chain']}\n" \
               f"Symbol: {data['symbol']}\n" \
               f"Price: ${data['price']:.5f}\n" \
               f"Website: {data['website']}"\


def start_command(update: Update, context: CallbackContext):
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Send token address to get started, or /help for more information"
    )


def token_lookup_arken(token):
    """Look up for token via Arken API"""

    # Supported networks
    networks = ["bsc", "ethereum", "polygon", "avalanche", "arbitrum"]

    # Contact API
    try:
        for network in networks:
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
