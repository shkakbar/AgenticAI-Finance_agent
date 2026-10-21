import feedparser
import requests
from datetime import datetime, timedelta
from config import REGIONAL_NEWS_SOURCES, NATIVE_NEWS_SOURCES, REGIONS
import time
import os
import json

class RegionalNewsFetcher:
    def init(self):
        self.cache_dir = 'data/news_cache'
        os.makedirs(self.cache_dir, exist_ok=True)

    def fetch_regional_news(self, region, hours_back=24):
        """Fetch news for a specific region from English sources"""
        urls = REGIONAL_NEWS_SOURCES.get(region, [])
        region_info = REGIONS.get(region, {})
        all_news = []

        for url in urls:
            try:
                feed = feedparser.parse(url)
                for entry in feed.entries[:10]:  # Top 10 per source
                    news_item = self._parse_feed_entry(entry, region, region_info, url)
                    if news_item and self._is_recent(news_item, hours_back):
                        all_news.append(news_item)
            except Exception as e:
                print(f"      ⚠️  Error fetching {url}: {e}")

        return all_news

    def fetch_native_news(self, region, hours_back=24):
        """Fetch news from native language sources (no translation)"""
        native_config = NATIVE_NEWS_SOURCES.get(region, {})
        if not native_config:
            return []

        language = native_config.get('language', 'unknown')
        sources = native_config.get('sources', [])
        all_news = []
        region_info = REGIONS.get(region, {})

        for source_info in sources:
            url = source_info['url']
            source_name = source_info['name']
            try:
                feed = feedparser.parse(url)
                for entry in feed.entries[:8]:  # Top 8 per source
                    news_item = self._parse_feed_entry(entry, region, region_info, url, source_name)
                    if news_item and self._is_recent(news_item, hours_back):
                        # Mark as native language (no translation)
                        news_item['original_language'] = language
                        news_item['is_translated'] = False
                        all_news.append(news_item)
            except Exception as e:
                print(f"      ⚠️  Error fetching {source_name} ({url}): {e}")

        return all_news

    def fetch_all_regional_news(self, hours_back=24):
        """Fetch news from all regions (English + Native languages, no translation)"""
        all_news = []

        # English sources
        for region in REGIONAL_NEWS_SOURCES.keys():
            region_info = REGIONS.get(region, {})
            flag = region_info.get('flag', '🌐')
            name = region_info.get('name', region)
            print(f"  📡 Fetching English news for {flag} {name}...")
            news = self.fetch_regional_news(region, hours_back)
            all_news.extend(news)

        # Native language sources (no translation)
        print()
        print("  🌐 Fetching native language news (original language)...")
        for region in NATIVE_NEWS_SOURCES.keys():
            region_info = REGIONS.get(region, {})
            lang = NATIVE_NEWS_SOURCES[region].get('language', '?')
            flag = region_info.get('flag', '🌐')
            name = region_info.get('name', region)
            print(f"  📡 Fetching {lang.upper()} news for {flag} {name}...")
            news = self.fetch_native_news(region, hours_back)
            all_news.extend(news)

        # Deduplicate by title similarity
        all_news = self._deduplicate_news(all_news)

        return all_news

    def _parse_feed_entry(self, entry, region, region_info, source_url, source_name=None):
        """Parse a feed entry into a standardized news item"""
        try:
            # Extract published date
            published = ''
            if hasattr(entry, 'published'):
                published = entry.published
            elif hasattr(entry, 'updated'):
                published = entry.updated

            # Extract summary
            summary = ''
            if hasattr(entry, 'summary'):
                summary = entry.summary
                # Strip HTML tags
                import re
                summary = re.sub(r'<[^>]+>', '', summary)
                summary = summary.strip()[:500]

            # Determine source name
            if not source_name:
                source_name = entry.get('source', {}).get('title', '')
                if not source_name:
                    # Extract from URL
                    from urllib.parse import urlparse
                    parsed = urlparse(source_url)
                    source_name = parsed.netloc.replace('www.', '')

            return {
                'title': entry.get('title', ''),
                'link': entry.get('link', ''),
                'published': published,
                'summary': summary,
                'source': source_name,
                'region': region,
                'region_name': region_info.get('name', region),
                'region_flag': region_info.get('flag', '🌐'),
                'is_translated': False,
                'original_language': 'en'
            }
        except Exception as e:
            print(f"      ⚠️  Error parsing entry: {e}")
            return None

    def _is_recent(self, news_item, hours_back):
        """Check if news is within the time window"""
        try:
            if not news_item.get('published'):
                return True  # Include if no date

            # Try common date formats
            published_str = news_item['published']
            for fmt in [
                '%a, %d %b %Y %H:%M:%S %z',
                '%a, %d %b %Y %H:%M:%S %Z',
                '%Y-%m-%dT%H:%M:%S%z',
                '%Y-%m-%dT%H:%M:%SZ',
            ]:
                try:
                    published_dt = datetime.strptime(published_str, fmt)
                    cutoff = datetime.now(published_dt.tzinfo) - timedelta(hours=hours_back)
                    return published_dt >= cutoff
                except:
                    continue

            # If we can't parse the date, include it
            return True
        except:
            return True

    def _deduplicate_news(self, news_items):
        """Remove duplicate news based on title similarity"""
        seen_titles = set()
        unique_news = []

        for news in news_items:
            # Normalize title for comparison
            title = news.get('title', '').lower().strip()
            # Remove common words
            title = ' '.join([w for w in title.split() if len(w) > 3])

            if title not in seen_titles and len(title) > 10:
                seen_titles.add(title)
                unique_news.append(news)

        return unique_news