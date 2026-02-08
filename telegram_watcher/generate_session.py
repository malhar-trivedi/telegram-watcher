from telethon import TelegramClient
from telethon.sessions import StringSession
import asyncio

# Use explicit asyncio to avoid "no current event loop" errors with the sync wrapper
async def generate_session_async():
    print("=== Telegram Session Generator ===")
    print("You need your API ID and API HASH from https://my.telegram.org")

    api_id = input("Enter API ID: ").strip()
    api_hash = input("Enter API HASH: ").strip()

    if not api_id or not api_hash:
        print("Error: API ID and Hash are required.")
        return

    print("\nConnecting to Telegram... (You may be asked to enter your phone number and 2FA password)")

    client = TelegramClient(StringSession(), int(api_id), api_hash)

    # Start the client (triggers interactive auth)
    await client.start()

    print("\nSuccessfully logged in!")
    session_string = client.session.save()

    print("\n" + "="*50)
    print("YOUR SESSION STRING (Keep this safe!):")
    print("="*50)
    print(session_string)
    print("="*50 + "\n")
    print("Copy the string above and use it as the TELEGRAM_SESSION_STRING environment variable.")

    await client.disconnect()

def main():
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(generate_session_async())
    except Exception as e:
        print(f"\nError: {e}")

if __name__ == '__main__':
    main()
