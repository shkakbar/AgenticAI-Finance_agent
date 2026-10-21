"""
Sector Agent - Fetches real sector ETF prices from SECTOR_DEFINITIONS.
"""
from agents.base_agent import BaseAgent
import yfinance as yf
import config, time

class SectorAgent(BaseAgent):
    def __init__(self, model_router=None, vector_db=None):
        super().__init__('SectorAgent', model_router, vector_db)

    def execute(self, all_news):
        if not self.validate_input(all_news):
            return None

        self.log("Analyzing sector performance...")
        sector_definitions = getattr(config, 'SECTOR_DEFINITIONS', {})

        us_sector_data, us_sector_sentiment = self._fetch_sectors(sector_definitions.get('US', {}), all_news)
        sweden_sector_data, sweden_sector_sentiment = self._fetch_sectors(sector_definitions.get('Sweden', {}), all_news)

        self.log(f"Sectors complete. US: {len(us_sector_data)}, Sweden: {len(sweden_sector_data)}", 'SUCCESS')

        return {
            'us_sector_data': us_sector_data,
            'us_sector_sentiment': us_sector_sentiment,
            'sweden_sector_data': sweden_sector_data,
            'sweden_sector_sentiment': sweden_sector_sentiment
        }

    def _fetch_sectors(self, sectors, all_news):
        data, sentiments = {}, {}
        for name, info in sectors.items():
            # GAP-02: equal-weighted average of representative constituents
            # Accept 'tickers' (list) OR 'ticker' (string or list); flatten any accidental nesting
            raw = info.get('tickers') if info.get('tickers') is not None else info.get('ticker')
            ticker_list = []
            if isinstance(raw, str):
                ticker_list = [raw]
            elif isinstance(raw, (list, tuple)):
                for item in raw:
                    if isinstance(item, (list, tuple)):
                        ticker_list.extend([x for x in item if isinstance(x, str) and x.strip()])
                    elif isinstance(item, str) and item.strip():
                        ticker_list.append(item)
            ticker_symbol = ticker_list[0] if ticker_list else ''  # back-compat for downstream code

            daily_change, weekly_change = 0.0, 0.0

            if ticker_list:
                daily_vals, weekly_vals = [], []
                try:
                    # Robust batch download prevents yfinance session exhaustion late in the pipeline
                    syms = [s for s in ticker_list if isinstance(s, str) and s.strip()]
                    bad = [s for s in ticker_list if not isinstance(s, str)]
                    if bad:
                        self.log(f"Sector '{name}': NON-STRING tickers present -> {bad}", 'WARN')
                    # Space-joined string bypasses yfinance's buggy list-handling path
                    batch_hist = yf.download(" ".join(syms), period="5d",
                        group_by='ticker', progress=False, threads=False)
                    
                    for symbol in ticker_list:
                        try:
                            # Handle single vs multi-ticker DataFrame structures safely
                            # Robust to both flat and MultiIndex columns (varies by yfinance version)
                            try:
                                hist = batch_hist[symbol]['Close'].dropna()      # MultiIndex layout
                            except (KeyError, TypeError):
                                hist = batch_hist['Close'].dropna()              # flat single-ticker layout
                                
                            if len(hist) >= 2:
                                current = float(hist.iloc[-1])
                                prev = float(hist.iloc[-2])
                                if prev > 0:
                                    daily_vals.append((current - prev) / prev * 100)
                                if len(hist) >= 5 and float(hist.iloc[0]) > 0:
                                    weekly_vals.append((current - float(hist.iloc[0])) / float(hist.iloc[0]) * 100)
                        except Exception:
                            continue
                except Exception as e:
                    self.log(f"Sector batch download failed for {name}: {e}", 'WARN')
                    
                if daily_vals:
                    daily_change = round(sum(daily_vals) / len(daily_vals), 2)
                if weekly_vals:
                    weekly_change = round(sum(weekly_vals) / len(weekly_vals), 2)

            data[name] = {
                'ticker': ticker_symbol,
                'icon': info.get('icon', '📊'),
                'daily_change': daily_change,
                'weekly_change': weekly_change,
                'key_companies': info.get('key_companies', [])
            }

            keywords = [name.lower()] + [c.lower() for c in info.get('key_companies', [])]
            relevant = [n for n in all_news if any(kw in n.get('title', '').lower() for kw in keywords)]
            score = self._calculate_score(relevant)
            drivers = [n.get('title', '')[:100] for n in relevant[:3]]

            sentiments[name] = {'score': score, 'label': self._score_to_label(score), 'drivers': drivers}

        return data, sentiments

    def _calculate_score(self, news_list):
        if not news_list:
            return 0
        pos_words = ['rally', 'surge', 'gain', 'growth', 'rise', 'bullish', 'record', 'strong', 'beat', 'upgrade']
        neg_words = ['crash', 'fall', 'drop', 'decline', 'bearish', 'recession', 'weak', 'miss', 'downgrade', 'crisis']
        pos = sum(1 for n in news_list for w in pos_words if w in n.get('title', '').lower())
        neg = sum(1 for n in news_list for w in neg_words if w in n.get('title', '').lower())
        total = pos + neg
        return max(-100, min(100, int(((pos - neg) / total) * 100))) if total > 0 else 0

    def _score_to_label(self, score):
        if score >= 40: return 'Very Bullish'
        if score >= 15: return 'Bullish'
        if score >= -15: return 'Neutral'
        if score >= -40: return 'Bearish'
        return 'Very Bearish'
    