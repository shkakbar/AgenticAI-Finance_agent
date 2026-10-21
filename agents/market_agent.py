"""
Market Agent - Fetches live market data and multi-timeframe performance.
Rounds all values to 2 decimal places.
Maps performance data to keys expected by HTML generator.
Updated: Fetches 10 years of history to populate 3Y, 5Y, and 10Y columns.
"""
from agents.base_agent import BaseAgent
import yfinance as yf
import config

# Mapping from ticker symbols to HTML generator expected keys
PERFORMANCE_KEY_MAP = {
    '^GSPC': 'sp500',
    '^IXIC': 'nasdaq',
    '^DJI': 'dow_jones',
    '^OMXSPI': 'omx_stockholm',
    '^OMX': 'omx_stockholm',
    '^TNX': 'us10y_yield',
    '^IRX': 'us_tbill',
    'GC=F': 'gold',
    'SI=F': 'silver',
    'BTC-USD': 'bitcoin',
    'ETH-USD': 'ethereum',
    'SEK=X': 'usd_sek',
    'USDSEK=X': 'usd_sek',
    'EURSEK=X': 'eur_sek',
    'BZ=F': 'brent_crude',
    'CL=F': 'wti_crude',
    'NG=F': 'natural_gas',
}

PERFORMANCE_ICONS = {
    'sp500': '📈', 'nasdaq': '💻', 'dow_jones': '🏭',
    'omx_stockholm': '🇸🇪', 'us10y_yield': '🏦', 'us_tbill': '🏦',
    'gold': '🥇', 'silver': '🥈', 'bitcoin': '₿', 'ethereum': 'Ξ',
    'usd_sek': '💱', 'eur_sek': '💱',
    'brent_crude': '🛢️', 'wti_crude': '🛢️', 'natural_gas': '🔥',
}

class MarketAgent(BaseAgent):
    def __init__(self, model_router=None, vector_db=None):
        super().__init__('MarketAgent', model_router, vector_db)

    def execute(self, *args, **kwargs):
        """Fetch current market prices and multi-timeframe performance."""
        self.log("Fetching market data via yfinance...")

        market_tickers = getattr(config, 'MARKET_TICKERS', {})

        if not market_tickers:
            self.log("No MARKET_TICKERS found in config.py!", 'ERROR')
            return {'market_data': {}, 'performance_data': {}}

        market_data = {}
        performance_data = {}

        for asset_class, groups in market_tickers.items():
            market_data[asset_class] = {}

            if not isinstance(groups, dict):
                continue

            for group_name, ticker_list in groups.items():
                if not isinstance(ticker_list, list):
                    continue

                market_data[asset_class][group_name] = []

                for ticker_info in ticker_list:
                    if isinstance(ticker_info, str):
                        symbol = ticker_info
                        name = ticker_info
                        flag = ''
                    else:
                        symbol = ticker_info.get('symbol', '')
                        name = ticker_info.get('name', symbol)
                        flag = ticker_info.get('flag', '')

                    if not symbol:
                        continue

                    try:
                        ticker = yf.Ticker(symbol)
                        # UPDATED: Fetch 10 years of history to populate 3Y, 5Y, 10Y
                        hist = ticker.history(period="10y")
                        hist = hist.dropna(subset=['Close'])  # skip nan bars (Shanghai feed glitches)

                        """if not hist.empty and len(hist) >= 2:
                            current_price = round(float(hist['Close'].iloc[-1]), 2)
                            prev_close = float(hist['Close'].iloc[-2])

                            daily_change = round(((current_price - prev_close) / prev_close) * 100, 2) if prev_close > 0 else 0.0
                            weekly_change = round(((current_price - hist['Close'].iloc[-5]) / hist['Close'].iloc[-5]) * 100, 2) if len(hist) >= 5 else 0.0"""
                        if not hist.empty and len(hist) >= 2:
                            raw_price = float(hist['Close'].iloc[-1])
                            prev_close = float(hist['Close'].iloc[-2])
                            week_close = float(hist['Close'].iloc[-5]) if len(hist) >= 5 else None

                            # Determine decimal places based on price magnitude to avoid fake 100% moves
                            if raw_price <= 0:
                                decimals = 2
                            elif raw_price < 0.01:
                                decimals = 8   # e.g., SHIB, VET
                            elif raw_price < 1:
                                decimals = 4   # e.g., SAND
                            else:
                                decimals = 2   # e.g., BTC, ETH
                            current_price = round(raw_price, decimals)

                            # Calculate changes using RAW prices to ensure mathematical accuracy
                            daily_change = round(((raw_price - prev_close) / prev_close) * 100, 2) if prev_close > 0 else 0.0
                            weekly_change = round(((raw_price - week_close) / week_close) * 100, 2) if week_close and week_close > 0 else 0.0

                            if daily_change > 0:
                                direction = 'up'
                            elif daily_change < 0:
                                direction = 'down'
                            else:
                                direction = 'flat'

                            # Sprint 1B: anomaly guard — never publish fabricated −100% or >25% moves
                            # Catches SHIB −100%, VeChain +41.9% at $0.01, and any yfinance glitch.
                            # (No market_cap_bucket in ticker_info yet, so flag regardless of cap size.)
                            daily_anomaly = False
                            weekly_anomaly = False
                            if daily_change is not None and (daily_change <= -99.0 or abs(daily_change) > 25.0):
                                self.log(f"Anomaly suppressed for {symbol}: daily {daily_change:+.2f}%", 'WARN')
                                daily_change = None
                                daily_anomaly = True
                            if weekly_change is not None and (weekly_change <= -99.0 or abs(weekly_change) > 50.0):
                                self.log(f"Anomaly suppressed for {symbol}: weekly {weekly_change:+.2f}%", 'WARN')
                                weekly_change = None
                                weekly_anomaly = True

                            # When suppressed, render as N/A in HTML (price still shown)
                            price_display = current_price if not daily_anomaly else current_price
                            daily_disp = daily_change if daily_change is not None else None
                            weekly_disp = weekly_change if weekly_change is not None else None

                            market_data[asset_class][group_name].append({
                                'symbol': symbol,
                                'name': name,
                                'flag': flag,
                                'price': current_price,
                                'daily_change': daily_disp,
                                'weekly_change': weekly_disp,
                                'daily_direction': direction if not daily_anomaly else 'flat',
                                'daily_anomaly': daily_anomaly,
                                'weekly_anomaly': weekly_anomaly,
                            })

                            # Build performance data with HTML-expected keys
                            perf_key = PERFORMANCE_KEY_MAP.get(symbol, symbol)
                            if perf_key not in performance_data:
                                def get_return(days_back):
                                    idx = max(0, len(hist) - days_back)
                                    start_price = float(hist['Close'].iloc[idx])
                                    if start_price > 0:
                                        return round(((raw_price - start_price) / start_price) * 100, 2)
                                    return 0.0

                                def get_return_years(years):
                                    days = years * 252
                                    if len(hist) >= days:
                                        start_price = float(hist['Close'].iloc[-days])
                                        if start_price > 0:
                                            return round(((raw_price - start_price) / start_price) * 100, 2)
                                    return None

                                performance_data[perf_key] = {
                                    'name': name,
                                    'icon': PERFORMANCE_ICONS.get(perf_key, '📊'),
                                    'category': asset_class.replace('_', ' ').title(),
                                    'current_price': current_price,
                                    'timeframes': {
                                        '1M': get_return(21),
                                        '3M': get_return(63),
                                        '6M': get_return(126),
                                        '1Y': get_return(252),
                                        '3Y': get_return_years(3),
                                        '5Y': get_return_years(5),
                                        '10Y': get_return_years(10),
                                    }
                                }
                        else:
                            market_data[asset_class][group_name].append({
                                'symbol': symbol, 'name': name, 'flag': flag,
                                'price': 0.0, 'daily_change': 0.0, 'weekly_change': 0.0,
                                'daily_direction': 'flat',
                                'decimals': decimals
                            })
                    except Exception as e:
                        self.log(f"Failed to fetch {symbol}: {e}", 'WARN')
                        market_data[asset_class][group_name].append({
                            'symbol': symbol, 'name': name, 'flag': flag,
                            'price': 0.0, 'daily_change': 0.0, 'weekly_change': 0.0,
                            'daily_direction': 'flat'
                        })

        self.log(f"Market data complete. {len(performance_data)} performance entries.", 'SUCCESS')

        # GAP-01: Reconcile FX cross-rates from USD legs (yfinance cross tickers have unreliable closes)
        self._reconcile_fx_crosses(market_data)

        return {
            'market_data': market_data,
            'performance_data': performance_data
        }

        # ── GAP-01: Synthetic FX cross-rate reconciliation ─────────────
    # price = leg1 <op> leg2; % changes compound from the legs' own changes.
    CROSS_DEFINITIONS = {
        'JPYSEK=X': ('USDSEK=X', 'USDJPY=X', 'divide'),    # JPY/SEK = USDSEK ÷ USDJPY
        'EURSEK=X': ('EURUSD=X', 'USDSEK=X', 'multiply'),  # EUR/SEK = EURUSD × USDSEK
        'SEKINR=X': ('USDINR=X', 'USDSEK=X', 'divide'),    # SEK/INR = USDINR ÷ USDSEK
    }

    def _reconcile_fx_crosses(self, market_data):
        """Recompute cross-rate prices & % changes algebraically from liquid USD legs."""
        lookup = {}

        def _extract(obj):
            if isinstance(obj, dict):
                for v in obj.values():
                    _extract(v)
            elif isinstance(obj, list):
                for item in obj:
                    if isinstance(item, dict) and 'symbol' in item:
                        lookup[item['symbol']] = item

        _extract(market_data)

        # Each leg accepts every symbol variant present in config.py
        cross_map = {
            'JPYSEK=X': (['USDSEK=X', 'SEK=X'], ['USDJPY=X', 'JPY=X'], 'divide'),
            'EURSEK=X': (['EURUSD=X'],          ['USDSEK=X', 'SEK=X'], 'multiply'),
            'SEKINR=X': (['USDINR=X', 'INR=X'], ['USDSEK=X', 'SEK=X'], 'divide'),
        }

        for cross_sym, (leg1_opts, leg2_opts, op) in cross_map.items():
            cross = lookup.get(cross_sym)
            leg1  = next((lookup[s] for s in leg1_opts if s in lookup), None)
            leg2  = next((lookup[s] for s in leg2_opts if s in lookup), None)

            if not cross:
                self.log(f"FX cross {cross_sym}: CROSS SYMBOL NOT FOUND. Have: {sorted(lookup.keys())}", 'WARN')
                continue
            if not leg1 or not leg2:
                missing = [o for o in leg1_opts if o not in lookup] + [o for o in leg2_opts if o not in lookup]
                self.log(f"FX cross {cross_sym}: missing leg(s) {missing}. Have: {sorted(lookup.keys())}", 'WARN')
                continue

            try:
                p1, p2 = float(leg1['price']), float(leg2['price'])
                if p2 <= 0:
                    continue
                new_price = (p1 / p2) if op == 'divide' else (p1 * p2)
                cross['price'] = round(new_price, 4) if new_price < 10 else round(new_price, 2)

                for chg_key in ('daily_change', 'weekly_change'):
                    c1, c2 = float(leg1.get(chg_key, 0.0)), float(leg2.get(chg_key, 0.0))
                    d1 = (1 + c1 / 100.0) or 1.0
                    d2 = (1 + c2 / 100.0) or 1.0
                    p1_prev, p2_prev = p1 / d1, p2 / d2
                    prev_price = (p1_prev / p2_prev) if op == 'divide' else (p1_prev * p2_prev)
                    if prev_price:
                        cross[chg_key] = round(((cross['price'] / prev_price) - 1) * 100, 2)

                dc = cross.get('daily_change', 0.0)
                cross['daily_direction'] = 'up' if dc > 0 else 'down' if dc < 0 else 'flat'
                self.log(f"FX cross {cross_sym} reconciled: {cross['price']} ({cross['daily_change']}%)", 'SUCCESS')
            except Exception as e:
                self.log(f"FX reconciliation math failed for {cross_sym}: {e}", 'WARN')