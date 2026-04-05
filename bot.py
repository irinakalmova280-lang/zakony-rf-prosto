import os
import json
import hashlib
import requests
import time
from xml.etree import ElementTree as ET
from bs4 import BeautifulSoup

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")

RSS_URL = "http://publication.pravo.gov.ru/api/rss?pageSize=200"
CONSULTANT_URL = "https://www.consultant.ru/legalnews/buh/"
GARANT_URL = "https://www.garant.ru/hotlaw/federal/archive/2026/"
RNK_URL = "https://e.rnk.ru/"

SENT_FILE = "sent_ids.json"  # файл для хранения отправленных ID


# ── Дедупликация ─────────────────────────────────────────────────────────────

def load_sent() -> set:
    if os.path.exists(SENT_FILE):
        with open(SENT_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    return set()

def save_sent(sent: set):
    with open(SENT_FILE, "w", encoding="utf-8") as f:
        json.dump(list(sent), f, ensure_ascii=False)

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


# ── Форматирование ────────────────────────────────────────────────────────────

CATEGORY_ICONS = {
    "федеральный закон": "⚖️",
    "указ президента": "🏛",
    "постановление правительства": "📜",
    "налог": "💰",
    "штраф": "🚫",
    "изменение": "🔄",
}

def get_icon(title: str) -> str:
    t = title.lower()
    for key, icon in CATEGORY_ICONS.items():
        if key in t:
            return icon
    return "📄"

def format_message(item: dict) -> str:
    icon = get_icon(item["title"])
    parts = [f"{icon} <b>{item['title']}</b>"]

    if item.get("date"):
        parts.append(f"\n🗓 <i>{item['date']}</i>")

    if item.get("desc"):
        desc = item["desc"].strip()
        if len(desc) > 600:
            desc = desc[:600].rsplit(" ", 1)[0] + "…"
        parts.append(f"\n{desc}")

    if item.get("source"):
        parts.append(f"\n🔖 <i>Источник: {item['source']}</i>")

    if item.get("link"):
        parts.append(f"\n\n🔗 <a href='{item['link']}'>Читать полностью →</a>")

    return "\n".join(parts)


# ── Фильтрация ────────────────────────────────────────────────────────────────

KEYWORDS = [
    "федеральный закон", "указ президента", "постановление правительства",
    "налог", "штраф", "изменение"
]

def is_important(title: str) -> bool:
    t = title.lower()
    return any(k in t for k in KEYWORDS)


# ── Парсеры ───────────────────────────────────────────────────────────────────

def fetch(url: str) -> str:
    try:
        r = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        return r.text
    except Exception as e:
        print(f"Ошибка загрузки {url}: {e}")
        return ""

def get_new_laws(limit: int = 10) -> list:
    try:
        r = requests.get(RSS_URL, timeout=15)
        r.raise_for_status()
        root = ET.fromstring(r.content)
        laws = []
        for item in root.findall(".//item"):
            title = (item.findtext("title") or "").strip()
            link  = (item.findtext("link")  or "").strip()
            date  = (item.findtext("pubDate") or "").strip()
            desc  = (item.findtext("description") or "").strip()
            if not is_important(title):
                continue
            laws.append({
                "title": title,
                "link": link,
                "date": date,
                "desc": (desc[:600] + "…") if len(desc) > 600 else desc,
                "source": "pravo.gov.ru",
            })
        return laws[:limit]
    except Exception as e:
        print("Ошибка RSS:", e)
        return []

def parse_consultant(html: str) -> list:
    soup = BeautifulSoup(html, "html.parser")
    items = []
    for item in soup.select("div.listing-news__item"):
        a    = item.select_one("a.listing-news__item-title")
        date = item.select_one("div.listing-news__item-date")
        desc = item.select_one("span.listing-news__item-description")
        if not a:
            continue
        title = a.get_text(strip=True)
        if not is_important(title):
            continue
        link = a.get("href", "")
        if not link.startswith("http"):
            link = "https://www.consultant.ru" + link
        items.append({
            "title": title,
            "link": link,
            "date": date.get_text(strip=True) if date else "",
            "desc": desc.get_text(strip=True) if desc else "",
            "source": "consultant.ru",
        })
    return items

def parse_garant(html: str) -> list:
    soup = BeautifulSoup(html, "html.parser")
    items = []
    for a in soup.select("div.listing_news a"):
        title = a.get_text(strip=True)
        link  = a.get("href", "")
        if not title or not is_important(title):
            continue
        if not link.startswith("http"):
            link = "https://www.garant.ru" + link
        items.append({"title": title, "link": link, "date": "", "desc": "", "source": "garant.ru"})
    return items

def parse_rnk(html: str) -> list:
    soup = BeautifulSoup(html, "html.parser")
    items = []
    for a in soup.select("div.header-panel__news ul li a"):
        title = a.get_text(strip=True)
        link  = a.get("href", "")
        if not title or not is_important(title):
            continue
        if not link.startswith("http"):
            link = "https://www.rnk.ru" + link
        items.append({"title": title, "link": link, "date": "", "desc": "", "source": "rnk.ru"})
    return items

def get_extra_news() -> list:
    news = []
    for url, parser in [
        (CONSULTANT_URL, parse_consultant),
        (GARANT_URL,     parse_garant),
        (RNK_URL,        parse_rnk),
    ]:
        html = fetch(url)
        if html:
            news.extend(parser(html))
    return news


# ── Главная ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("🚀 Запуск бота...")

    sent = load_sent()
    laws  = get_new_laws(limit=5)
    extra = get_extra_news()
    all_items = laws + extra

    new_count = 0
    for item in all_items:
        uid = make_id(item["title"], item["link"])
        if uid in sent:
            print(f"⏭  Уже отправлено: {item['title'][:60]}")
            continue

        text = format_message(item)
        send_message(text)
        sent.add(uid)
        new_count += 1
        print(f"✅ Отправлено: {item['title'][:60]}")
        time.sleep(2)

    save_sent(sent)

    if new_count == 0:
        send_message("📭 Нет новых важных законов или налоговых изменений")
        print("Новых новостей нет.")
    else:
        print(f"Готово. Отправлено {new_count} новых сообщений.")
