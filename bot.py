import os
import csv
import io
import requests

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")

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

    # Берём первые N строк (в них обычно есть данные)
    return acts[:limit]

def format_act(row: dict) -> str:
    # Попробуем несколько вариантов названий колонок
    possible_organ_keys = [
        "Наименование принявшего органа",
        "Наименование принявшего органа НПА",
    ]
    possible_count_keys = [
        "Количество опубликованных документов за период",
        "Количество опубликованных НПА за период",
    ]
    possible_date_from_keys = [
        "Дата начала периода",
        "Начало периода публикации НПА",
    ]
    possible_date_to_keys = [
        "Дата окончания периода",
        "Окончание периода публикации НПА",
    ]
    possible_link_keys = [
        "Ссылка на список документов",
        "Ссылка на поисковую выборку",
    ]

    def first_non_empty(row, keys):
        for k in keys:
            if k in row and row[k].strip():
                return row[k].strip()
        return ""

    organ = first_non_empty(row, possible_organ_keys)
    count = first_non_empty(row, possible_count_keys)
    date_from = first_non_empty(row, possible_date_from_keys)
    date_to = first_non_empty(row, possible_date_to_keys)
    link = first_non_empty(row, possible_link_keys)

    if not (organ or link):
        return ""

    text = (
        f"<b>{organ or 'Не указан орган'}</b>\n"
        f"Период: {date_from or '?'} – {date_to or '?'}\n"
        f"Опубликовано документов: {count or '?'}\n\n"
        f"Список документов: {link or 'нет ссылки'}"
    )
    return text

if __name__ == "__main__":
    acts = fetch_latest_acts(limit=3)
    if not acts:
        send_message("Пока нет данных в наборе открытых данных.")
    else:
        for act in acts:
            msg = format_act(act)
            if msg:
                send_message(msg)
