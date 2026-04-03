import os
import requests
import feedparser  # эту библиотеку нужно установить: pip install feedparser

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")

def send_message(text: str):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": CHANNEL_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": False,
    }
    try:
        r = requests.post(url, data=data, timeout=10)
        r.raise_for_status()
        print("Сообщение отправлено успешно")
    except Exception as e:
        print("Ошибка отправки в Telegram:", e)

def fetch_latest_laws(limit: int = 5):
    # Самая хорошая лента — только федеральные законы и акты
    rss_url = "http://publication.pravo.gov.ru/api/rss?block=federal&pageSize=50"
    
    feed = feedparser.parse(rss_url)
    
    laws = []
    for entry in feed.entries[:limit]:
        title = entry.get("title", "Без названия")
        link = entry.get("link", "")
        published = entry.get("published", "Дата неизвестна")
        summary = entry.get("summary", "")[:400]  # короткое описание
        
        laws.append({
            "title": title,
            "link": link,
            "published": published,
            "summary": summary
        })
    return laws

def format_law(law):
    text = (
        f"📄 <b>{law['title']}</b>\n\n"
        f"📅 Опубликовано: {law['published']}\n\n"
        f"{law['summary']}\n\n"
        f"🔗 <a href='{law['link']}'>Читать полный текст на pravo.gov.ru</a>"
    )
    return text

if __name__ == "__main__":
    print("Запуск бота...")
    laws = fetch_latest_laws(limit=3)
    
    if not laws:
        send_message("Пока нет новых федеральных актов.")
    else:
        for law in laws:
            msg = format_law(law)
            send_message(msg)
            print("Отправлен закон:", law['title'][:60])
