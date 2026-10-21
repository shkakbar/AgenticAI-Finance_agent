"""
Fundamentals Agent - Valuation fundamentals for the configured WATCHLIST.
Source: yfinance .info with 24h file cache and per-ticker resilience.
"""
import json
import os
import time
from datetime import datetime

import config
from agents.base_agent import BaseAgent


class FundamentalsAgent(BaseAgent):
    CACHE_DIR = 'data/cache'
    CACHE_TTL_HOURS = 24

    def __init__(self, model_router=None, vector_db=None):
        super().__init__('FundamentalsAgent', model_router, vector_db)

    # ── Cache helpers ─────────────────────────────────────────────
    def _cache_path(self):
        return os.path.join(self.CACHE_DIR, 'fundamentals_cache.json')

    def _load_cache(self):
        try:
            path = self._cache_path()
            if not os.path.exists(path):
                return {}
            with open(path, 'r') as f:
                cache = json.load(f)
            ts = cache.get('timestamp')
            if not ts:
                return {}
            age_h = (datetime.now() - datetime.fromisoformat(ts)).total_seconds() / 3600
            if age_h > self.CACHE_TTL_HOURS:
                return {}
            return cache.get('data', {})
        except Exception:
            return {}

    def _save_cache(self, data):
        try:
            os.makedirs(self.CACHE_DIR, exist_ok=True)
            with open(self._cache_path(), 'w') as f:
                json.dump({'timestamp': datetime.now().isoformat(), 'data': data}, f)
        except Exception as e:
            self.log(f"Cache save failed: {e}", 'WARN')

    # ── Field extraction ──────────────────────────────────────────
    @staticmethod
    def _r(v, nd=2):
        try:
            return round(float(v), nd) if v is not None else None
        except Exception:
            return None

    @staticmethod
    def _div_yield(info, price):
        """Unambiguous yield: dividendRate / price. Fallback handles fraction-vs-percent API drift."""
        rate = info.get('dividendRate')
        if rate and price:
            return round((float(rate) / float(price)) * 100, 2)
        y = info.get('dividendYield')
        if y is None:
            return None
        y = float(y)
        return round(y * 100, 2) if 0 < y < 1 else round(y, 2)

    def _extract(self, symbol, meta):
        import yfinance as yf
        info = {}
        try:
            info = yf.Ticker(symbol).info or {}
        except Exception:
            info = {}
        price = info.get('currentPrice') or info.get('regularMarketPrice')
        if not price:
            return None
        high = info.get('fiftyTwoWeekHigh')
        low = info.get('fiftyTwoWeekLow')
        pos = round(((price - low) / (high - low)) * 100, 1) if (high and low and high > low) else None
        return {
            'symbol': symbol,
            'name': meta.get('name', info.get('shortName', symbol)),
            'region': meta.get('region', ''),
            'currency': info.get('currency', ''),
            'sector': info.get('sector', ''),
            'price': round(float(price), 2),
            'market_cap': info.get('marketCap'),
            'trailing_pe': self._r(info.get('trailingPE')),
            'forward_pe': self._r(info.get('forwardPE')),
            'eps': self._r(info.get('trailingEps')),
            'div_yield_pct': self._div_yield(info, price),
            'beta': self._r(info.get('beta')),
            'week52_high': high,
            'week52_low': low,
            'week52_position_pct': pos,
        }

    # ── Main ──────────────────────────────────────────────────────
    def execute(self):
        watchlist = getattr(config, 'WATCHLIST', [])
        if not watchlist:
            self.log("No WATCHLIST configured.", 'WARN')
            return {'watchlist_fundamentals': []}

        cache = self._load_cache()
        results, fetched = [], 0
        for meta in watchlist:
            sym = meta.get('symbol')
            if sym in cache:
                results.append(cache[sym])
                continue
            try:
                rec = self._extract(sym, meta)
                if rec:
                    cache[sym] = rec
                    results.append(rec)
                    fetched += 1
                else:
                    self.log(f"No price data for {sym}; skipped.", 'WARN')
            except Exception as e:
                self.log(f"Fundamentals fetch failed for {sym}: {str(e)[:80]}", 'WARN')
            time.sleep(0.3)  # rate-limit courtesy

        if fetched:
            self._save_cache(cache)
        self.log(f"Fundamentals complete: {len(results)}/{len(watchlist)} tickers ({fetched} fresh).", 'SUCCESS')
        return {'watchlist_fundamentals': results}