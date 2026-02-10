import os
import requests
import urllib.parse

def send_whatsapp_alert(message_body):
    """
    Sends an alert using the configured provider.
    Priority:
    1. TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID (Telegram)
    2. TWILIO_ACCOUNT_SID + TWILIO_AUTH_TOKEN (Twilio)
    3. WHATSAPP_WEBHOOK_URL (Generic/CallMeBot)
    """

    # --- Telegram Configuration ---
    tg_token = os.getenv('TELEGRAM_BOT_TOKEN')
    tg_chat_id = os.getenv('TELEGRAM_CHAT_ID')

    # --- Twilio Configuration ---
    twilio_sid = os.getenv('TWILIO_ACCOUNT_SID')
    twilio_token = os.getenv('TWILIO_AUTH_TOKEN')
    twilio_from = os.getenv('TWILIO_WHATSAPP_FROM')
    twilio_to = os.getenv('TWILIO_WHATSAPP_TO')

    # --- Generic Webhook / CallMeBot Configuration ---
    webhook_url = os.getenv('WHATSAPP_WEBHOOK_URL')

    if tg_token and tg_chat_id:
        return _send_via_telegram(tg_token, tg_chat_id, message_body)
    elif twilio_sid and twilio_token and twilio_from and twilio_to:
        return _send_via_twilio(twilio_sid, twilio_token, twilio_from, twilio_to, message_body)
    elif webhook_url:
        return _send_via_webhook(webhook_url, message_body)
    else:
        print("Error: No notification configuration found. Set Telegram, Twilio, or Webhook vars.")
        return False

def _send_via_telegram(token, chat_id, body):
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        data = {
            "chat_id": chat_id,
            "text": body,
            "parse_mode": "HTML"
        }
        response = requests.post(url, data=data, timeout=10)
        if response.status_code == 200:
            return True
        else:
            print(f"Telegram Bot Error: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"Telegram Bot Exception: {e}")
        return False

def _send_via_twilio(sid, token, from_number, to_number, body):
    try:
        url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"
        data = {
            'From': from_number,
            'To': to_number,
            'Body': body
        }
        response = requests.post(url, data=data, auth=(sid, token), timeout=10)

        if response.status_code in [200, 201]:
            return True
        else:
            print(f"Twilio Error: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"Twilio Exception: {e}")
        return False

def _send_via_webhook(url, body):
    """
    Sends a GET/POST request to a webhook.
    Ideal for CallMeBot: https://api.callmebot.com/whatsapp.php?phone=[phone]&text=[text]&apikey=[key]
    The code assumes the URL in env var already contains keys/phone, and we just append/replace 'text' or send as JSON.
    For simplicity, if it's CallMeBot, we usually construct it manually.

    Here we append the message to the URL properly encoded.
    """
    try:
        # Simple implementation: Append &text=encoded_message (common for CallMeBot)
        # If the user provides a full URL like "https://api.callmebot.com/...?apikey=123", we append using & or ?

        separator = '&' if '?' in url else '?'
        final_url = f"{url}{separator}text={urllib.parse.quote(body)}"

        # Some require GET, some POST. We'll try GET for simple APIs like CallMeBot.
        response = requests.get(final_url, timeout=10)

        if response.status_code == 200:
            return True
        else:
            print(f"Webhook Error: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"Webhook Exception: {e}")
        return False
