import feedparser
import json
import re
import html
import time
import calendar
import hashlib
import urllib.request
from collections import Counter
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

OUT = "news.json"
PER_FEED = 25          # อ่านข่าวล่าสุดจากแต่ละประเทศสูงสุดกี่ข่าวต่อรอบ
MAX_AGE_DAYS = 14      # เก็บข่าวย้อนหลังกี่วัน (ข่าวเก่ากว่านี้จะถูกลบ)
MAX_NEW_PER_RUN = 250  # เปิดหน้าข่าวใหม่ได้สูงสุดกี่หน้าต่อรอบ (กันรันนานเกินไป ที่เหลือรอบหน้าค่อยทำ)
MIN_PER_DAY = 10       # เป้าหมายข่าวต่อวัน (ใช้เตือนใน log)
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
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=10) as r:
            page = r.read(600000).decode("utf-8", "ignore")
        return extract_page(page)
    except Exception as e:
        print(f"page error: {e}")
        return None, ""


def item_ts(item):
    if item.get("ts"):
        return item["ts"]
    try:
        return int(datetime.strptime(item.get("date", ""), "%b %d, %Y").timestamp() * 1000)
    except Exception:
        return 0


def main():
    # ข่าวเดิมที่เก็บไว้ (สะสมข้ามรอบ จะได้มีข่าวครบทุกวัน)
    try:
        with open(OUT, encoding="utf-8") as f:
            old = json.load(f)
    except Exception:
        old = []
    cutoff = datetime.now() - timedelta(days=MAX_AGE_DAYS)
    cutoff_ms = int(cutoff.timestamp() * 1000)
    items = {i["url"]: i for i in old if i.get("url") and item_ts(i) >= cutoff_ms}
    print(f"เก็บข่าวเดิมไว้ {len(items)} ข่าว")

    new_count = 0
    for category, feed_url in THE_LOCAL_FEEDS.items():
        try:
            feed = feedparser.parse(feed_url)
            if not feed.entries:
                print(f"Warning: no entries for {category} ({feed_url})")
                continue
            added = 0
            for entry in feed.entries[:PER_FEED]:
                link = getattr(entry, "link", "")
                if not link or link in items:
                    continue
                if getattr(entry, "published_parsed", None):
                    dt = datetime.fromtimestamp(calendar.timegm(entry.published_parsed))
                else:
                    dt = datetime.now()
                if dt < cutoff:
                    continue
                if new_count >= MAX_NEW_PER_RUN:
                    continue  # เกินโควตารอบนี้ ไว้รอบหน้า
                page_img, body = page_info(link)
                time.sleep(0.3)
                summary = clean(entry.summary) if hasattr(entry, "summary") else clean(entry.title)
                seed = hashlib.md5(link.encode()).hexdigest()[:10]
                items[link] = {
                    "id": 0,
                    "title": clean(entry.title, 300),
                    "cat": category,
                    "date": dt.strftime("%b %d, %Y"),
                    "ts": int(dt.timestamp() * 1000),
                    "img": rss_image(entry) or page_img or f"https://picsum.photos/seed/{seed}/800/600",
                    "desc": body if len(body) > len(summary) else summary,  # เนื้อข่าวแบบละเอียด
                    "summary": summary,
                    "url": link,
                }
                new_count += 1
                added += 1
            print(f"{category}: ข่าวใหม่ {added}")
        except Exception as e:
            print(f"Error fetching {category}: {e}")

    result = sorted(items.values(), key=item_ts, reverse=True)
    for i, n in enumerate(result, 1):
        n["id"] = i

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    per_day = Counter(n["date"] for n in result)
    for day in sorted(per_day, key=lambda d: datetime.strptime(d, "%b %d, %Y"), reverse=True):
        mark = "" if per_day[day] >= MIN_PER_DAY else f"  <-- น้อยกว่า {MIN_PER_DAY}"
        print(f"{day}: {per_day[day]} ข่าว{mark}")
    print(f"Successfully generated {len(result)} articles ({new_count} new).")


if __name__ == "__main__":
    main()
