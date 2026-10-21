import requests, feedparser, re
from datetime import datetime, timedelta
from config import FINNHUB_KEY, ALPHA_VANTAGE_KEY
import json
import os


# from config import REGIONS


class EconomicCalendarFetcher:
    def __init__(self):
        self.cache_dir = 'data/calendar_cache'
        os.makedirs(self.cache_dir, exist_ok=True)

    def fetch_upcoming_events(self, days_ahead=14):
        """Fetch upcoming economic events using multiple sources with fallbacks"""
        events = []
        today = datetime.now()

        # 1. Try Finnhub (if key exists)
        if FINNHUB_KEY and FINNHUB_KEY not in ["YOUR_ACTUAL_KEY_HERE", ""]:
            print("    Trying Finnhub API...")
            events = self._fetch_finnhub_calendar(days_ahead)
            if events:
                print(f"    ✅ Fetched {len(events)} events from Finnhub")

        # 2. Try Investing.com RSS (no API key needed!)
        if not events:
            print("    Trying Investing.com RSS (no API key needed)...")
            events = self._fetch_investing_rss(days_ahead)
            if events:
                print(f"    ✅ Fetched {len(events)} events from Investing.com")

        # 3. Final fallback: realistic mock calendar
        if not events:
            print("    💡 Using realistic upcoming economic events fallback.")
            events = self._get_mock_calendar(days_ahead)

        # Filter past events and sort
        today_str = today.strftime('%Y-%m-%d')
        events = [e for e in events if e.get('date', '') >= today_str]
        events.sort(key=lambda x: x['date'])

        self._cache_events(events)
        return events

    def _fetch_finnhub_calendar(self, days_ahead):
        """Fetch from Finnhub API"""
        events = []
        today = datetime.now()
        end_date = today + timedelta(days=days_ahead)

        try:
            url = 'https://finnhub.io/api/v1/calendar/economic'
            params = {
                'token': FINNHUB_KEY,
                'from': today.strftime('%Y-%m-%d'),
                'to': end_date.strftime('%Y-%m-%d'),
            }
            response = requests.get(url, params=params, timeout=15)

            if response.status_code != 200:
                print(f"    ⚠️  Finnhub returned status {response.status_code}")
                return []

            data = response.json()
            calendar_items = data.get('economicCalendar', [])
            if not calendar_items:
                return []

            country_map = {
                'US': {'flag': '🇺🇸', 'name': 'United States'},
                'EU': {'flag': '🇪🇺', 'name': 'European Union'},
                'JP': {'flag': '🇯🇵', 'name': 'Japan'},
                'CN': {'flag': '🇨🇳', 'name': 'China'},
                'GB': {'flag': '🇬🇧', 'name': 'United Kingdom'},
                'SE': {'flag': '🇸🇪', 'name': 'Sweden'},
                'DK': {'flag': '🇩🇰', 'name': 'Denmark'},
                'NO': {'flag': '🇳🇴', 'name': 'Norway'},
                'DE': {'flag': '🇩🇪', 'name': 'Germany'},
            }

            for item in calendar_items:
                country_code = item.get('country', '')
                if country_code not in country_map:
                    continue
                impact = item.get('impact', 'Low')
                if impact not in ['High', 'Medium']:
                    continue

                country_info = country_map[country_code]
                event_time = item.get('time', '')
                event_date = event_time[:10] if event_time else ''
                event_hour = event_time[11:16] if len(event_time) > 11 else ''

                if event_date < today.strftime('%Y-%m-%d'):
                    continue

                consensus = item.get('consensus')
                previous = item.get('previous')
                actual = item.get('actual')
                unit = item.get('unit', '')

                events.append({
                    'date': event_date,
                    'time': event_hour,
                    'event': item.get('event', 'Unknown'),
                    'country': country_info['name'],
                    'country_code': country_code,
                    'flag': country_info['flag'],
                    'impact': impact.upper(),
                    'forecast': f"{consensus}{unit}" if consensus is not None else 'N/A',
                    'previous': f"{previous}{unit}" if previous is not None else 'N/A',
                    'actual': f"{actual}{unit}" if actual is not None else 'Pending',
                    'currency': item.get('currency', ''),
                    'description': f"{item.get('event', '')} - {country_info['name']}",
                })

            return events[:20]

        except Exception as e:
            print(f"    ⚠️  Finnhub error: {e}")
            return []

    def _fetch_investing_rss(self, days_ahead):
        """Fetch economic calendar from Investing.com RSS feed (NO API KEY NEEDED)"""
        events = []
        today = datetime.now()
        end_date = today + timedelta(days=days_ahead)

        # Investing.com economic calendar RSS feeds by country
        rss_feeds = [
            {'url': 'https://www.investing.com/rss/news_14.rss', 'country': 'US', 'flag': '🇺🇸', 'name': 'United States'},
            {'url': 'https://www.investing.com/rss/news_15.rss', 'country': 'EU', 'flag': '🇪🇺', 'name': 'European Union'},
            {'url': 'https://www.investing.com/rss/news_12.rss', 'country': 'JP', 'flag': '🇯🇵', 'name': 'Japan'},
            {'url': 'https://www.investing.com/rss/news_126.rss', 'country': 'CN', 'flag': '🇨🇳', 'name': 'China'},
            {'url': 'https://www.investing.com/rss/news_11.rss', 'country': 'GB', 'flag': '🇬🇧', 'name': 'United Kingdom'},
            {'url': 'https://www.investing.com/rss/news_111.rss', 'country': 'SE', 'flag': '🇸🇪', 'name': 'Sweden'},
            {'url': 'https://www.investing.com/rss/news_72.rss', 'country': 'DE', 'flag': '🇩🇪', 'name': 'Germany'},
        ]

        # High-impact event keywords to filter for
        high_impact_keywords = [
            'interest rate', 'rate decision', 'cpi', 'inflation', 'gdp',
            'non-farm', 'payrolls', 'employment', 'unemployment', 'retail sales',
            'pce', 'ppi', 'fomc', 'ecb', 'boj', 'boe', 'riksbank',
            'trade balance', 'manufacturing pmi', 'services pmi',
            'consumer confidence', 'industrial production'
        ]

        for feed_info in rss_feeds:
            try:
                feed = feedparser.parse(feed_info['url'])
                for entry in feed.entries[:10]:
                    title = entry.get('title', '').lower()
                    summary = entry.get('summary', '').lower()
                    combined = title + ' ' + summary

                    # Check if this is a high-impact economic event
                    is_high_impact = any(kw in combined for kw in high_impact_keywords)
                    if not is_high_impact:
                        continue

                    # Try to extract date from published field
                    published = entry.get('published', '')
                    event_date = self._extract_date(published, today)
                    if not event_date:
                        continue

                    if event_date < today or event_date > end_date:
                        continue

                    # Extract forecast/previous from summary if available
                    forecast, previous = self._extract_forecast_previous(summary)

                    # Determine impact level
                    impact = 'HIGH' if any(kw in combined for kw in
                                ['rate decision', 'cpi', 'gdp', 'non-farm', 'fomc', 'ecb', 'boj']) else 'MEDIUM'

                    events.append({
                        'date': event_date.strftime('%Y-%m-%d'),
                        'time': '',
                        'event': entry.get('title', 'Economic Event'),
                        'country': feed_info['name'],
                        'country_code': feed_info['country'],
                        'flag': feed_info['flag'],
                        'impact': impact,
                        'forecast': forecast,
                        'previous': previous,
                        'actual': 'Pending',
                        'currency': '',
                        'description': entry.get('title', ''),
                        'link': entry.get('link', ''),
                    })
            except Exception as e:
                print(f"    ⚠️  RSS error for {feed_info['name']}: {e}")
                continue

        # Remove duplicates based on event name + date
        seen = set()
        unique_events = []
        for ev in events:
            key = (ev['event'], ev['date'])
            if key not in seen:
                seen.add(key)
                unique_events.append(ev)

        return unique_events[:20]

    def _extract_date(self, text, default_date):
        """Try to extract a date from text"""
        if not text:
            return None

        # Try common date formats
        date_patterns = [
            r'(\d{4}-\d{2}-\d{2})',  # 2026-09-28
            r'(\d{2}/\d{2}/\d{4})',  # 09/28/2026
            r'(\w+ \d{1,2}, \d{4})',  # September 28, 2026
        ]

        for pattern in date_patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    date_str = match.group(1)
                    for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%B %d, %Y', '%b %d, %Y']:
                        try:
                            return datetime.strptime(date_str, fmt)
                        except:
                            continue
                except:
                    continue

        return None

    def _extract_forecast_previous(self, text):
        """Try to extract forecast and previous values from text"""
        forecast = 'N/A'
        previous = 'N/A'

        # Look for patterns like "forecast: 3.2%" or "previous: 3.4%"
        forecast_match = re.search(r'forecast[:\s]+([+-]?\d+\.?\d*%?)', text, re.IGNORECASE)
        previous_match = re.search(r'previous[:\s]+([+-]?\d+\.?\d*%?)', text, re.IGNORECASE)

        if forecast_match:
            forecast = forecast_match.group(1)
        if previous_match:
            previous = previous_match.group(1)

        return forecast, previous

    def _get_mock_calendar(self, days_ahead):
        """Generate realistic upcoming economic events if all APIs fail"""
        today = datetime.now()

        mock_events = [
            {
                'date': (today + timedelta(days=3)).strftime('%Y-%m-%d'),
                'time': '08:30',
                'event': 'US Non-Farm Payrolls',
                'country': 'United States', 'country_code': 'US', 'flag': '🇺🇸',
                'impact': 'HIGH', 'forecast': '185K', 'previous': '175K',
                'actual': 'Pending', 'currency': 'USD',
                'description': 'US monthly employment report - major market mover'
            },
            {
                'date': (today + timedelta(days=3)).strftime('%Y-%m-%d'),
                'time': '08:30',
                'event': 'US Unemployment Rate',
                'country': 'United States', 'country_code': 'US', 'flag': '🇺🇸',
                'impact': 'HIGH', 'forecast': '4.2%', 'previous': '4.3%',
                'actual': 'Pending', 'currency': 'USD',
                'description': 'US unemployment rate'
            },
            {
                'date': (today + timedelta(days=8)).strftime('%Y-%m-%d'),
                'time': '08:30',
                'event': 'US CPI (Consumer Price Index)',
                'country': 'United States', 'country_code': 'US', 'flag': '🇺🇸',
                'impact': 'HIGH', 'forecast': '3.2% YoY', 'previous': '3.4% YoY',
                'actual': 'Pending', 'currency': 'USD',
                'description': 'Primary US inflation gauge'
            },
            {
                'date': (today + timedelta(days=10)).strftime('%Y-%m-%d'),
                'time': '13:15',
                'event': 'ECB Interest Rate Decision',
                'country': 'European Union', 'country_code': 'EU', 'flag': '🇪🇺',
                'impact': 'HIGH', 'forecast': '3.75%', 'previous': '3.75%',
                'actual': 'Pending', 'currency': 'EUR',
                'description': 'European Central Bank rate decision'
            },
            {
                'date': (today + timedelta(days=11)).strftime('%Y-%m-%d'),
                'time': '09:30',
                'event': 'China CPI',
                'country': 'China', 'country_code': 'CN', 'flag': '🇨🇳',
                'impact': 'MEDIUM', 'forecast': '0.6% YoY', 'previous': '0.5% YoY',
                'actual': 'Pending', 'currency': 'CNY',
                'description': 'Chinese consumer price index'
            },
            {
                'date': (today + timedelta(days=12)).strftime('%Y-%m-%d'),
                'time': '11:00',
                'event': 'BOJ Policy Rate',
                'country': 'Japan', 'country_code': 'JP', 'flag': '🇯🇵',
                'impact': 'HIGH', 'forecast': '0.25%', 'previous': '0.25%',
                'actual': 'Pending', 'currency': 'JPY',
                'description': 'Bank of Japan policy decision'
            },
            {
                'date': (today + timedelta(days=14)).strftime('%Y-%m-%d'),
                'time': '09:30',
                'event': 'Riksbank Interest Rate Decision',
                'country': 'Sweden', 'country_code': 'SE', 'flag': '🇸🇪',
                'impact': 'HIGH', 'forecast': '3.25%', 'previous': '3.25%',
                'actual': 'Pending', 'currency': 'SEK',
                'description': 'Swedish central bank rate decision'
            },
            {
                'date': (today + timedelta(days=14)).strftime('%Y-%m-%d'),
                'time': '10:00',
                'event': 'Danmarks Nationalbank Rate',
                'country': 'Denmark', 'country_code': 'DK', 'flag': '🇩🇰',
                'impact': 'MEDIUM', 'forecast': '3.35%', 'previous': '3.35%',
                'actual': 'Pending', 'currency': 'DKK',
                'description': 'Danish central bank rate (tracks ECB)'
            },
        ]

        end_date = today + timedelta(days=days_ahead)
        return [ev for ev in mock_events
                if datetime.strptime(ev['date'], '%Y-%m-%d') <= end_date]

    def _cache_events(self, events):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        cache_file = os.path.join(self.cache_dir, f'calendar_{timestamp}.json')
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(events, f, indent=2, ensure_ascii=False)

    def format_calendar_summary(self, events):
        if not events:
            return "No major upcoming economic events found."

        summary = "UPCOMING ECONOMIC EVENTS:\n"
        for event in events[:15]:
            summary += f"\n{event['flag']} {event['date']} {event.get('time','')} - {event['event']}"
            summary += f"\n   Impact: {event['impact']} | Forecast: {event['forecast']} | Previous: {event['previous']}"
            if event.get('actual') and event['actual'] != 'Pending':
                summary += f" | Actual: {event['actual']}"
        return summary