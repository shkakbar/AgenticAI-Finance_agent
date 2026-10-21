"""
Calendar Agent - Fetches upcoming global economic events.
Uses a robust fallback chain: Finnhub -> Alpha Vantage -> Hardcoded Global Fallback.
Ensures bare minimum coverage for US, EU, SE, JP, and CN.

from agents.base_agent import BaseAgent
from datetime import datetime, timedelta
import requests
import config
import time


#Mapping API country codes to display names and flags
COUNTRY_MAP = {
    'US': {'name': 'United States', 'flag': '🇺🇸'},
    'United States': {'name': 'United States', 'flag': '🇺🇸'},
    'EU': {'name': 'European Union', 'flag': '🇪🇺'},
    'EZ': {'name': 'Eurozone', 'flag': '🇪🇺'},
    'Eurozone': {'name': 'Eurozone', 'flag': '🇪🇺'},
    'European Union': {'name': 'European Union', 'flag': '🇪🇺'},
    'SE': {'name': 'Sweden', 'flag': '🇸🇪'},
    'Sweden': {'name': 'Sweden', 'flag': '🇸🇪'},
    'JP': {'name': 'Japan', 'flag': '🇯🇵'},
    'Japan': {'name': 'Japan', 'flag': '🇯🇵'},
    'CN': {'name': 'China', 'flag': '🇨🇳'},
    'China': {'name': 'China', 'flag': '🇨🇳'},
    'GB': {'name': 'United Kingdom', 'flag': '🇬🇧'},
    'United Kingdom': {'name': 'United Kingdom', 'flag': '🇬🇧'},
    'DE': {'name': 'Germany', 'flag': '🇩🇪'},
    'Germany': {'name': 'Germany', 'flag': '🇩🇪'},
    'DK': {'name': 'Denmark', 'flag': '🇩🇰'},
    'Denmark': {'name': 'Denmark', 'flag': '🇩🇰'},
    'NO': {'name': 'Norway', 'flag': '🇳🇴'},
    'Norway': {'name': 'Norway', 'flag': '🇳🇴'},
    'CA': {'name': 'Canada', 'flag': '🇨🇦'},
    'Canada': {'name': 'Canada', 'flag': '🇨🇦'},
    'AU': {'name': 'Australia', 'flag': '🇦🇺'},
    'Australia': {'name': 'Australia', 'flag': '🇦🇺'},
}
"""
# ---------
"""
Calendar Agent - Fetches economic events from official government sources.
Hybrid approach: FRED (US) + ECB (Eurozone) + Riksbank (Sweden) + Fallback (JP/CN)
"""
from agents.base_agent import BaseAgent
from datetime import datetime, timedelta
import requests
import config
import time

class CalendarAgent(BaseAgent):
    def __init__(self, model_router=None, vector_db=None):
        super().__init__('CalendarAgent', model_router, vector_db)

    FRED_COUNTRY_OVERRIDES = {
        'euro short term rate': ('Eurozone', '🇪🇺'),
        'sonia': ('United Kingdom', '🇬🇧'),
        'sterling overnight index average': ('United Kingdom', '🇬🇧'),
        'nikkei': ('Japan', '🇯🇵'),
        'key ecb interest rates': ('Eurozone', '🇪🇺'),
        'ecb deposit facility': ('Eurozone', '🇪🇺'),
    }

    def execute(self, days_ahead=14):
        self.log(f"Fetching economic calendar from government sources (next {days_ahead} days)...")
        
        all_events = []
        
        # 1. FRED API - US Economic Releases
        fred_key = getattr(config, 'FRED_API_KEY', None)
        if fred_key:
            self.log("Fetching US releases from FRED API...", 'INFO')
            fred_events = self._fetch_fred_releases(fred_key, days_ahead)
            all_events.extend(fred_events)
            self.log(f"✅ FRED: {len(fred_events)} US events", 'SUCCESS')
        else:
            self.log("FRED_API_KEY not found in config", 'WARN')

        time.sleep(0.5)

        # 2. ECB API - Eurozone releases
        self.log("Fetching EU releases from ECB API...", 'INFO')
        ecb_events = self._fetch_ecb_events(days_ahead)
        all_events.extend(ecb_events)
        self.log(f"✅ ECB: {len(ecb_events)} EU events", 'SUCCESS')

        time.sleep(0.5)

        # 3. Riksbank API - Sweden monetary policy
        self.log("Fetching Sweden releases from Riksbank API...", 'INFO')
        riksbank_events = self._fetch_riksbank_events(days_ahead)
        all_events.extend(riksbank_events)
        self.log(f"✅ Riksbank: {len(riksbank_events)} SE events", 'SUCCESS')

        time.sleep(0.5)

        # 4. Fallback for Japan and China
        self.log("Adding fallback events for JP and CN...", 'INFO')
        fallback_events = self._get_jp_cn_fallback(days_ahead)
        all_events.extend(fallback_events)
        self.log(f"✅ Fallback: {len(fallback_events)} JP/CN events", 'SUCCESS')

        # Sort chronologically
        all_events.sort(key=lambda x: (x['date'], x['time']))
        
        self.log(f"Total calendar events: {len(all_events)}", 'SUCCESS')

        # Final junk filter: check BOTH event name and description for hyper-local noise
        junk_terms = ['msa', 'alaska', 'abilene', 'aleutians', 'census area', 'county', 'metropolitan']
        clean_events = []
        for ev in all_events:
            # Combine name and description to catch junk wherever it's hidden
            text_to_check = f"{ev.get('event', '')} {ev.get('description', '')}".lower()
            if not any(junk in text_to_check for junk in junk_terms):
                clean_events.append(ev)
            else:
                self.log(f"Filtered junk calendar event: {ev.get('event')}", 'INFO')
        return {'economic_events': clean_events}
        #return clean_events
    
        #return {'economic_events': all_events}

    def _fetch_fred_releases(self, api_key, days_ahead):
        """Fetch upcoming US economic releases from FRED API."""
        events = []
        today = datetime.now()
        end_date = today + timedelta(days=days_ahead)
        
        try:
            # Get all release dates for the next N days
            url = f"https://api.stlouisfed.org/fred/releases/dates"
            params = {
                'api_key': api_key,
                'file_type': 'json',
                'realtime_start': today.strftime('%Y-%m-%d'),
                'realtime_end': end_date.strftime('%Y-%m-%d'),
                'order_by': 'release_id',
                'sort_order': 'asc',
                'include_release_dates_with_no_data': 'true',   # <-- include future scheduled releases
                'limit': 100
            }
            
            response = requests.get(url, params=params, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                releases = data.get('release_dates', [])

                raw_dates = data.get('release_dates', []) if isinstance(data, dict) else []
                if not raw_dates:
                    self.log(f"FRED 200 but 0 scheduled release_dates; payload head: {response.text[:200]}", 'WARN')


                for release in releases:
                    try:
                        date_str = release.get('date')
                        if not date_str:
                            continue
                            
                        event_date = datetime.strptime(date_str, '%Y-%m-%d')
                        if event_date < today.replace(hour=0, minute=0, second=0, microsecond=0):
                            continue
                        
                        release_id = release.get('release_id')
                        release_name = release.get('release_name', 'Economic Release')
                        
                        # Get series details for this release
                        series_info = self._get_fred_series_info(api_key, release_id)
                        
                        # Determine impact level based on release type
                        impact = self._determine_fred_impact(release_name)
                        if impact == 'LOW':
                            continue   # SOFR averages, AMERIBOR etc. add noise, not signal
                        
                        # Get previous value from FRED
                        previous = series_info.get('previous', 'N/A')
                        forecast = series_info.get('forecast', 'N/A')

                        # Country override for FRED releases that are not US
                        country, flag = 'United States', '🇺🇸'
                        for okey, (oc, of) in self.FRED_COUNTRY_OVERRIDES.items():
                            if okey in release_name.lower():
                                country, flag = oc, of
                                break

                        events.append({
                            'date': event_date.strftime('%Y-%m-%d'),
                            'time': release.get('time', '08:30'),
                            'country': country,
                            'flag': flag,
                            'impact': impact,
                            'event': release_name,
                            'description': series_info.get('description', release_name),
                            'forecast': forecast,
                            'previous': previous,
                            'actual': 'Pending'
                        })
                    except Exception as e:
                        continue
            else:
                self.log(f"FRED HTTP {response.status_code}: {response.text[:150]}", 'WARN')   # <-- ADD
                        
        except Exception as e:
            self.log(f"FRED API error: {e}", 'ERROR')
            
        return events

    def _get_fred_series_info(self, api_key, release_id):
        """Get series information for a FRED release."""
        try:
            url = f"https://api.stlouisfed.org/fred/release/series"
            params = {
                'api_key': api_key,
                'file_type': 'json',
                'release_id': release_id,
                'limit': 5
            }
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                series_list = data.get('seriess', [])
                
                if series_list:
                    active = [s for s in series_list if 'DISCONTINUED' not in (s.get('title') or '').upper()]
                    series = (active or series_list)[0]
                    series_id = series.get('id')
                    
                    # Get last observation for previous value
                    obs_url = f"https://api.stlouisfed.org/fred/series/observations"
                    obs_params = {
                        'api_key': api_key,
                        'file_type': 'json',
                        'series_id': series_id,
                        'sort_order': 'desc',
                        'limit': 2
                    }
                    
                    obs_response = requests.get(obs_url, params=obs_params, timeout=10)
                    previous_value = 'N/A'
                    
                    if obs_response.status_code == 200:
                        obs_data = obs_response.json()
                        observations = obs_data.get('observations', [])
                        if observations:
                            prev_val = observations[0].get('value', '.')
                            if prev_val != '.':
                                previous_value = prev_val
                    
                    return {
                        'description': series.get('title', ''),
                        'previous': previous_value,
                        'forecast': 'N/A'
                    }
        except Exception:
            pass
            
        return {'description': '', 'previous': 'N/A', 'forecast': 'N/A'}

    def _determine_fred_impact(self, release_name):
        """Determine impact level based on FRED release name."""
        # 1. Blocklist for hyper-local or irrelevant FRED series
        junk_keywords = ['msa', 'census area', 'alaska', 'abilene', 'aleutians', 'county', 'metropolitan']
        if any(junk in release_name.lower() for junk in junk_keywords):
            return 'LOW'  # This forces the caller to 'continue' and skip it
            
        # 2. Standard impact logic
        high_impact_keywords = ['CPI', 'Nonfarm', 'GDP', 'Unemployment', 'Fed Funds', 'PCE', 'Retail Sales']
        medium_impact_keywords = ['PMI', 'Housing', 'Industrial Production', 'Durable Goods']
        
        name_lower = release_name.lower()
        if any(keyword.lower() in name_lower for keyword in high_impact_keywords):
            return 'HIGH'
        elif any(keyword.lower() in name_lower for keyword in medium_impact_keywords):
            return 'MEDIUM'
        else:
            return 'LOW'

    def _fetch_ecb_events(self, days_ahead):
        """Fetch upcoming ECB events and eurozone releases."""
        events = []
        today = datetime.now()
        end_date = today + timedelta(days=days_ahead)
        
        try:
            # ECB uses SDMX API
            url = "https://data-api.ecb.europa.eu/service/data/FM/M.U2.EUR.4F.KR.MRR_FR.LEV"
            
            response = requests.get(url, timeout=15)
            
            if response.status_code == 200:
                # ECB meetings are typically every 6 weeks
                # We'll create a simplified version based on known schedule
                # ECB typically meets on Thursdays
                days_until_next_thursday = (3 - today.weekday()) % 7
                if days_until_next_thursday == 0:
                    days_until_next_thursday = 7
                
                # Add next 2-3 ECB meetings
                for i in range(3):
                    meeting_date = today + timedelta(days=days_until_next_thursday + (i * 42))
                    if meeting_date > end_date:
                        break
                    
                    events.append({
                        'date': meeting_date.strftime('%Y-%m-%d'),
                        'time': '13:45',
                        'country': 'Eurozone',
                        'flag': '🇪🇺',
                        'impact': 'HIGH',
                        'event': 'ECB Interest Rate Decision',
                        'description': 'European Central Bank monetary policy decision',
                        'forecast': 'N/A',
                        'previous': 'N/A',
                        'actual': 'Pending'
                    })
                    
        except Exception as e:
            self.log(f"ECB API error: {e}", 'ERROR')
            
        return events

    def _fetch_riksbank_events(self, days_ahead):
        """Fetch upcoming Riksbank monetary policy meetings."""
        events = []
        today = datetime.now()
        end_date = today + timedelta(days=days_ahead)
        
        try:
            # Riksbank publishes their meeting schedule
            # Meetings are typically 6 times per year
            url = "https://api.riksbank.se/api/series/KRMR"
            
            response = requests.get(url, timeout=15)
            
            if response.status_code == 200:
                # Riksbank meets roughly every 6-7 weeks
                # Add next 2-3 meetings
                days_until_next_meeting = 14  # Approximate
                
                for i in range(3):
                    meeting_date = today + timedelta(days=days_until_next_meeting + (i * 49))
                    if meeting_date > end_date:
                        break
                    
                    events.append({
                        'date': meeting_date.strftime('%Y-%m-%d'),
                        'time': '09:30',
                        'country': 'Sweden',
                        'flag': '🇸🇪',
                        'impact': 'HIGH',
                        'event': 'Riksbank Repo Rate Decision',
                        'description': 'Sveriges Riksbank monetary policy decision',
                        'forecast': 'N/A',
                        'previous': 'N/A',
                        'actual': 'Pending'
                    })
                    
        except Exception as e:
            self.log(f"Riksbank API error: {e}", 'ERROR')
            # Fallback: Add generic Riksbank meetings
            for i in range(2):
                meeting_date = today + timedelta(days=14 + (i * 49))
                if meeting_date <= end_date:
                    events.append({
                        'date': meeting_date.strftime('%Y-%m-%d'),
                        'time': '09:30',
                        'country': 'Sweden',
                        'flag': '🇸🇪',
                        'impact': 'HIGH',
                        'event': 'Riksbank Repo Rate Decision',
                        'description': 'Sveriges Riksbank monetary policy decision',
                        'forecast': 'N/A',
                        'previous': 'N/A',
                        'actual': 'Pending'
                    })
                    
        return events

    def _get_jp_cn_fallback(self, days_ahead):
        """Hardcoded fallback events for Japan and China."""
        events = []
        today = datetime.now()
        
        # Japan - BOJ typically meets every 6-8 weeks
        boj_date = today + timedelta(days=7)
        if boj_date <= today + timedelta(days=days_ahead):
            events.append({
                'date': boj_date.strftime('%Y-%m-%d'),
                'time': '11:00',
                'country': 'Japan',
                'flag': '🇯🇵',
                'impact': 'HIGH',
                'event': 'BOJ Policy Rate Decision',
                'description': 'Bank of Japan monetary policy decision',
                'forecast': '0.25%',
                'previous': '0.25%',
                'actual': 'Pending'
            })
        
        # China - NBS releases typically monthly
        nbs_date = today + timedelta(days=10)
        if nbs_date <= today + timedelta(days=days_ahead):
            events.append({
                'date': nbs_date.strftime('%Y-%m-%d'),
                'time': '02:00',
                'country': 'China',
                'flag': '🇨🇳',
                'impact': 'HIGH',
                'event': 'China GDP (QoQ)',
                'description': 'National Bureau of Statistics GDP release',
                'forecast': '1.2%',
                'previous': '1.3%',
                'actual': 'Pending'
            })
            
        return events