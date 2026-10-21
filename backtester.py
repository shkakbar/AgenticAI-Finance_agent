"""
Backtester Module - Tracks AI predictions and evaluates accuracy over time.
Saves predictions after each run, evaluates them against actual market moves 24h later.
"""
import json
import os
from datetime import datetime, timedelta
import yfinance as yf

class Backtester:
    def __init__(self, data_dir='data/backtest'):
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
        self.db_file = os.path.join(data_dir, 'predictions.json')
        self.predictions = self._load_db()

        # Core assets we will track to grade the AI's predictions
        self.tracked_assets = {
            'stocks': {'ticker': '^GSPC', 'name': 'S&P 500'},
            'gold': {'ticker': 'GC=F', 'name': 'Gold'},
            'bitcoin': {'ticker': 'BTC-USD', 'name': 'Bitcoin'}
        }

    def _load_db(self):
        """Load prediction history from disk"""
        if os.path.exists(self.db_file):
            try:
                with open(self.db_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return []
        return []

    def _save_db(self):
        """Save prediction history to disk"""
        try:
            with open(self.db_file, 'w', encoding='utf-8') as f:
                json.dump(self.predictions, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"    ⚠️  Could not save backtest database: {e}")

    def _get_current_price(self, ticker_symbol):
        """Fetch the current live price of an asset"""
        try:
            ticker = yf.Ticker(ticker_symbol)
            hist = ticker.history(period='1d')
            if not hist.empty:
                return round(hist['Close'].iloc[-1], 2)
        except:
            pass
        return None

    def save_predictions(self, sentiment_data, market_data):
        """
        Saves today's AI predictions and current market prices to the database.
        """
        print("    💾 Saving today's AI predictions for future backtesting...")
        
        timestamp = datetime.now().isoformat()
        
        # Extract current prices from the market_data already fetched by main.py
        current_prices = {}
        for asset_key, asset_info in self.tracked_assets.items():
            price = None
            # Search through market data to find the price
            for category, groups in market_data.items():
                if isinstance(groups, dict):
                    for group_name, tickers in groups.items():
                        if isinstance(tickers, list):
                            for t in tickers:
                                if t.get('symbol') == asset_info['ticker'] or asset_info['name'] in t.get('name', ''):
                                    price = t.get('price')
                                    break
                        if price: break
                if price: break
            
            # Fallback to yfinance if not found in market_data
            if price is None:
                price = self._get_current_price(asset_info['ticker'])
                
            current_prices[asset_key] = price

        # Extract AI sentiment scores
        asset_sentiments = sentiment_data.get('asset_sentiments', {})
        
        prediction_record = {
            'timestamp': timestamp,
            'overall_sentiment': sentiment_data.get('overall_sentiment', 0),
            'asset_predictions': {},
            'evaluated': False,
            'results': {}
        }

        # Map AI sentiment to our tracked assets
        mapping = {
            'stocks': 'stocks',
            'bullion': 'gold',
            'crypto': 'bitcoin'
        }

        for sentiment_key, asset_key in mapping.items():
            score = asset_sentiments.get(sentiment_key, {}).get('score', 0)
            prediction_record['asset_predictions'][asset_key] = {
                'ai_score': score,
                'ai_label': asset_sentiments.get(sentiment_key, {}).get('label', 'Neutral'),
                'price_at_prediction': current_prices.get(asset_key)
            }

        self.predictions.append(prediction_record)
        self._save_db()
        print(f"    ✅ Saved prediction record for {timestamp[:10]}")

    def evaluate_past_predictions(self):
        """
        Looks at predictions made 24+ hours ago, fetches current prices, 
        and grades the AI's accuracy.
        """
        print("    🔍 Evaluating past predictions (24h+ old)...")
        now = datetime.now()
        evaluated_count = 0
        wins = 0
        losses = 0

        for record in self.predictions:
            if record['evaluated']:
                continue

            pred_time = datetime.fromisoformat(record['timestamp'])
            # Only evaluate if 24 hours have passed
            if now - pred_time < timedelta(hours=24):
                continue

            record['evaluated'] = True
            record['results'] = {}
            evaluated_count += 1

            for asset_key, pred_data in record['asset_predictions'].items():
                ai_score = pred_data['ai_score']
                start_price = pred_data['price_at_prediction']

                # Skip neutral predictions (too ambiguous to grade)
                if -19 <= ai_score <= 19 or start_price is None:
                    continue

                current_price = self._get_current_price(self.tracked_assets[asset_key]['ticker'])
                if current_price is None:
                    continue

                # Calculate actual market movement
                price_change_pct = ((current_price - start_price) / start_price) * 100
                
                # Determine if AI was right
                # Bullish (>= 20) expects price to go UP (> 0)
                # Bearish (<= -20) expects price to go DOWN (< 0)
                is_correct = (ai_score >= 20 and price_change_pct > 0) or (ai_score <= -20 and price_change_pct < 0)

                record['results'][asset_key] = {
                    'ai_score': ai_score,
                    'start_price': start_price,
                    'end_price': current_price,
                    'price_change_pct': round(price_change_pct, 2),
                    'is_correct': is_correct
                }

                if is_correct:
                    wins += 1
                else:
                    losses += 1

        if evaluated_count > 0:
            self._save_db()
            print(f"    ✅ Evaluated {evaluated_count} past prediction cycles.")
            print(f"    📊 Grading results: {wins} Wins, {losses} Losses")
        else:
            print("    ⏳ No predictions older than 24 hours ready for evaluation yet.")

    def get_accuracy_stats(self):
        """
        Calculates the rolling accuracy score based on all evaluated predictions.
        Returns a dict with stats for the HTML report.
        """
        total_evaluated = 0
        total_wins = 0
        recent_results = []

        for record in reversed(self.predictions):  # Newest first
            if not record['evaluated']:
                continue
            
            for asset_key, result in record['results'].items():
                total_evaluated += 1
                if result['is_correct']:
                    total_wins += 1
                
                if len(recent_results) < 5:
                    recent_results.append({
                        'date': record['timestamp'][:10],
                        'asset': self.tracked_assets[asset_key]['name'],
                        'ai_label': record['asset_predictions'][asset_key]['ai_label'],
                        'market_move': result['price_change_pct'],
                        'is_correct': result['is_correct']
                    })

        accuracy_pct = round((total_wins / total_evaluated) * 100, 1) if total_evaluated > 0 else 0.0

        return {
            'total_evaluated': total_evaluated,
            'total_wins': total_wins,
            'accuracy_pct': accuracy_pct,
            'recent_results': recent_results
        }

