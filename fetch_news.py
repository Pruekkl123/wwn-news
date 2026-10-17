import feedparser
import json
from datetime import datetime

THE_LOCAL_FEEDS = {
    'Sweden': 'https://feeds.thelocal.com/rss/se',
    'Denmark': 'https://feeds.thelocal.com/rss/dk',
    'Germany': 'https://feeds.thelocal.com/rss/de',
    'Europe': 'https://feeds.thelocal.com/rss/fr'
}

all_news = []
news_id = 1

for category, feed_url in THE_LOCAL_FEEDS.items():
    try:
        feed = feedparser.parse(feed_url)
        entries = feed.entries[:10] if feed.entries else []
        
        for entry in entries:
            image_url = f"https://picsum.photos/id/{news_id * 10}/800/600"
            if hasattr(entry, 'media_content') and len(entry.media_content) > 0:
                image_url = entry.media_content[0].get('url', image_url)
            
            summary = entry.summary if hasattr(entry, 'summary') else entry.title

            all_news.append({
                "id": news_id,
                "title": entry.title,
                "cat": category,
                "date": datetime.now().strftime("%b %d, %Y"),
                "img": image_url,
                "desc": summary
            })
            news_id += 1
    except Exception as e:
        print(f"Error fetching {category}: {e}")

# บันทึกไฟล์ news.json
with open('news.json', 'w', encoding='utf-8') as f:
    json.dump(all_news, f, ensure_ascii=False, indent=2)

print(f"Successfully generated {len(all_news)} articles.")
