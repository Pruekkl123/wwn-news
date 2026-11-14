"""ส่งข่าวเด่น (ภาษาไทย) เข้า LINE OA แบบ broadcast ถึงผู้ติดตามทุกคน
ต้องมี env LINE_CHANNEL_ACCESS_TOKEN  |  DRY_RUN=true = แสดงข้อความเฉยๆ ไม่ส่งจริง
"""
import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

SITE_URL = os.environ.get("SITE_URL", "https://wwn-news.vercel.app")
MAX_ITEMS = 5
SENT_FILE = "sent_news.json"


def load(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


news = load("news.json", [])
sent = set(load(SENT_FILE, []))

# หัวข้อที่มีคำเหล่านี้จะไม่ถูกส่งเข้า LINE (fun fact / คำศัพท์ประจำวัน / ควิซ)
EXCLUDE = ("word of the day", "expression of the day", "phrase of the day", "saying of the day",
           "word of the week", "fun fact", "did you know", "quiz")

groups = {}
for n in news:
    key = n.get("url") or n.get("title")
    if key in sent:
        continue
    if any(k in (n.get("title") or "").lower() for k in EXCLUDE):
        continue
    groups.setdefault(n.get("cat", ""), []).append(n)

picked = []
while len(picked) < MAX_ITEMS and any(groups.values()):
    for cat in list(groups):
        if groups[cat] and len(picked) < MAX_ITEMS:
            picked.append(groups[cat].pop(0))

if not picked:
    print("ไม่มีข่าวใหม่ที่ยังไม่เคยส่ง ข้ามการส่งรอบนี้")
    raise SystemExit(0)

now = datetime.now(timezone.utc) + timedelta(hours=7)
rnd = "รอบเช้า" if now.hour < 9 else "รอบเที่ยง" if now.hour < 15 else "รอบเย็น"
lines = [f"📰 ข่าว{rnd} {now.strftime('%d/%m/%Y')}", ""]
for i, n in enumerate(picked, 1):
    lines.append(f"{i}. {n.get('titleTh') or n['title']}")
    if n.get("url"):
        lines.append(n["url"])
    lines.append("")
lines.append(f"อ่านข่าวทั้งหมด: {SITE_URL}")
text = "\n".join(lines)[:4900]

if os.environ.get("DRY_RUN", "").lower() == "true":
    print("[DRY RUN] ข้อความที่จะส่ง:\n" + text)
    raise SystemExit(0)

token = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
if not token:
    raise SystemExit("ยังไม่ได้ตั้ง LINE_CHANNEL_ACCESS_TOKEN")

req = urllib.request.Request(
    "https://api.line.me/v2/bot/message/broadcast",
    data=json.dumps({"messages": [{"type": "text", "text": text}]}).encode("utf-8"),
    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    method="POST",
)
try:
    with urllib.request.urlopen(req, timeout=20) as r:
        print("ส่งเข้า LINE OA สำเร็จ:", r.status)
except urllib.error.HTTPError as e:
    raise SystemExit(f"LINE API error {e.code}: {e.read().decode('utf-8', 'ignore')}")

# จำข่าวที่ส่งแล้ว (เก็บ 300 รายการล่าสุด) เพื่อไม่ส่งซ้ำ
sent_list = list(sent) + [n.get("url") or n.get("title") for n in picked]
with open(SENT_FILE, "w", encoding="utf-8") as f:
    json.dump(sent_list[-300:], f, ensure_ascii=False, indent=1)
