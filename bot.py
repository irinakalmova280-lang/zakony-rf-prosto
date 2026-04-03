
import os
import csv
import io
import requests
from datetime import datetime

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")

# ССЫЛКА НА CSV: возьми её со страницы "Правовые акты за последние 30 дней" на pravo.gov.ru (раздел "Открытые данные")
CSV_URL = "http://publication.pravo.gov.ru/opendata/7710349494-legalacts-30/data-legalacts-30.csv"
def send_message(text: str):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": CHANNEL_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    r = requests.post(url, data=data)
    r.raise_for_status()

def fetch_latest_acts(limit: int = 3):
    resp = requests.get(CSV_URL)
    resp.raise_for_status()

    content = resp.content.decode("utf-8", errors="ignore")
    reader = csv.DictReader(io.StringIO(content), delimiter=';')

    acts = list(reader)
    if not acts:
        return []

    # берём последние N записей
    return acts[-limit:]

def format_act(row: dict) -> str:
    organ = row.get("Наименование принявшего органа", "").strip()
    count = row.get("Количество опубликованных документов за период", "").strip()
    date_from = row.get("Дата начала периода", "").strip()
    date_to = row.get("Дата окончания периода", "").strip()
    link = row.get("Ссылка на список документов", "").strip()

    text = (
        f"<b>{organ}</b>\n"
        f"Период: {date_from} – {date_to}\n"
        f"Опубликовано документов: {count}\n\n"
        f"Список документов: {link}"
    )
    return text

if __name__ == "__main__":
    acts = fetch_latest_acts(limit=3)
    if not acts:
        send_message("Пока нет новых актов в открытых данных.")
    else:
        for act in acts:
            msg = format_act(act)
            send_message(msg)
