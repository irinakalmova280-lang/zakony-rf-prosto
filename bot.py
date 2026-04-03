import os
import requests

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")

def send_message(text: str):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": CHANNEL_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    try:
        r = requests.post(url, data=data, timeout=15)
        print("Статус отправки:", r.status_code)
        if r.status_code != 200:
            print("Ошибка Telegram:", r.text)
    except Exception as e:
        print("Ошибка при отправке:", e)

def get_new_laws():
    # Прямая ссылка на RSS (актуальная на 2026)
    rss_url = "http://publication.pravo.gov.ru/api/rss?pageSize=50"
    
    try:
        response = requests.get(rss_url, timeout=15)
        response.raise_for_status()
        
        # Простой парсинг без feedparser (чтобы меньше ошибок)
        from xml.etree import ElementTree as ET
        root = ET.fromstring(response.content)
        
        items = []
        for item in root.findall(".//item")[:5]:   # берём максимум 5 последних
            title = item.find("title").text if item.find("title") is not None else "Без названия"
            link = item.find("link").text if item.find("link") is not None else ""
            pub_date = item.find("pubDate").text if item.find("pubDate") is not None else "Дата неизвестна"
            description = item.find("description").text if item.find("description") is not None else ""
            
            items.append({
                "title": title.strip(),
                "link": link,
                "date": pub_date,
                "desc": description[:350] if description else ""
            })
        return items
        
    except Exception as e:
        print("Ошибка при получении данных:", e)
        return []

if __name__ == "__main__":
    print("Запуск проверки новых законов...")
    laws = get_new_laws()
    
    if not laws:
        send_message("⚠️ Пока нет новых опубликованных актов или ошибка подключения к pravo.gov.ru")
    else:
        for law in laws:
            text = (
                f"📄 <b>{law['title']}</b>\n\n"
                f"📅 {law['date']}\n\n"
                f"{law['desc']}\n\n"
                f"🔗 <a href='{law['link']}'>Читать полный текст →</a>"
            )
            send_message(text)
            print("Отправлено:", law['title'][:70])
