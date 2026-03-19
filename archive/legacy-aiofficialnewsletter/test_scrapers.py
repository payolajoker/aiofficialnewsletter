from src.scrapers import get_all_news
import logging

logging.basicConfig(level=logging.INFO)

print("Testing Scrapers...")
try:
    news = get_all_news()
    print(f"Found {len(news)} items.")
    for item in news:
        print(f"- [{item['source']}] {item['title']} ({item['link']})")
except Exception as e:
    print(f"Error during testing: {e}")
