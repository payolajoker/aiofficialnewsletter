import os
import json
import logging
import requests
from datetime import datetime
from dotenv import load_dotenv
from scrapers import get_all_news
from translator import translate_content

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

HISTORY_FILE = "data/history.json"
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def save_history(history):
    os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

def send_discord_message(article):
    if not DISCORD_WEBHOOK_URL:
        logger.warning("Discord Webhook URL not set. Skipping message.")
        return

    embed = {
        "title": article['translated_title'],
        "description": article['translated_summary'] or article['summary'],
        "url": article['link'],
        "color": 5763719,
        "footer": {
            "text": f"Source: {article['source']} | 꿀꿀로드(OinkRoad)"
        },
        "timestamp": datetime.now().isoformat()
    }

    payload = {
        "username": "꿀꿀로드",
        "embeds": [embed]
    }

    try:
        response = requests.post(DISCORD_WEBHOOK_URL, json=payload)
        response.raise_for_status()
        logger.info(f"Sent to Discord: {article['title']}")
    except Exception as e:
        logger.error(f"Failed to send to Discord: {e}")

def main():
    logger.info("Starting AI News Check...")
    
    # 1. Load History
    history = load_history()
    history_links = {item['link'] for item in history}

    # 2. Fetch News
    news_items = get_all_news()
    logger.info(f"Fetched {len(news_items)} items.")

    new_items = []
    
    # 3. Filter New Items
    for item in news_items:
        if item['link'] not in history_links:
            new_items.append(item)

    if not new_items:
        logger.info("No new items found.")
        return

    # 4. Process New Items (Translate & Send)
    for item in new_items:
        logger.info(f"Processing new item: {item['title']}")
        
        # Translate Title
        item['translated_title'] = translate_content(item['title'])
        
        # Translate Summary (if exists and reasonably short)
        if item['summary']:
             # Truncate summary to avoid token limits if necessary, though Gemini is generous
             summary_text = item['summary'][:500] + "..." if len(item['summary']) > 500 else item['summary']
             item['translated_summary'] = translate_content(summary_text)
        else:
             item['translated_summary'] = "No Summary"

        # Update History immediately BEFORE sending to avoid duplicate sending if crash occurs after send
        history.append({
            "link": item['link'],
            "title": item['title'],
            "processed_at": datetime.now().isoformat()
        })
        save_history(history)

        # Send to Discord
        send_discord_message(item)
        
        # Limit processing to avoid spamming or rate limits if many new items
        # Just process all for now, but maybe add a sleep
        
    logger.info("News check completed.")

if __name__ == "__main__":
    main()
