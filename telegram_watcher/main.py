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

async def heartbeat_loop():
    """
    Updates a local file timestamp every minute so Docker can check health.
    """
    while True:
        try:
            with open("/tmp/heartbeat", "w") as f:
                f.write(str(datetime.datetime.now()))
        except Exception as e:
            print(f"Error writing heartbeat: {e}")

        await asyncio.sleep(60)

async def main():
    print("Starting Telegram Watcher...")
    await client.start()

    # Register event handlers
    register_handlers(client)

    # Start background tasks
    client.loop.create_task(daily_summary_loop())
    client.loop.create_task(heartbeat_loop())

    print("Telegram Watcher is running and listening for messages...")
    await client.run_until_disconnected()

if __name__ == '__main__':
    client.loop.run_until_complete(main())
