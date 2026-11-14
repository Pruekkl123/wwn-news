import feedparser
import json
import re
import html
import time
import calendar
import urllib.request
from datetime import datetime, timedelta

# The Local ครบทั้ง 9 ประเทศ
THE_LOCAL_FEEDS = {
    'Sweden': 'https://feeds.thelocal.com/rss/se',
    'Norway': 'https://feeds.thelocal.com/rss/no',
    'Denmark': 'https://feeds.thelocal.com/rss/dk',
    'Germany': 'https://feeds.thelocal.com/rss/de',
    'France': 'https://feeds.thelocal.com/rss/fr',
    'Italy': 'https://feeds.thelocal.com/rss/it',
    'Spain': 'https://feeds.thelocal.com/rss/es',
    'Switzerland': 'https://feeds.thelocal.com/rss/ch',
    'Austria': 'https://feeds.thelocal.com/rss/at',
}

PER_FEED = 10          # จำนวนข่าวต่อประเทศ
MAX_AGE_DAYS = 14      # ข้ามข่าวที่เก่ากว่านี้ (ใส่ 0 = ไม่กรอง)
BODY_CHARS = 1000      # ความยาวเนื้อข่าวที่ดึงมาแสดง (ย่อหน้าแรกๆ)
UA = {"User-Agent": "Mozilla/5.0 (compatible; WWNNewsBot/1.0)"}
SKIP = ("subscribe", "become a member", "sign up", "cookie", "newsletter", "log in",
        "read also", "read more", "advertisement", "already a member")


def clean(text, limit=400):
    text = re.sub(r"<[^>]+>", " ", text or "")
    return re.sub(r"\s+", " ", html.unescape(text)).strip()[:limit]


def rss_image(entry):
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


def extract_page(page):
    """ดึงรูปปก (og:image) และย่อหน้าแรกๆ ของข่าวจาก HTML"""
    m = (re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)', page)
         or re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']', page))
    img = html.unescape(m.group(1)) if m else None

    body_html = re.sub(r"<(script|style|noscript|nav|footer|header|aside|form)\b[\s\S]*?</\1>", " ", page, flags=re.I)
    paras, total = [], 0
    for p in re.finditer(r"<p\b[^>]*>([\s\S]*?)</p>", body_html, flags=re.I):
        t = clean(p.group(1), 2000)
        if len(t) < 60 or any(s in t.lower() for s in SKIP):
            continue
        paras.append(t)
        total += len(t)
        if total >= BODY_CHARS:
            break
    body = "\n\n".join(paras)
    if len(body) > BODY_CHARS + 300:  # ตัดที่จบประโยค
        cut = body[:BODY_CHARS + 300]
        body = cut[:cut.rfind(". ") + 1] if ". " in cut else cut
    return img, body


def page_info(url):
    if not url:
        return None, ""
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=10) as r:
            page = r.read(600000).decode("utf-8", "ignore")
        return extract_page(page)
    except Exception as e:
        print(f"page error: {e}")
        return None, ""


if __name__ == "__main__":
    all_news = []
    news_id = 1
    cutoff = datetime.now() - timedelta(days=MAX_AGE_DAYS) if MAX_AGE_DAYS else None

    for category, feed_url in THE_LOCAL_FEEDS.items():
        try:
            feed = feedparser.parse(feed_url)
            if not feed.entries:
                print(f"Warning: no entries for {category} ({feed_url})")
                continue
            count = 0
            for entry in feed.entries:
                if count >= PER_FEED:
                    break
                if getattr(entry, "published_parsed", None):
                    dt = datetime.fromtimestamp(calendar.timegm(entry.published_parsed))
                else:
                    dt = datetime.now()
                if cutoff and dt < cutoff:
                    continue

                link = getattr(entry, "link", "")
                page_img, body = page_info(link)
                time.sleep(0.3)
                summary = clean(entry.summary) if hasattr(entry, "summary") else clean(entry.title)
                image_url = rss_image(entry) or page_img or f"https://picsum.photos/id/{news_id * 10}/800/600"

                all_news.append({
                    "id": news_id,
                    "title": clean(entry.title, 300),
                    "cat": category,
                    "date": dt.strftime("%b %d, %Y"),
                    "img": image_url,
                    "desc": body if len(body) > len(summary) else summary,  # เนื้อข่าวแบบละเอียด
                    "summary": summary,
                    "url": link,
                })
                news_id += 1
                count += 1
        except Exception as e:
            print(f"Error fetching {category}: {e}")

    with open('news.json', 'w', encoding='utf-8') as f:
        json.dump(all_news, f, ensure_ascii=False, indent=2)

    print(f"Successfully generated {len(all_news)} articles.")
