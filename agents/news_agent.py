"""
News Agent - Fetches and processes financial news from RSS feeds.
Filters to last 24 hours. Structures news_by_asset for HTML generator.
"""
from agents.base_agent import BaseAgent
import feedparser
import requests
from bs4 import BeautifulSoup
from langdetect import detect
from datetime import datetime, timedelta, timezone
import time
import config

class NewsAgent(BaseAgent):
    def __init__(self, model_router=None, vector_db=None):
        super().__init__('NewsAgent', model_router, vector_db)
        self.headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }

    def execute(self, hours_back=24):
        """Fetch news from configured RSS feeds, filtered to last N hours."""
        self.log(f"Fetching news for the last {hours_back} hours...")

        regional_sources = getattr(config, 'REGIONAL_NEWS_SOURCES', {})
        native_sources = getattr(config, 'NATIVE_NEWS_SOURCES', {})
        regions_config = getattr(config, 'REGIONS', {})
        asset_classes = getattr(config, 'ASSET_CLASSES', {})

        if not regional_sources:
            self.log("No REGIONAL_NEWS_SOURCES found in config.py!", 'ERROR')
            return {'all_news': [], 'news_by_region': {}, 'news_by_asset': {}}

        all_news = []
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours_back)

        # Fetch from REGIONAL_NEWS_SOURCES
        for region_code, urls in regional_sources.items():
            region_info = regions_config.get(region_code, {'name': region_code, 'flag': '🌍'})

            for feed_url in urls:
                try:
                    response = requests.get(feed_url, headers=self.headers, timeout=10)

                    if response.status_code == 200:
                        feed = feedparser.parse(response.content)

                        for entry in feed.entries:
                            # Time filter: only include news from last N hours
                            published = entry.get('published_parsed') or entry.get('updated_parsed')
                            if published:
                                try:
                                    pub_time = datetime.fromtimestamp(time.mktime(published), tz=timezone.utc)
                                    if pub_time < cutoff_time:
                                        continue  # Skip old news
                                except (TypeError, ValueError, OSError):
                                    pass  # If we can't parse time, include it

                            title = entry.get('title', '').strip()
                            if not title:
                                continue

                            link = entry.get('link', '')
                            summary = entry.get('summary', '')

                            if summary:
                                summary = BeautifulSoup(summary, 'html.parser').get_text()[:300]

                            try:
                                lang = detect(title)
                            except Exception:
                                lang = 'en'

                            all_news.append({
                                'title': title,
                                'link': link,
                                'summary': summary,
                                'published': entry.get('published', ''),
                                'source': feed.feed.get('title', 'Unknown'),
                                'region_name': region_info.get('name', region_code),
                                'region_flag': region_info.get('flag', '🌍'),
                                'region_code': region_code,
                                'original_language': lang
                            })
                    else:
                        self.log(f"Feed returned {response.status_code}: {feed_url[:60]}", 'WARN')

                except Exception as e:
                    self.log(f"Failed: {feed_url[:60]} - {str(e)[:50]}", 'WARN')

        # Fetch from NATIVE_NEWS_SOURCES
        for region_code, source_info in native_sources.items():
            region_info = regions_config.get(region_code, {'name': region_code, 'flag': '🌍'})
            sources = source_info.get('sources', [])

            for src in sources:
                feed_url = src.get('url', '')
                source_name = src.get('name', 'Unknown')
                if not feed_url:
                    continue

                try:
                    response = requests.get(feed_url, headers=self.headers, timeout=10)
                    if response.status_code == 200:
                        feed = feedparser.parse(response.content)

                        for entry in feed.entries:
                            published = entry.get('published_parsed') or entry.get('updated_parsed')
                            if published:
                                try:
                                    pub_time = datetime.fromtimestamp(time.mktime(published), tz=timezone.utc)
                                    if pub_time < cutoff_time:
                                        continue
                                except (TypeError, ValueError, OSError):
                                    pass

                            title = entry.get('title', '').strip()
                            if not title:
                                continue

                            link = entry.get('link', '')
                            summary = entry.get('summary', '')
                            if summary:
                                summary = BeautifulSoup(summary, 'html.parser').get_text()[:300]

                            all_news.append({
                                'title': title,
                                'link': link,
                                'summary': summary,
                                'published': entry.get('published', ''),
                                'source': source_name,
                                'region_name': region_info.get('name', region_code),
                                'region_flag': region_info.get('flag', '🌍'),
                                'region_code': region_code,
                                'original_language': source_info.get('language', 'en')
                            })
                except Exception:
                    pass  # Silently skip failed native sources

        # Remove duplicates by title
        seen_titles = set()
        unique_news = []
        for n in all_news:
            title_key = n['title'].lower().strip()
            if title_key not in seen_titles:
                seen_titles.add(title_key)
                unique_news.append(n)
        all_news = unique_news

        # Group by region
        news_by_region = {}
        for news in all_news:
            region = news.get('region_name', 'Unknown')
            if region not in news_by_region:
                news_by_region[region] = []
            news_by_region[region].append(news)

        # Group by asset class - structured for HTML generator
        # HTML expects: [{'news': {...}, 'score': X, 'label': 'Y'}]
        news_by_asset = {asset: [] for asset in asset_classes.keys()}
        news_by_asset['Other'] = []

        for news in all_news:
            title_lower = news.get('title', '').lower()
            matched = False
            for asset_key, asset_config in asset_classes.items():
                keywords = asset_config.get('keywords', [])
                if any(kw.lower() in title_lower for kw in keywords):
                    news_by_asset[asset_key].append({
                        'news': news,
                        'score': 0,
                        'label': 'Neutral'
                    })
                    matched = True
                    break
            if not matched:
                news_by_asset['Other'].append({
                    'news': news,
                    'score': 0,
                    'label': 'Neutral'
                })

        self.log(f"Fetched {len(all_news)} news across {len(news_by_region)} regions.", 'SUCCESS')

        return {
            'all_news': all_news,
            'news_by_region': news_by_region,
            'news_by_asset': news_by_asset
        }

    