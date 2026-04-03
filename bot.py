import os
import csv
import io
import time
import requests
from datetime import datetime
from typing import List, Dict

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")

CSV_URL = "http://publication.pravo.gov.ru/opendata/7710349494-legalacts-30/data-legalacts-30.csv"

def send_message(text: str):
    """Отправка сообщения в Telegram"""
    if not BOT_TOKEN or not CHANNEL_ID:
        print("Ошибка: не заданы BOT_TOKEN или CHANNEL_ID")
        return
        
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": CHANNEL_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    try:
        r = requests.post(url, data=data, timeout=10)
        r.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Ошибка отправки в Telegram: {e}")

def fetch_latest_acts(limit: int = 3) -> List[Dict]:
    """Получение последних актов из CSV"""
    try:
        resp = requests.get(CSV_URL, timeout=10)
        resp.raise_for_status()
        
        # Определяем правильную кодировку
        content = resp.content.decode('utf-8-sig', errors='ignore')
        reader = csv.DictReader(io.StringIO(content), delimiter=';')
        
        acts = list(reader)
        if not acts:
            return []
        
        # Пытаемся отсортировать по дате начала периода (от новых к старым)
        try:
            acts.sort(key=lambda x: x.get("Начало периода публикации НПА", ""), reverse=True)
        except:
            pass  # Если сортировка не удалась, оставляем как есть
        
        return acts[:limit]
        
    except requests.exceptions.RequestException as e:
        print(f"Ошибка загрузки CSV: {e}")
        return []
    except Exception as e:
        print(f"Ошибка обработки CSV: {e}")
        return []

def format_act(row: Dict) -> str:
    """Форматирование одного акта для отправки"""
    organ = row.get("Наименование принявшего органа НПА", "Не указан").strip()
    count = row.get("Количество опубликованных НПА за период", "0").strip()
    date_from = row.get("Начало периода публикации НПА", "").strip()
    date_to = row.get("Окончание периода публикации НПА", "").strip()
    link = row.get("Ссылка на поисковую выборку", "").strip()
    
    # Проверяем, что ссылка существует
    if not link or link == "0":
        link = "Не указана"
    
    # Форматируем даты
    try:
        if date_from:
            date_from = datetime.strptime(date_from, "%Y-%m-%d").strftime("%d.%m.%Y")
        if date_to:
            date_to = datetime.strptime(date_to, "%Y-%m-%d").strftime("%d.%m.%Y")
    except:
        pass  # Если дата в другом формате, оставляем как есть
    
    text = (
        f"📄 <b>{organ}</b>\n"
        f"📅 Период: {date_from} – {date_to}\n"
        f"📊 Опубликовано документов: {count}\n"
        f"🔗 <a href='{link}'>Смотреть документы</a>"
    )
    return text

def debug_csv_structure():
    """Отладочная функция для просмотра структуры CSV"""
    try:
        resp = requests.get(CSV_URL, timeout=10)
        resp.raise_for_status()
        content = resp.content.decode('utf-8-sig', errors='ignore')
        reader = csv.DictReader(io.StringIO(content), delimiter=';')
        
        print("Поля в CSV:", reader.fieldnames)
        
        # Выводим первую запись для примера
        first_row = next(reader, None)
        if first_row:
            print("\nПример записи:")
            for key, value in first_row.items():
                print(f"  {key}: {value}")
    except Exception as e:
        print(f"Ошибка отладки: {e}")

if __name__ == "__main__":
    # Для отладки - раскомментируйте следующую строку:
    # debug_csv_structure()
    
    print("Запуск парсера...")
    acts = fetch_latest_acts(limit=3)
    
    if not acts:
        print("Нет данных для отправки")
        send_message("📭 Пока нет новых актов в открытых данных pravo.gov.ru")
    else:
        print(f"Найдено {len(acts)} актов, отправляем...")
        for i, act in enumerate(acts, 1):
            msg = format_act(act)
            print(f"\nАкт {i}:\n{msg}")
            send_message(msg)
            # Небольшая задержка между сообщениями, чтобы не спамить
            if i < len(acts):
                time.sleep(1)
