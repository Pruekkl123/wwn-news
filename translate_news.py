# แปลข่าวใน news.json จากอังกฤษเป็นไทย (Google Translate ฟรี ไม่ต้องใช้ API key)
import json
from deep_translator import GoogleTranslator

tr = GoogleTranslator(source="en", target="th")


def th(text):
    if not text:
        return ""
    try:
        return tr.translate(text[:4500]) or text
    except Exception as e:
        print("translate error:", e)
        return text  # แปลไม่ได้ -> ใช้ข้อความอังกฤษแทน


with open("news.json", encoding="utf-8") as f:
    items = json.load(f)

for n in items:
    if not n.get("titleTh"):
        n["titleTh"] = th(n.get("title", ""))
    if not n.get("descTh"):
        n["descTh"] = th(n.get("desc", ""))

with open("news.json", "w", encoding="utf-8") as f:
    json.dump(items, f, ensure_ascii=False, indent=2)
print(f"translated {len(items)} articles")
