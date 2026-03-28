import os
import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession
from dotenv import load_dotenv
from monitor import register_handlers, STATS
from notifier import send_whatsapp_alert
import datetime

# Load environment variables
load_dotenv()

API_ID = os.getenv('TELEGRAM_API_ID')
API_HASH = os.getenv('TELEGRAM_API_HASH')
SESSION_STRING = os.getenv('TELEGRAM_SESSION_STRING')
SUMMARY_INTERVAL_HOURS = int(os.getenv('SUMMARY_INTERVAL_HOURS', 24))

if not all([API_ID, API_HASH, SESSION_STRING]):
    print("Error: TELEGRAM_API_ID, TELEGRAM_API_HASH, and TELEGRAM_SESSION_STRING must be set.")
    exit(1)

# --- Resilience constants ---
MAX_RETRIES = 10
INITIAL_BACKOFF = 5  # seconds

client = TelegramClient(StringSession(SESSION_STRING), int(API_ID), API_HASH)

async def daily_summary_loop():
    """
    Sends a summary message periodically to let the user know the bot is alive.
    """
    # Send one immediately on startup for confirmation
    print("Sending startup summary...")
    send_summary_notification("Startup")

    while True:
        # Wait for interval (default 24h)
        await asyncio.sleep(SUMMARY_INTERVAL_HOURS * 3600)
        print("Sending scheduled daily summary...")
        send_summary_notification("Daily")

def send_summary_notification(label):
    now = datetime.datetime.now()
    uptime = now - STATS['start_time'] if STATS['start_time'] else "N/A"

    summary_msg = (
        f"ℹ️ Telegram Watcher {label} Summary\n"
        f"Status: Running ✅\n"
        f"Uptime: {uptime}\n"
        f"Messages Scanned: {STATS['messages_seen']}\n"
        f"Alerts Sent: {STATS['alerts_sent']}"
    )

    send_whatsapp_alert(summary_msg)

    # Reset counters after summary
    STATS['messages_seen'] = 0
    STATS['alerts_sent'] = 0

async def heartbeat_loop(telegram_client):
    """
    Updates heartbeat ONLY if the Telegram client is connected.
    If disconnected, stops writing → healthcheck detects stale file → Docker restarts.
    """
    while True:
        try:
            if telegram_client.is_connected():
                with open("/tmp/heartbeat", "w") as f:
                    f.write(str(datetime.datetime.now()))
            else:
                print("⚠️ Heartbeat skipped: Telegram client not connected")
        except Exception as e:
            print(f"Error writing heartbeat: {e}")

        await asyncio.sleep(60)

async def main():
    print("Starting Telegram Watcher...")
    retries = 0

    while retries < MAX_RETRIES:
        try:
            await client.start()
            register_handlers(client)

            # Start background tasks on first connect
            if retries == 0:
                client.loop.create_task(daily_summary_loop())
                client.loop.create_task(heartbeat_loop(client))

            print("Telegram Watcher is running and listening for messages...")
            await client.run_until_disconnected()

            # If we get here, the connection dropped cleanly
            print("⚠️ Disconnected from Telegram. Attempting reconnect...")
            send_whatsapp_alert("⚠️ Telegram Watcher disconnected! Attempting auto-reconnect...")

        except Exception as e:
            print(f"❌ Connection error: {e}")
            send_whatsapp_alert(f"❌ Telegram Watcher error: {e}. Retrying...")

        retries += 1
        backoff = min(INITIAL_BACKOFF * (2 ** retries), 300)  # max 5 min
        print(f"Reconnecting in {backoff}s (attempt {retries}/{MAX_RETRIES})...")
        await asyncio.sleep(backoff)

    # Exhausted all retries — exit so Docker restarts the entire container
    print("💀 Max retries exhausted. Exiting for Docker restart...")
    send_whatsapp_alert("💀 Telegram Watcher: max reconnect retries exhausted. Container will restart.")
    exit(1)

if __name__ == '__main__':
    client.loop.run_until_complete(main())
