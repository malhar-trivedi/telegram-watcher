from telethon import events
import os
from notifier import send_whatsapp_alert

# Load keywords from env (comma separated)
TARGET_KEYWORDS = os.getenv('TARGET_KEYWORDS', '').lower().split(',')
TARGET_KEYWORDS = [k.strip() for k in TARGET_KEYWORDS if k.strip()]

# Load specific chats to monitor (Comma separated Chat IDs or exact Titles)
# Examples: -100123456789, My Group Chat, Another Group
target_chats_env = os.getenv('TARGET_CHATS', '')
TARGET_CHATS = [c.strip() for c in target_chats_env.split(',') if c.strip()]

# Statistics tracking
STATS = {
    'start_time': None,
    'messages_seen': 0,
    'alerts_sent': 0
}

def register_handlers(client):
    import datetime
    STATS['start_time'] = datetime.datetime.now()

    @client.on(events.NewMessage(incoming=True))
    async def handler(event):
        STATS['messages_seen'] += 1
        try:
            chat = await event.get_chat()
            chat_title = getattr(chat, 'title', 'Private Chat')
            chat_id = str(chat.id)

            # --- Chat Filtering ---
            # If TARGET_CHATS is set, we only proceed if the chat matches by ID or Title.
            # We strip "-100" prefixes sometimes found in ID strings just in case, but exact match is safer.
            if TARGET_CHATS:
                # Check for ID match or Title match (case-insensitive for title)
                match_found = False
                for t_chat in TARGET_CHATS:
                    if t_chat == chat_id:
                        match_found = True
                        break
                    if t_chat.lower() == chat_title.lower():
                        match_found = True
                        break

                if not match_found:
                    # Ignore this message
                    return

            message_text = event.message.message.lower() if event.message.message else ""
            sender = await event.get_sender()
            sender_name = getattr(sender, 'first_name', 'Unknown')

            print(f"New message in {chat_title} (ID: {chat_id}) from {sender_name}...")

            # 1. Check for Images
            if event.message.photo:
                print(f"Image detected from {sender_name}. Sending alert...")
                alert_message = (
                    f"🚨 Telegram Watcher Alert!\n"
                    f"Type: Image Detected 📸\n"
                    f"Chat: {chat_title}\n"
                    f"User: {sender_name}\n"
                    f"Caption: {event.message.message if event.message.message else '[No Caption]'}"
                )
                success = send_whatsapp_alert(alert_message)
                if success: STATS['alerts_sent'] += 1

            # 2. Check for Keywords (if text exists)
            if message_text:
                for keyword in TARGET_KEYWORDS:
                    if keyword in message_text:
                        print(f"Keyword '{keyword}' matched! Sending alert...")

                        alert_message = (
                            f"🚨 Telegram Watcher Alert!\n"
                            f"Type: Keyword Match 💬\n"
                            f"Keyword: {keyword}\n"
                            f"Chat: {chat_title}\n"
                            f"User: {sender_name}\n"
                            f"Message: {event.message.message}"
                        )

                        success = send_whatsapp_alert(alert_message)
                        if success: STATS['alerts_sent'] += 1
                        break  # Stop checking other keywords if one matches

        except Exception as e:
            print(f"Error processing message: {e}")
