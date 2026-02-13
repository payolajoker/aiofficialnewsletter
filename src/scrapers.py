import requests
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
import logging
from datetime import datetime
import time
from io import BytesIO

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

def fetch_feed(url):
    """Fetches and parses an RSS feed using BeautifulSoup."""
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        
        # Use html.parser which is lenient and available
        soup = BeautifulSoup(response.content, 'html.parser')
        
        entries = []
        # Try both 'item' (RSS) and 'entry' (Atom)
        items = soup.find_all(['item', 'entry'])
        
        for item in items:
            entry = {}
            
            # Title
            title_tag = item.find('title')
            entry['title'] = title_tag.get_text(strip=True) if title_tag else "No Title"
            
            # Link
            link_tag = item.find('link')
            if link_tag:
                # Atom <link href="..."> vs RSS <link>...</link>
                # BeautifulSoup might treat <link> in RSS as self-closing if using html.parser depending on context,
                # but usually works.
                # In RSS, link is text content. In Atom, it's href attr.
                if link_tag.get('href'):
                     entry['link'] = link_tag.get('href')
                else:
                     entry['link'] = link_tag.get_text(strip=True)
                
                # If link is empty but there's a guid (common in some feeds)
                if not entry['link']:
                     guid = item.find('guid')
                     if guid: entry['link'] = guid.get_text(strip=True)
            else:
                entry['link'] = ""

            # Published
            pub_tag = item.find(['pubdate', 'published', 'updated', 'dc:date'])
            entry['published'] = pub_tag.get_text(strip=True) if pub_tag else datetime.now().isoformat()
            
            # Summary
            summary_tag = item.find(['description', 'summary', 'content', 'content:encoded'])
            if summary_tag:
                 entry['summary'] = summary_tag.get_text(separator=' ', strip=True)
            else:
                 entry['summary'] = ""
                 
            entries.append(entry)
            
        return entries
    except Exception as e:
        logger.error(f"Failed to fetch feed {url}: {e}")
        return []

def get_google_ai_news():
    """Fetches from Google AI Blog RSS."""
    url = "https://blog.google/technology/ai/rss/"
    entries = fetch_feed(url)
    news = []
    for entry in entries[:5]: # Check latest 5
        news.append({
            "source": "Google AI Blog",
            "title": entry['title'],
            "link": entry['link'],
            "published": entry.get('published', datetime.now().isoformat()),
            "summary": entry.get('summary', "")
        })
    return news

def get_deepmind_news():
    """Fetches from Google DeepMind Blog."""
    # DeepMind requires JS rendering or complex scraping.
    # Currently returning empty to avoid errors.
    # TODO: Implement robust DeepMind scraping or find valid RSS.
    return []

def get_openai_news():
    """Fetches from OpenAI News RSS."""
    # Note: OpenAI RSS might be incomplete or delayed, but let's try it.
    url = "https://openai.com/news/rss.xml"
    entries = fetch_feed(url)
    news = []
    for entry in entries[:5]:
        news.append({
            "source": "OpenAI News",
            "title": entry['title'],
            "link": entry['link'],
            "published": entry.get('published', ""),
            "summary": entry.get('summary', "")
        })
    return news

def get_chatgpt_release_notes():
    """Fetches ChatGPT Release Notes."""
    url = "https://help.openai.com/en/articles/6825453-chatgpt-release-notes"
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        if response.status_code == 403:
            logger.warning("ChatGPT Release Notes Access Forbidden (403).")
            return []
            
        soup = BeautifulSoup(response.content, 'html.parser')
        news = []
        return news
    except Exception as e:
        logger.error(f"Failed to scrape ChatGPT Notes: {e}")
        return []

def get_anthropic_news():
    """Scrapes Anthropic News."""
    url = "https://www.anthropic.com/news"
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        news = []
        
        links = soup.find_all('a', href=True)
        import re
        date_pattern = re.compile(r'[A-Za-z]{3}\s+\d{1,2},\s+\d{4}')
        
        for link in links:
            href = link['href']
            if '/news/' in href or '/research/' in href:
                # Get text with separator to split components
                text_content = link.get_text(separator='|', strip=True)
                parts = [p.strip() for p in text_content.split('|') if p.strip()]
                
                # Filter parts
                candidates = []
                for part in parts:
                    # Skip dates
                    if date_pattern.search(part):
                        continue
                    # Skip common categories/metadata
                    if part.lower() in ['announcements', 'research', 'news', 'policy', 'product', 'company', 'company news', 'learning']:
                        continue
                    # Skip very short texts (often icons or symbols)
                    if len(part) < 3:
                        continue
                    candidates.append(part)
                
                if candidates:
                    # The first candidate after filtering dates/categories is likely the title.
                    # Summaries usually come after or are much longer/descriptive, but structurally title is first.
                    title = candidates[0]
                    
                    full_link = f"https://www.anthropic.com{href}" if not href.startswith('http') else href
                    
                    news.append({
                        "source": "Anthropic",
                        "title": title,
                        "link": full_link,
                        "published": datetime.now().isoformat(),
                        "summary": ""
                    })

        # Deduplicate
        seen = set()
        unique_news = []
        for n in news:
            if n['link'] not in seen:
                seen.add(n['link'])
                unique_news.append(n)
        return unique_news[:5]
    except Exception as e:
        logger.error(f"Failed to scrape Anthropic: {e}")
        return []

def get_all_news():
    all_news = []
    all_news.extend(get_google_ai_news())
    all_news.extend(get_deepmind_news())
    all_news.extend(get_openai_news())
    all_news.extend(get_chatgpt_release_notes())
    all_news.extend(get_anthropic_news())
    return all_news
