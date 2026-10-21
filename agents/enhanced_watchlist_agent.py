"""
Enhanced Watchlist Agent - WATCHLIST 2.0
Multi-period returns, volume, fundamentals, momentum sentiment, and Buffett valuation.
Buffett methodology: 5-pillar Quality Score (0-100) + Graham intrinsic value (margin of safety).
Educational analytics only — not investment advice.
"""
import os
import json
import time
from datetime import datetime

import numpy as np
import pandas as pd
import yfinance as yf

import config


class EnhancedWatchlistAgent:
    CACHE_DIR = 'data/cache'
    FUND_CACHE_TTL_HOURS = 24
    GRAHAM_BASE = 8.5
    BOND_YIELD = 5.5          # AAA corporate proxy for Buffett's 4.4/Y adjustment
    QUALITY_THRESHOLD = 65    # min Quality Score for "Buffett's Picks"
    MOS_THRESHOLD = 15        # min margin of safety (%) for "Buffett's Picks"
    MOS_SANITY_CAP = 250      # GAP-15: MoS beyond this = data suspect (ADR/FX/unit mismatch)

    def __init__(self, model_router=None, vector_db=None):
        self.name = 'EnhancedWatchlistAgent'

    def log(self, msg, level='INFO'):
        prefix = {'INFO': 'ℹ️', 'SUCCESS': '✅', 'WARN': '⚠️', 'ERROR': '❌'}.get(level, 'ℹ️')
        print(f"  {prefix} [{self.name}] {msg}")

    # ── Fundamentals cache ─────────────────────────────────────────
    def _fund_cache_path(self):
        return os.path.join(self.CACHE_DIR, 'enhanced_watchlist_fund.json')

    def _load_fund_cache(self):
        try:
            p = self._fund_cache_path()
            if not os.path.exists(p):
                return {}
            with open(p) as f:
                cache = json.load(f)
            ts = cache.get('timestamp')
            if not ts:
                return {}
            age_h = (datetime.now() - datetime.fromisoformat(ts)).total_seconds() / 3600
            if age_h > self.FUND_CACHE_TTL_HOURS:
                return {}
            return cache.get('data', {})
        except Exception:
            return {}

    def _save_fund_cache(self, data):
        try:
            os.makedirs(self.CACHE_DIR, exist_ok=True)
            with open(self._fund_cache_path(), 'w') as f:
                json.dump({'timestamp': datetime.now().isoformat(), 'data': data}, f)
        except Exception as e:
            self.log(f"Fund cache save failed: {e}", 'WARN')

    # ── Price data (batched) ───────────────────────────────────────
    def _batch_download(self, symbols, period, interval):
        try:
            return yf.download(symbols, period=period, interval=interval,
                               group_by='ticker', auto_adjust=True,
                               threads=True, progress=False)
        except Exception as e:
            self.log(f"Price download failed: {str(e)[:80]}", 'WARN')
            return pd.DataFrame()

    def _series(self, data, symbol, field):
        try:
            if isinstance(data.columns, pd.MultiIndex):
                if symbol in data.columns.get_level_values(0):
                    return data[symbol][field].dropna()
            else:
                if field in data.columns:
                    return data[field].dropna()
        except Exception:
            pass
        return pd.Series(dtype=float)

    @staticmethod
    def _pct_change_calendar(close, calendar_days):
        """Return % change vs the price closest to `calendar_days` ago."""
        if close is None or len(close) < 2:
            return None
        target = close.index[-1] - pd.Timedelta(days=calendar_days)
        past = close[close.index <= target]
        if past.empty:
            return None
        past_price = past.iloc[-1]
        cur = close.iloc[-1]
        if past_price == 0:
            return None
        return round((cur / past_price - 1) * 100, 2)

    # ── Classification & sentiment ─────────────────────────────────
    @staticmethod
    def _cap_class(mcap_usd):
        if not mcap_usd:
            return 'N/A'
        if mcap_usd >= 10e9:
            return 'Large'
        if mcap_usd >= 2e9:
            return 'Mid'
        return 'Small'

    @staticmethod
    def _avg(*vals):
        vals = [v for v in vals if v is not None]
        return sum(vals) / len(vals) if vals else None

    @staticmethod
    def _momentum_label(score, threshold):
        if score is None:
            return 'Neutral'
        if score >= threshold:
            return 'Bullish'
        if score <= -threshold:
            return 'Bearish'
        return 'Neutral'

    # ── Buffett Quality Score (0-100, five 20-pt pillars) ──────────
    def _buffett_quality(self, info):
        score = 0
        # 1) ROE
        roe = info.get('returnOnEquity')
        if roe is not None:
            r = roe * 100
            if r >= 20: score += 20
            elif r >= 15: score += 15
            elif r >= 10: score += 10
            elif r >= 5: score += 5
        # 2) Net margin
        margin = info.get('profitMargins')
        if margin is not None:
            m = margin * 100
            if m >= 20: score += 20
            elif m >= 15: score += 15
            elif m >= 10: score += 10
            elif m >= 5: score += 5
        # 3) Balance sheet (debt) — neutral for financials
        sector = (info.get('sector') or '') + ' ' + (info.get('industry') or '')
        is_fin = any(k in sector for k in ('Financial', 'Bank', 'Insurance'))
        if is_fin:
            score += 10
        else:
            de = info.get('debtToEquity')
            if de is not None:
                d = de / 100.0  # yfinance returns percentage
                if d <= 0.3: score += 20
                elif d <= 0.5: score += 15
                elif d <= 1.0: score += 10
                elif d <= 2.0: score += 5
        # 4) Earnings quality & growth
        eps = info.get('trailingEps')
        eg = info.get('earningsGrowth')
        if eps is not None and eps > 0:
            score += 10
            if eg is not None and eg > 0:
                score += 10
        # 5) Valuation discipline
        pe = info.get('trailingPE')
        pb = info.get('priceToBook')
        if pe is not None and 0 < pe <= 25: score += 10
        if pb is not None and 0 < pb <= 3: score += 10
        return min(score, 100)

    # ── Buffett Valuation (Graham intrinsic value) ─────────────────
    def _buffett_valuation(self, info, price, ticker_obj=None):
        """Owner-Earnings DCF (primary) → Graham Number (financials) → Graham formula (fallback)."""
        if not price:
            return None, None, 'N/A', 'none'
        eps = info.get('trailingEps')

        # GAP-11: Buffett does not value loss-making companies off trailing losses.
        if not eps or eps <= 0:
            return None, None, 'N/A', 'negative_eps'

        # Financials: D&A/CapEx logic doesn't apply → Graham Number (book-based)

        # Financials: D&A/CapEx logic doesn't apply → Graham Number (book-based)
        if 'Financial' in (info.get('sector') or ''):
            pb = info.get('priceToBook')
            if eps and eps > 0 and pb and pb > 0:
                bvps = price / pb
                gn = (22.5 * eps * bvps) ** 0.5
                mos = round((gn - price) / price * 100, 1)
                return round(gn, 2), mos, self._verdict(mos), 'graham_number'
            return None, None, 'N/A', 'none'

        # Primary: Owner-Earnings DCF
        iv, mos = self._owner_earnings_intrinsic(info.get('_oe_series') or [], info, price)
        if iv is not None:
            return iv, mos, self._verdict(mos), 'owner_earnings'

        # Fallback: Graham formula (growth capped at 12%)
        if not eps or eps <= 0:
            return None, None, 'N/A', 'none'
        g = info.get('earningsGrowth') or info.get('revenueGrowth') or 0.05
        g_pct = max(0.0, min(g * 100, 12.0))
        intrinsic = eps * (self.GRAHAM_BASE + 2 * g_pct) * (4.4 / self.BOND_YIELD)
        mos = round((intrinsic - price) / price * 100, 1)
        return round(intrinsic, 2), mos, self._verdict(mos), 'graham'

    def _ev_ebit(self, ticker_obj, info):
        ev = info.get('enterpriseValue')
        if not ev:
            return None
        ebit = None
        try:
            fin = ticker_obj.financials
            if fin is not None and 'EBIT' in fin.index:
                ebit = fin.loc['EBIT'].iloc[0]
        except Exception:
            ebit = None
        if ebit and ebit > 0:
            return round(ev / ebit, 1)
        ebitda = info.get('ebitda')
        if ebitda and ebitda > 0:
            return round(ev / ebitda, 1)  # EV/EBITDA fallback
        return None

    #---
    # ── Owner Earnings (Buffett's method) ──────────────────────────
    def _owner_earnings_series(self, ticker_obj):
        """Annual Owner Earnings = Net Income + D&A − CapEx, per available year."""
        try:
            fin = ticker_obj.financials
            cf = ticker_obj.cashflow
            if fin is None or cf is None or 'Net Income' not in fin.index:
                return []
            ni_row = fin.loc['Net Income'].dropna()
            # GAP-11: if the LATEST fiscal year is a loss, averaging in older
            # profitable years produces value-trap mirages (the Viaplay case).
            if len(ni_row) == 0 or ni_row.iloc[0] <= 0:
                return []
            
            da_row = cf.loc['Depreciation And Amortization'].dropna() if 'Depreciation And Amortization' in cf.index else None
            cx_row = cf.loc['Capital Expenditure'].dropna() if 'Capital Expenditure' in cf.index else None
            out = []
            for yr in ni_row.index:
                ni = ni_row.get(yr)
                if ni is None or ni <= 0:
                    continue
                da = float(da_row.get(yr, 0) or 0) if da_row is not None else 0.0
                cx = abs(float(cx_row.get(yr, 0) or 0)) if cx_row is not None else 0.0
                out.append(float(ni) + da - cx)
            return out
        except Exception:
            return []

    def _owner_earnings_intrinsic(self, oe_list, info, price):
        """Two-stage DCF of averaged owner earnings. Returns (intrinsic, mos%) or (None, None)."""
        shares = info.get('sharesOutstanding')
        if not oe_list or not shares or shares <= 0 or not price:
            return None, None
        oe = sum(oe_list) / len(oe_list)          # multi-year average smooths cyclicals
        if oe <= 0:
            return None, None
        g = min(max(info.get('earningsGrowth') or 0.04, 0.0), 0.08)   # conservative cap
        terminal_g, discount = 0.03, 0.10                              # Buffett-style hurdle
        pv, oe_t = 0.0, oe
        for yr in range(1, 11):
            oe_t *= (1 + g)
            pv += oe_t / ((1 + discount) ** yr)
        terminal = oe_t * (1 + terminal_g) / (discount - terminal_g)
        pv += terminal / ((1 + discount) ** 10)
        iv = pv / shares
        return round(iv, 2), round((iv - price) / price * 100, 1)

    @staticmethod
    def _verdict(mos):
        if mos is None: return 'N/A'
        if mos > EnhancedWatchlistAgent.MOS_SANITY_CAP: return 'Verify Data'
        if mos >= 25: return 'Undervalued'
        if mos >= 0: return 'Fair'
        return 'Overvalued'
    #---
    # ── Main ───────────────────────────────────────────────────────
    def execute(self):
        universe = getattr(config, 'ENHANCED_WATCHLIST', [])
        if not universe:
            self.log("No ENHANCED_WATCHLIST configured.", 'WARN')
            return {'by_country': {}, 'buffett_picks': [], 'meta': {'total': 0}}

        symbols = [w['symbol'] for w in universe]
        self.log(f"Analyzing {len(symbols)} stocks across countries...", 'INFO')

        # Batch price downloads
        daily = self._batch_download(symbols, period='2y', interval='1d')
        weekly = self._batch_download(symbols, period='10y', interval='1wk')

        fund_cache = self._load_fund_cache()
        rows = []
        fresh = 0
        cache_dirty = False

        for w in universe:
            sym, name, country, ccy = w['symbol'], w['name'], w['country'], w['currency']
            # Grouping rule: US or Sweden only — Nordic neighbors fold into Sweden group
            if country in ('Norway', 'Denmark', 'Finland'):
                country = 'Sweden'
            try:
                d_close = self._series(daily, sym, 'Close')
                d_vol = self._series(daily, sym, 'Volume')
                w_close = self._series(weekly, sym, 'Close')

                price = float(d_close.iloc[-1]) if len(d_close) else None
                if price is None:
                    self.log(f"{sym}: no price data; skipped.", 'WARN')
                    continue

                # Period changes (calendar-day lookback)
                chg = {d: self._pct_change_calendar(d_close, d) for d in (1, 7, 30, 90, 180)}
                ret_1y = self._pct_change_calendar(d_close, 365)
                ret_3y = self._pct_change_calendar(w_close, 365 * 3)
                ret_5y = self._pct_change_calendar(w_close, 365 * 5)
                ret_10y = self._pct_change_calendar(w_close, 3600)  # just under 10y to avoid boundary miss

                # Volume: avg over window vs latest
                avg_vol = int(d_vol.mean()) if len(d_vol) else None
                cur_vol = int(d_vol.iloc[-1]) if len(d_vol) else None
                vol_ratio = round(cur_vol / avg_vol, 2) if (avg_vol and cur_vol) else None

                # Fundamentals (cached)
                if sym in fund_cache:
                    info = fund_cache[sym]
                else:
                    tk = yf.Ticker(sym)
                    try:
                        info = tk.info or {}
                    except Exception:
                        info = {}
                    fund_cache[sym] = info
                    fresh += 1
                    time.sleep(0.2)

                mcap = info.get('marketCap')
                pe = info.get('trailingPE')
                pb = info.get('priceToBook')
                eps = info.get('trailingEps')
                
                div_rate = info.get('dividendRate')
                if div_rate and price:
                    div_pct = round((float(div_rate) / price) * 100, 2)
                else:
                    div = info.get('dividendYield')
                    div_pct = round(float(div), 2) if isinstance(div, (int, float)) and div > 0 else None

                tk = yf.Ticker(sym)
                ev_ebit = self._ev_ebit(tk, info)

                # Inject Owner Earnings series for the DCF valuation
                if '_oe_series' not in info:
                    info['_oe_series'] = self._owner_earnings_series(tk)
                    cache_dirty = True

                quality = self._buffett_quality(info)
                # Unpack all 4 values returned by the valuation router
                intrinsic, mos, verdict, method = self._buffett_valuation(info, price, tk)

                # Momentum sentiment by horizon
                short = self._momentum_label(self._avg(chg[30], chg[90]), 8)
                mid = self._momentum_label(self._avg(chg[90], chg[180]), 10)
                long_ = self._momentum_label(self._avg(ret_1y, ret_3y), 15)

                # ── OPTION B: FX conversion for uniform SEK display ──
                # All internal math (returns, Buffett) already done in native currency above.
                # Convert only the display values here.
                display_price = round(price, 2)
                display_ccy = ccy
                if ccy == 'NOK':
                    display_price = round(price * 0.95, 2)   # NOK → SEK
                    display_ccy = 'SEK'
                elif ccy == 'DKK':
                    display_price = round(price * 1.55, 2)   # DKK → SEK
                    display_ccy = 'SEK'
                # USD and SEK pass through unchanged

                rows.append({
                    'symbol': sym, 'name': name, 'country': country, 'currency': display_ccy,
                    'sector': info.get('sector', 'N/A'),
                    'price': display_price, 'market_cap': mcap,
                    'cap_class': self._cap_class(mcap),
                    'chg_1d': chg[1], 'chg_7d': chg[7], 'chg_30d': chg[30],
                    'chg_90d': chg[90], 'chg_180d': chg[180],
                    'ret_1y': ret_1y, 'ret_3y': ret_3y, 'ret_5y': ret_5y, 'ret_10y': ret_10y,
                    'avg_volume': avg_vol, 'current_volume': cur_vol, 'volume_ratio': vol_ratio,
                    'div_yield_pct': div_pct, 'pe': round(pe, 2) if pe else None,
                    'pb': round(pb, 2) if (pb and 0 < pb <= 50) else None,   # GAP-13: >50 = data suspect
                    'eps': round(eps, 2) if eps else None,
                    'ev_ebit': ev_ebit if (ev_ebit is not None and 3 <= ev_ebit <= 60) else None,  # GAP-13
                    'sent_short': short, 'sent_mid': mid, 'sent_long': long_,
                    'buffett_quality': quality,
                    'buffett_intrinsic': intrinsic, 'buffett_mos_pct': mos,
                    'buffett_method': method,
                    'buffett_verdict': verdict,
                })
            except Exception as e:
                self.log(f"{sym}: failed ({str(e)[:70]}).", 'WARN')

            if fresh or cache_dirty:
                self._save_fund_cache(fund_cache)

        # Group by country (stable order)
        order = ['US', 'Sweden', 'Norway', 'Denmark']
        by_country = {}
        for c in order:
            grp = [r for r in rows if r['country'] == c]
            if grp:
                by_country[c] = grp

        # Buffett's Picks: strong quality + attractive valuation
        picks = [r for r in rows
            if r['buffett_quality'] >= self.QUALITY_THRESHOLD
                and r['buffett_mos_pct'] is not None
                and self.MOS_THRESHOLD <= r['buffett_mos_pct'] <= self.MOS_SANITY_CAP
                and r['buffett_verdict'] not in ('N/A', 'Verify Data')]
        picks.sort(key=lambda r: (r['buffett_mos_pct'], r['buffett_quality']), reverse=True)

        self.log(f"Enhanced Watchlist complete: {len(rows)} stocks, "
                 f"{len(picks)} Buffett Picks ({fresh} fundamentals refreshed).", 'SUCCESS')

        return {
            'by_country': by_country,
            'buffett_picks': picks,
            'meta': {
                'total': len(rows),
                'quality_threshold': self.QUALITY_THRESHOLD,
                'mos_threshold': self.MOS_THRESHOLD,
                'generated': datetime.now().isoformat(),
            },
        }