import os
import json
import hashlib
import requests
import time
from xml.etree import ElementTree as ET
from bs4 import BeautifulSoup

BOT_TOKEN  = os.getenv("TELEGRAM_BOT_TOKEN")
CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")

SENT_FILE = "sent_ids.json"

# ── Источники ─────────────────────────────────────────────────────────────────

SOURCES = [
    {
        "name": "Российская газета",
        "url": "https://rg.ru/tema/4365/",   # Законы для граждан
        "type": "rg",
    },
    {
        "name": "Официальное опубликование законов",
        "url": "http://publication.pravo.gov.ru/api/rss?pageSize=200",
        "type": "rss_pravo",
    },
    {
        "name": "Госуслуги — новости",
        "url": "https://www.gosuslugi.ru/newsrss",
        "type": "rss_gosuslugi",
    },
    {
        "name": "Роспотребнадзор",
        "url": "https://rospotrebnadzor.ru/rss/",
        "type": "rss_generic",
    },
]

# ── Фильтры — только то что касается людей ───────────────────────────────────

# Эти слова = точно берём
MUST_KEYWORDS = [
    "штраф", "запрет", "запрещ", "обязан", "обязательн",
    "пособи", "выплат", "льгот", "материнск", "пенси",
    "жкх", "коммунал", "тариф", "плата за",
    "МРОТ", "зарплат", "трудов",
    "водител", "автомобил", "парковк", "гибдд",
    "алкоголь", "табак", "курени",
    "указ президента", "федеральный закон",
    "законопроект", "госдума приняла", "подписал закон",
    "с 1 января", "с 1 февраля", "с 1 марта", "с 1 апреля",
    "с 1 мая", "с 1 июня", "с 1 июля", "с 1 августа",
    "с 1 сентября", "с 1 октября", "с 1 ноября", "с 1 декабря",
    "ипотек", "аренд", "недвижим",
    "медицин", "больниц", "полис", "омс",
    "мигрант", "гражданств", "виза", "регистраци",
    "интернет", "связь", "vpn", "мобильн",
]

# Эти слова = пропускаем (технические, не для людей)
SKIP_KEYWORDS = [
    "усн", "ндс", "рсв", "аусн", "есхн", "ефс-1",
    "бухгалтер", "бухучет", "проводк",
    "арбитраж", "кассаци", "апелляци",
    "счет-фактур", "книга покупок", "книга продаж",
    "декларация по ндс", "налог на прибыль организаци",
    "страховые взносы организаци",
]

def is_for_people(title: str, desc: str = "") -> bool:
    text = (title + " " + desc).lower()
    # Сначала проверяем — не технический ли
    if any(k in text for k in SKIP_KEYWORDS):
        return False
    # Потом проверяем — касается ли людей
    return any(k in text for k in MUST_KEYWORDS)


# ── Иконки по теме ────────────────────────────────────────────────────────────

ICONS = {
    "штраф": "🚨",
    "запрет": "🚫",
    "запрещ": "🚫",
    "пособи": "👶",
    "выплат": "💵",
    "льгот": "🎁",
    "пенси": "👴",
    "материнск": "👩‍👧",
    "жкх": "🏠",
    "коммунал": "🏠",
    "тариф": "💡",
    "водител": "🚗",
    "автомобил": "🚗",
    "парковк": "🅿️",
    "гибдд": "🚔",
    "зарплат": "💰",
    "мрот": "💰",
    "ипотек": "🏦",
    "медицин": "🏥",
    "больниц": "🏥",
    "полис": "🏥",
    "интернет": "📱",
    "vpn": "📱",
    "указ президента": "🏛",
    "федеральный закон": "⚖️",
    "законопроект": "📋",
}

def get_icon(title: str) -> str:
    t = title.lower()
    for key, icon in ICONS.items():
        if key in t:
            return icon
    return "📌"


# ── Форматирование — живой язык ───────────────────────────────────────────────

def format_message(item: dict) -> str:
    icon = get_icon(item["title"])
    lines = []

    lines.append(f"{icon} <b>{item['title']}</b>")

    if item.get("date"):
        lines.append(f"📅 {item['date']}")

    if item.get("desc"):
        desc = item["desc"].strip()
        if len(desc) > 400:
            desc = desc[:400].rsplit(" ", 1)[0] + "…"
        lines.append("")
        lines.append(desc)

    lines.append("")
    lines.append(f"Источник: {item.get('source', '')}")

    if item.get("link"):
        lines.append(f"🔗 <a href='{item['link']}'>Читать →</a>")

    return "\n".join(lines)


# ── Дедупликация ──────────────────────────────────────────────────────────────

def load_sent() -> set:
    if os.path.exists(SENT_FILE):
        with open(SENT_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    return set()

def save_sent(sent: set):
    with open(SENT_FILE, "w", encoding="utf-8") as f:
        json.dump(list(sent)[-1000:], f, ensure_ascii=False)

def make_id(title: str, link: str) -> str:
    return hashlib.md5((title + link).encode()).hexdigest()


# ── Telegram ──────────────────────────────────────────────────────────────────

def send_message(text: str):
    if not BOT_TOKEN or not CHANNEL_ID:
        print("⚠️  Нет BOT_TOKEN или CHANNEL_ID")
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        r = requests.post(url, data={
            "chat_id": CHANNEL_ID,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }, timeout=15)
        if r.status_code != 200:
            print("Ошибка Telegram:", r.text)
    except Exception as e:
        print("Ошибка отправки:", e)


# ── Парсеры ───────────────────────────────────────────────────────────────────

def fetch(url: str) -> str:
    try:
        r = requests.get(url, timeout=15, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        r.raise_for_status()
        return r.text
    except Exception as e:
        print(f"Ошибка загрузки {url}: {e}")
        return ""

def parse_rss(html: str, source_name: str) -> list:
    """Универсальный RSS парсер"""
    try:
        root = ET.fromstring(html.encode("utf-8") if isinstance(html, str) else html)
        items = []
        for item in root.findall(".//item"):
            title = (item.findtext("title") or "").strip()
            link  = (item.findtext("link")  or "").strip()
            date  = (item.findtext("pubDate") or "").strip()
            desc  = (item.findtext("description") or "").strip()
            # Убираем HTML теги из описания
            desc = BeautifulSoup(desc, "html.parser").get_text()
            if not is_for_people(title, desc):
                continue
            items.append({
                "title": title,
                "link": link,
                "date": date[:16] if date else "",
                "desc": desc[:400],
                "source": source_name,
            })
        return items
    except Exception as e:
        print(f"Ошибка RSS парсинга ({source_name}):", e)
        return []

def parse_rg(html: str) -> list:
    """Российская газета"""
    soup = BeautifulSoup(html, "html.parser")
    items = []
    for article in soup.select("article, div.article-item, div.b-material-wrapper__content"):
        a = article.select_one("a[href]")
        title_tag = article.select_one("h2, h3, .title, .article-title")
        desc_tag = article.select_one("p, .lead, .desc, .announce")
        date_tag = article.select_one("time, .date, .article-date")

        if not a or not title_tag:
            continue

        title = title_tag.get_text(strip=True)
        desc  = desc_tag.get_text(strip=True) if desc_tag else ""
        date  = date_tag.get_text(strip=True) if date_tag else ""
        link  = a.get("href", "")
        if not link.startswith("http"):
            link = "https://rg.ru" + link

        if not is_for_people(title, desc):
            continue

        items.append({
            "title": title,
            "link": link,
            "date": date,
            "desc": desc[:400],
            "source": "rg.ru",
        })
    return items


# ── Сбор всех новостей ────────────────────────────────────────────────────────

def collect_all_news() -> list:
    all_news = []

    for source in SOURCES:
        print(f"📡 Загружаю: {source['name']}...")
        html = fetch(source["url"])
        if not html:
            continue

        if source["type"] == "rg":
            items = parse_rg(html)
        elif source["type"] in ("rss_pravo", "rss_gosuslugi", "rss_generic"):
            items = parse_rss(html, source["name"])
        else:
            items = []

        print(f"   Найдено подходящих: {len(items)}")
        all_news.extend(items)

    return all_news


# ── Главная ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("🚀 Запуск бота...")

    sent = load_sent()
    all_items = collect_all_news()

    if not all_items:
        print("Новостей не найдено.")

    new_count = 0
    for item in all_items:
        uid = make_id(item["title"], item["link"])
        if uid in sent:
            print(f"⏭  Пропуск: {item['title'][:60]}")
            continue

        text = format_message(item)
        send_message(text)
        sent.add(uid)
        new_count += 1
        print(f"✅ Отправлено: {item['title'][:60]}")
        time.sleep(2)

    save_sent(sent)
    print(f"\nГотово. Отправлено новых: {new_count}")
