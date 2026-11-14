# แปลข่าวใน news.json จากอังกฤษเป็นไทย (ฟรี ไม่ต้องใช้ API key ไม่ต้องติดตั้งแพ็กเกจเพิ่ม)
# ลำดับการแปล: 1) ผ่าน /api/translate บนเว็บของเรา  2) เรียก Google Translate ตรงๆ
import json
import os
import time
import urllib.parse
import urllib.request

SITE = os.environ.get("SITE_URL", "https://wwn-news.vercel.app")
UA = {"User-Agent": "Mozilla/5.0 (compatible; WWNNewsBot/1.0)"}


def get_json(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode("utf-8"))


def via_site(text):
    return get_json(f"{SITE}/api/translate?q=" + urllib.parse.quote(text))["text"]


def via_google(text):
    j = get_json("https://translate.googleapis.com/translate_a/single?client=gtx&sl=en&tl=th&dt=t&q=" + urllib.parse.quote(text))
    return "".join(seg[0] for seg in j[0])


def th(text):
    if not text:
        return ""
    text = text[:1500]
    for fn in (via_site, via_google):
        try:
            out = fn(text)
            if out:
                return out
        except Exception as e:
            print(f"{fn.__name__} error: {e}")
        time.sleep(0.3)
    return ""  # แปลไม่ได้ -> เว้นว่าง ให้หน้าเว็บแปลเองภายหลัง


with open("news.json", encoding="utf-8") as f:
    items = json.load(f)

ok = 0
for n in items:
    if not n.get("titleTh") or n["titleTh"] == n.get("title"):
        n["titleTh"] = th(n.get("title", ""))
    if not n.get("descTh") or n["descTh"] == n.get("desc"):
        n["descTh"] = th(n.get("desc", ""))
    if n["titleTh"]:
        ok += 1

with open("news.json", "w", encoding="utf-8") as f:
    json.dump(items, f, ensure_ascii=False, indent=2)
print(f"translated {ok}/{len(items)} articles")
