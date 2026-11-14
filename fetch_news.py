import feedparser
import json
import re
import html
import urllib.request
import calendar
from datetime import datetime

THE_LOCAL_FEEDS = {
    'Sweden': 'https://feeds.thelocal.com/rss/se',
    'Denmark': 'https://feeds.thelocal.com/rss/dk',
    'Germany': 'https://feeds.thelocal.com/rss/de',
    'Europe': 'https://feeds.thelocal.com/rss/fr'
}

UA = {"User-Agent": "Mozilla/5.0 (compatible; WWNNewsBot/1.0)"}


def clean(text):
    text = re.sub(r"<[^>]+>", " ", text or "")
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def rss_image(entry):
    """หารูปจากข้อมูลใน RSS หลายช่องทาง"""
    for key in ("media_content", "media_thumbnail"):
        for m in getattr(entry, key, None) or []:
            if m.get("url"):
                return m["url"]
    for e in getattr(entry, "enclosures", None) or []:
        if e.get("type", "").startswith("image") and e.get("href"):
            return e["href"]
    blob = " ".join([getattr(entry, "summary", "")] +
                    [c.get("value", "") for c in (getattr(entry, "content", None) or [])])
    m = re.search(r'<img[^>]+src=["\']([^"\']+)', blob)
    return m.group(1) if m else None


def og_image(url):
    """ถ้า RSS ไม่มีรูป ให้เปิดหน้าข่าวแล้วดึงรูปปก (og:image)"""
    if not url:
        return None
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=8) as r:
            page = r.read(300000).decode("utf-8", "ignore")
        m = (re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)', page)
             or re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']', page))
        return html.unescape(m.group(1)) if m else None
    except Exception as e:
        print(f"og:image error: {e}")
        return None


all_news = []
news_id = 1

for category, feed_url in THE_LOCAL_FEEDS.items():
    try:
        feed = feedparser.parse(feed_url)
        entries = feed.entries[:10] if feed.entries else []

        for entry in entries:
            link = getattr(entry, "link", "")
            image_url = rss_image(entry) or og_image(link) or f"https://picsum.photos/id/{news_id * 10}/800/600"

            summary = clean(entry.summary) if hasattr(entry, 'summary') else clean(entry.title)

            if getattr(entry, "published_parsed", None):
                date = datetime.fromtimestamp(calendar.timegm(entry.published_parsed)).strftime("%b %d, %Y")
            else:
                date = datetime.now().strftime("%b %d, %Y")

            all_news.append({
                "id": news_id,
                "title": entry.title,
                "cat": category,
                "date": date,
                "img": image_url,
                "desc": summary,
                "url": link
            })
            news_id += 1
    except Exception as e:
        print(f"Error fetching {category}: {e}")

# บันทึกไฟล์ news.json
with open('news.json', 'w', encoding='utf-8') as f:
    json.dump(all_news, f, ensure_ascii=False, indent=2)

print(f"Successfully generated {len(all_news)} articles.")
