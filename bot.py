import os
import requests
from xml.etree import ElementTree as ET
from bs4 import BeautifulSoup
import time

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")

RSS_URL = "http://publication.pravo.gov.ru/api/rss?pageSize=200"
CONSULTANT_URL = "https://www.consultant.ru/legalnews/buh/"
GARANT_URL = "https://www.garant.ru/hotlaw/federal/archive/2026/"
RNK_URL = "https://e.rnk.ru/"

def send_message(text: str):
    if not BOT_TOKEN or not CHANNEL_ID:
        print("Нет BOT_TOKEN или CHANNEL_ID")
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

def is_important(title: str) -> bool:
    t = title.lower()
    keywords = ["федеральный закон","указ президента","постановление правительства","налог","штраф","изменение"]
    return any(k in t for k in keywords)

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
            if not is_important(title):
                continue
            laws.append({
                "title": title.strip(),
                "link": link.strip(),
                "date": pub_date.strip(),
                "desc": (description.strip()[:800] + "…") if description else "",
            })
        return laws[:limit]
    except Exception as e:
        print("Ошибка RSS:", e)
        return []

def fetch_site(url: str):
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        return r.text
    except Exception as e:
        print("Ошибка загрузки сайта:", url, e)
        return ""

def parse_consultant(html: str):
    soup = BeautifulSoup(html, "html.parser")
    items = []
    for item in soup.select("div.listing-news__item"):
        title_tag = item.select_one("a.listing-news__item-title")
        date_tag = item.select_one("div.listing-news__item-date")
        desc_tag = item.select_one("span.listing-news__item-description")
        if title_tag:
            title = title_tag.get_text(strip=True)
            link = title_tag.get("href", "")
            if not link.startswith("http"):
                link = "https://www.consultant.ru" + link
            date = date_tag.get_text(strip=True) if date_tag else ""
            desc = desc_tag.get_text(strip=True) if desc_tag else ""
            if is_important(title):
                items.append({"title": title, "link": link, "date": date, "desc": desc})
    return items

def parse_garant(html: str):
    soup = BeautifulSoup(html, "html.parser")
    items = []
    for item in soup.select("div.listing_news a"):
        title = item.get_text(strip=True)
        link = item.get("href", "")
        if title and link:
            if not link.startswith("http"):
                link = "https://www.garant.ru" + link
            if is_important(title):
                items.append({"title": title, "link": link, "date": "", "desc": ""})
    return items

def parse_rnk(html: str):
    soup = BeautifulSoup(html, "html.parser")
    items = []
    for item in soup.select("div.header-panel__news ul li a"):
        title = item.get_text(strip=True)
        link = item.get("href", "")
        if title and link:
            if not link.startswith("http"):
                link = "https://www.rnk.ru" + link
            if is_important(title):
                items.append({"title": title, "link": link, "date": "", "desc": ""})
    return items

def get_extra_news():
    news = []
    html = fetch_site(CONSULTANT_URL)
    if html:
        news.extend(parse_consultant(html))
    html = fetch_site(GARANT_URL)
    if html:
        news.extend(parse_garant(html))
    html = fetch_site(RNK_URL)
    if html:
        news.extend(parse_rnk(html))
    return news

if __name__ == "__main__":
    print("Запуск...")
    laws = get_new_laws(limit=5)
    extra = get_extra_news()
    all_items = laws + extra
    if not all_items:
        send_message("📭 Нет новых важных законов или налоговых изменений")
    else:
        for law in all_items:
            text = (
                f"📄 <b>{law['title']}</b>\n\n"
                f"📅 {law['date']}\n\n"
                f"{law['desc']}\n\n"
                f"🔗 <a href='{law['link']}'>Читать полностью</a>"
            )
            send_message(text)
            print("Отправлено:", law["title"])
            time.sleep(2)
