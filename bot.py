import os
import requests
from xml.etree import ElementTree as ET

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

def get_new_laws(limit: int = 5):
    rss_url = "http://publication.pravo.gov.ru/api/rss?pageSize=50"
    try:
        response = requests.get(rss_url, timeout=15)
        response.raise_for_status()
        root = ET.fromstring(response.content)

        items = []
        for item in root.findall(".//item")[:limit]:
            title = item.findtext("title", default="Без названия") or "Без названия"
            link = item.findtext("link", default="") or ""
            pub_date = item.findtext("pubDate", default="Дата неизвестна") or "Дата неизвестна"
            description = item.findtext("description", default="") or ""

            items.append({
                "title": title.strip(),
                "link": link.strip(),
                "date": pub_date.strip(),
                "desc": (description.strip()[:350] + "…") if description else ""
            })
        return items

    except Exception as e:
        print("Ошибка при получении данных:", e)
        return []

if __name__ == "__main__":
    print("Запуск проверки новых законов...")
    laws = get_new_laws(limit=5)

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
            print("Отправлено:", law['title'])
