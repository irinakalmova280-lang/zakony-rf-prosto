import os
import json
import hashlib
import requests
import time
from xml.etree import ElementTree as ET
from bs4 import BeautifulSoup

BOT_TOKEN  = os.getenv("TELEGRAM_BOT_TOKEN")
CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")
GROQ_KEY   = os.getenv("GROQ_API_KEY")        # ← добавили

SENT_FILE = "sent_ids.json"

# ── Источники ─────────────────────────────────────────────────────────────────

SOURCES = [
    {
        "name": "Российская газета",
        "url": "https://rg.ru/tema/4365/",
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

# ── Фильтр региональных законов ───────────────────────────────────────────────

REGIONAL_MARKERS = [
    "областной закон", "республик", "губернатор", "муниципальн",
    "псковской", "новгородской", "московской области", "ленинградской",
    "краснодарского", "свердловской", "челябинской", "самарской",
    "ростовской", "нижегородской", "татарстан", "башкортостан",
    "красноярского", "иркутской", "омской", "саратовской",
    "воронежской", "волгоградской", "пермского", "тюменской",
    "кемеровской", "оренбургской", "ставропольского", "приморского",
    "хабаровского", "астраханской", "брянской", "владимирской",
    "вологодской", "ивановской", "калужской", "костромской",
    "курской", "липецкой", "орловской", "рязанской", "смоленской",
    "тамбовской", "тверской", "тульской", "ярославской",
    "порховского", "пушкиногорского", "администраци области",
    "комитет по тарифам", "министерства транспорта и дорожного",
    "министерства строительства и жилищно-коммунального хозяйства",
    "министерства тарифов",
]

def is_federal(title: str) -> bool:
    t = title.lower()
    return not any(k in t for k in REGIONAL_MARKERS)

# ── Фильтры — только то что касается людей ───────────────────────────────────

MUST_KEYWORDS = [
    "штраф", "запрет", "запрещ", "обязан", "обязательн",
    "пособи", "выплат", "льгот", "материнск", "пенси",
    "жкх", "коммунал", "тариф", "плата за",
    "мрот", "зарплат", "трудов",
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
    "дети", "ребенок", "семь", "школ",
    "пенсионер", "инвалид", "ветеран",
    "военнослужащ", "мобилизац",
]

SKIP_KEYWORDS = [
    "усн", "ндс", "рсв", "аусн", "есхн", "ефс-1",
    "бухгалтер", "бухучет", "проводк",
    "арбитраж", "кассаци", "апелляци",
    "счет-фактур", "книга покупок", "книга продаж",
    "декларация по ндс", "налог на прибыль организаци",
    "страховые взносы организаци",
    "водоснабжени", "водоотведени", "канализаци",
    "порядок уведомлени", "конфликт интересов",
    "благоустройств", "рейтингового голосовани",
]

def is_for_people(title: str, desc: str = "") -> bool:
    text = (title + " " + desc).lower()
    if any(k in text for k in SKIP_KEYWORDS):
        return False
    return any(k in text for k in MUST_KEYWORDS)

# ── AI объяснение через Groq (бесплатно) ─────────────────────────────────────

def explain_with_groq(title: str, desc: str) -> str:
    if not GROQ_KEY:
        return ""
    try:
        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {GROQ_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "llama3-8b-8192",
                "max_tokens": 200,
                "messages": [
                    {
                        "role": "user",
                        "content": (
                            f"Новость: {title}\n{desc}\n\n"
                            "Объясни это простым языком для обычного человека "
                            "в 2-3 коротких предложениях. "
                            "Скажи: что изменилось, кого касается, "
                            "что нужно сделать (если нужно). "
                            "Без вступлений, сразу по делу. Начни с эмодзи 💡"
                        ),
                    }
                ],
            },
            timeout=20,
        )
        data = r.json()
        return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print("Ошибка Groq:", e)
        return ""

# ── Иконки по теме ────────────────────────────────────────────────────────────

ICONS = {
    "штраф": "🚨", "запрет": "🚫", "запрещ": "🚫",
    "пособи": "👶", "выплат": "💵", "льгот": "🎁",
    "пенси": "👴", "материнск": "👩‍👧",
    "жкх": "🏠", "коммунал": "🏠", "тариф": "💡",
    "водител": "🚗", "автомобил": "🚗", "парковк": "🅿️", "гибдд": "🚔",
    "зарплат": "💰", "мрот": "💰",
    "ипотек": "🏦", "медицин": "🏥", "больниц": "🏥", "полис": "🏥",
    "интернет": "📱", "vpn": "📱",
    "указ президента": "🏛", "федеральный закон": "⚖️", "законопроект": "📋",
    "дети": "👧", "школ": "🎒", "военнослужащ": "🪖",
}

def get_icon(title: str) -> str:
    t = title.lower()
    for key, icon in ICONS.items():
        if key in t:
            return icon
    return "📌"

# ── Форматирование ────────────────────────────────────────────────────────────

def format_message(item: dict, explanation: str = "") -> str:
    icon = get_icon(item["title"])
    lines = [f"{icon} <b>{item['title']}</b>"]

    if item.get("date"):
        lines.append(f"📅 {item['date']}")

    # AI объяснение вместо сырого описания
    if explanation:
        lines.append("")
        lines.append(explanation)
    elif item.get("desc"):
        desc = item["desc"].strip()
        if len(desc) > 400:
            desc = desc[:400].rsplit(" ", 1)[0] + "…"
        lines.append("")
        lines.append(desc)

    lines.append("")
    lines.append(f"Источник: {item.get('source', '')}")
    if item.get("link"):
        lines.append(f"🔗 <a href='{item['link']}'>Читать →</a>")

    lines.append("")
    lines.append("<i>ℹ️ Материал носит ознакомительный характер и не является юридической консультацией.</i>")

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
    try:
        root = ET.fromstring(html.encode("utf-8") if isinstance(html, str) else html)
        items = []
        for item in root.findall(".//item"):
            title = (item.findtext("title") or "").strip()
            link  = (item.findtext("link")  or "").strip()
            date  = (item.findtext("pubDate") or "").strip()
            desc  = BeautifulSoup(item.findtext("description") or "", "html.parser").get_text()
            if not is_federal(title):
                continue
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
    soup = BeautifulSoup(html, "html.parser")
    items = []
    for article in soup.select("article, div.article-item, div.b-material-wrapper__content"):
        a         = article.select_one("a[href]")
        title_tag = article.select_one("h2, h3, .title, .article-title")
        desc_tag  = article.select_one("p, .lead, .desc, .announce")
        date_tag  = article.select_one("time, .date, .article-date")
        if not a or not title_tag:
            continue
        title = title_tag.get_text(strip=True)
        desc  = desc_tag.get_text(strip=True) if desc_tag else ""
        date  = date_tag.get_text(strip=True) if date_tag else ""
        link  = a.get("href", "")
        if not link.startswith("http"):
            link = "https://rg.ru" + link
        if not is_federal(title):
            continue
        if not is_for_people(title, desc):
            continue
        items.append({
            "title": title, "link": link,
            "date": date, "desc": desc[:400],
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
        else:
            items = parse_rss(html, source["name"])
        print(f"   Подходящих: {len(items)}")
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

        # Объясняем через Groq
        explanation = explain_with_groq(item["title"], item.get("desc", ""))

        text = format_message(item, explanation)
        send_message(text)
        sent.add(uid)
        new_count += 1
        print(f"✅ Отправлено: {item['title'][:60]}")
        time.sleep(2)

    save_sent(sent)
    print(f"\nГотово. Отправлено новых: {new_count}")
