import os
import requests

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = "@название_канала"

def send_message(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    data = {
        "chat_id": CHAT_ID,
        "text": text
    }
    r = requests.post(url, data=data)
    r.raise_for_status()


# 🔎 Получаем "новость" (пока тестовая)
def get_law():
    return {
        "title": "Новый законопроект",
        "text": "В России рассматривается законопроект об изменении правил..."
    }


# 🧠 Упрощаем текст
def simplify(text):
    return f"Проще говоря: {text}"


def main():
    law = get_law()
    
    message = f"""📜 Новый закон

Название: {law['title']}

Суть:
{simplify(law['text'])}
"""
    send_message(message)


if __name__ == "__main__":
    main()
