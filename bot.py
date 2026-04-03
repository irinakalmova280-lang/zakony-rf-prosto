import os
import requests

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")

def send_message(text: str):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": CHANNEL_ID,
        "text": text
    }
    r = requests.post(url, data=data)
    r.raise_for_status()

if __name__ == "__main__":
    send_message("Тест: бот теперь пишет прямо в канал.")
