import os
import requests
from xml.etree import ElementTree as ET
import time

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")

# RSS с актами, берём побольше, чтобы было из чего фильтровать
RSS_URL = "http://publication.pravo.gov.ru/api/rss?pageSize=200"


# ================== TELEGRAM ==================
def send_message(text: str):
    if not BOT_TOKEN or not CHANNEL_ID:
        print("Нет BOT_TOKEN или CHANNEL_ID")
        return

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    try:
        r = requests.post(
            url,
            data={
                "chat_id": CHANNEL_ID,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            },
            timeout=15,
        )

        if r.status_code != 200:
            print("Ошибка Telegram:", r.text)

    except Exception as e:
        print("Ошибка отправки:", e)


# ================== ФИЛЬТР ВАЖНЫХ АКТОВ ==================
def is_important(title: str) -> bool:
    """
    Оставляем только то, что реально интересно:
    - Федеральные законы
    - Указы Президента РФ
    - Постановления Правительства РФ
    """
    t = title.lower()

    keywords = [
        "федеральный закон",
        "указ президента российской федерации",
        "указ президента рф",
        "президент российской федерации",
        "постановление правительства российской федерации",
    ]

    return any(k in t for k in keywords)


# ================== ПОЛУЧЕНИЕ ДАННЫХ ИЗ RSS ==================
def get_new_laws(limit: int = 10):
    try:
        response = requests.get(RSS_URL, timeout=15)
        response.raise_for_status()

        root = ET.fromstring(response.content)

        laws = []

        for item in root.findall(".//item"):
            title = item.findtext("title", default="") or ""
            link = item.findtext("link", default="") or ""
            pub_date = item.findtext("pubDate", default="") or ""
            description = item.findtext("description", default="") or ""

            # фильтруем только важное
            if not is_important(title):
                continue

            laws.append(
                {
                    "title": title.strip(),
                    "link": link.strip(),
                    "date": pub_date.strip(),
                    "desc": (description.strip()[:800] + "…")
                    if description
                    else "",
                }
            )

        # берём максимум limit штук
        return laws[:limit]

    except Exception as e:
        print("Ошибка RSS:", e)
        return []


# ================== MAIN ==================
if __name__ == "__main__":
    print("Запуск...")

    laws = get_new_laws(limit=5)  # максимум 5 важных актов за запуск

    if not laws:
        send_message("📭 Нет новых важных законов (президент / федеральные / правительство)")
    else:
        for law in laws:
            text = (
                f"📄 <b>{law['title']}</b>\n\n"
                f"📅 {law['date']}\n\n"
                f"{law['desc']}\n\n"
                f"🔗 <a href='{law['link']}'>Читать полностью</a>"
            )

            send_message(text)
            print("Отправлено:", law["title"])

            time.sleep(2)  # небольшая пауза, чтобы не заспамить
