import ollama
from config import OLLAMA_MODEL, ASSET_CLASSES, REGIONS, SUB_CLASSES
import json, os, re
from datetime import datetime
from agents.base_agent import BaseAgent
from schemas import TimeHorizonSentiment, ConsolidatedMarketView



class SentimentAnalyzer:
    def __init__(self):
        self.model = OLLAMA_MODEL
        self.history_dir = 'data/sentiment_history'
        os.makedirs(self.history_dir, exist_ok=True)

    def analyze_sentiment(self, news_items):
        """Analyze sentiment with robust multi-layer fallback"""
        if not news_items:
            return self._empty_sentiment()

        # Prepare news summary
        news_summary = []
        for i, news in enumerate(news_items[:15], 1):
            title = news.get('title', '')
            region = news.get('region_name', 'Global')
            news_summary.append(f"{i}. [{region}] {title}")

        news_text = '\n'.join(news_summary)

        print(f"    📝 Analyzing {len(news_items)} news items...")

        # STEP 1: Try AI analysis
        result = self._try_ai_sentiment(news_text)

        # STEP 2: If AI failed, use keyword-based fallback
        if result.get('_failed', False):
            print("    ⚠️  AI sentiment failed, using keyword fallback...")
            result = self._keyword_fallback_sentiment(news_items)

        # Clean up internal flags
        result.pop('_failed', None)

        self._save_to_history(result)
        return result

    def _try_ai_sentiment(self, news_text):
        """Try to get sentiment from AI with robust parsing"""

        # Simpler prompt - ask for plain text format, not JSON
        prompt = f"""Analyze these financial news headlines. For each category, give a sentiment score from -100 (very bearish) to +100 (very bullish).
        NEWS:
{news_text}
Respond in this EXACT format (one line per item, no other text):
OVERALL: <score>
STOCKS: <score>
BONDS: <score>
FOREX: <score>
CRYPTO: <score>
FUNDS: <score>
BULLION: <score>
US: <score>
EU: <score>
JP: <score>
CN: <score>
NORDICS: <score>
DK: <score>
SE: <score>
DRIVERS: <comma-separated list of 2-3 key drivers>
Use only integers. Example: OVERALL: +25"""
        try:
            response = ollama.chat(
                model=self.model,
                messages=[{'role': 'user', 'content': prompt}]
            )
            content = response['message']['content']

            # DEBUG: Show what we got
            print(f"    🔍 AI response preview: {content[:200]}...")

            # Try to parse the simple format
            parsed = self._parse_simple_format(content)
            if parsed and self._has_nonzero_scores(parsed):
                print("    ✅ AI sentiment parsed successfully")
                return parsed

            # Try JSON extraction as backup
            json_data = self._extract_json(content)
            if json_data:
                parsed = self._normalize_from_json(json_data)
                if parsed and self._has_nonzero_scores(parsed):
                    print("    ✅ AI sentiment parsed from JSON")
                    return parsed

            print("    ⚠️  Could not extract meaningful scores from AI response")
            return {'_failed': True}

        except Exception as e:
            print(f"    ⚠️  AI call failed: {e}")
            return {'_failed': True}

    def _parse_simple_format(self, content):
        """Parse the simple KEY: VALUE format"""
        result = {
            'overall_sentiment': 0,
            'overall_label': 'Neutral',
            'asset_sentiments': {},
            'sub_class_sentiments': {},
            'regional_sentiments': {},
            'key_drivers': [],
            'sentiment_shift': 'stable'
        }

        # Map of keys to where they go
        asset_map = {
            'STOCKS': 'stocks', 'BONDS': 'bonds', 'FOREX': 'forex',
            'CRYPTO': 'crypto', 'FUNDS': 'funds', 'BULLION': 'bullion'
        }
        region_map = {
            'US': 'US', 'EU': 'EU', 'JP': 'JP', 'CN': 'CN',
            'NORDICS': 'Nordics', 'DK': 'DK', 'SE': 'SE'
        }

        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            if ':' not in line:
                continue

            key, _, value = line.partition(':')
            key = key.strip().upper()
            value = value.strip()

            # Extract integer from value
            score = self._extract_int(value)

            if key == 'OVERALL':
                result['overall_sentiment'] = score
                result['overall_label'] = self._label(score)
            elif key in asset_map:
                asset = asset_map[key]
                result['asset_sentiments'][asset] = {'score': score, 'label': self._label(score)}
            elif key in region_map:
                region = region_map[key]
                result['regional_sentiments'][region] = {'score': score, 'label': self._label(score)}
            elif key == 'DRIVERS':
                # Parse comma-separated drivers
                drivers = [d.strip() for d in value.split(',') if d.strip()]
                result['key_drivers'] = drivers[:5]

        # Fill in missing assets/regions with 0
        for asset in ['stocks','bonds','forex','crypto','funds','bullion']:
            if asset not in result['asset_sentiments']:
                result['asset_sentiments'][asset] = {'score': 0, 'label': 'Neutral'}
        for region in ['US','EU','JP','CN','Nordics','DK','SE']:
            if region not in result['regional_sentiments']:
                result['regional_sentiments'][region] = {'score': 0, 'label': 'Neutral'}

        # Generate sub-class sentiments based on parent asset + region
        result['sub_class_sentiments'] = self._derive_subclass_sentiments(
            result['asset_sentiments'], result['regional_sentiments']
        )

        return result

    def _derive_subclass_sentiments(self, asset_sentiments, regional_sentiments):
        """Derive sub-class scores from parent asset + regional scores"""
        result = {}

        # Stocks sub-classes: blend asset score with regional score
        stocks_score = asset_sentiments.get('stocks', {}).get('score', 0)
        for sub, region in [('US Stocks','US'), ('EU Stocks','EU'),
                            ('Asia Stocks','JP'), ('Nordic Stocks','SE')]:
            reg_score = regional_sentiments.get(region, {}).get('score', 0)
            blended = int(stocks_score * 0.6 + reg_score * 0.4)
            result[sub] = {'score': self._clamp(blended), 'label': self._label(blended)}

        # Bonds sub-classes
        bonds_score = asset_sentiments.get('bonds', {}).get('score', 0)
        result['Government Bonds'] = {'score': bonds_score, 'label': self._label(bonds_score)}
        result['Yield Curve'] = {'score': int(bonds_score * 0.8), 'label': self._label(int(bonds_score * 0.8))}

        # Forex sub-classes
        forex_score = asset_sentiments.get('forex', {}).get('score', 0)
        result['Major FX'] = {'score': forex_score, 'label': self._label(forex_score)}
        nordic_fx = (regional_sentiments.get('SE',{}).get('score',0) + regional_sentiments.get('DK',{}).get('score',0)) // 2
        result['Nordic FX'] = {'score': nordic_fx, 'label': self._label(nordic_fx)}
        result['EM FX'] = {'score': regional_sentiments.get('CN',{}).get('score',0), 'label': self._label(regional_sentiments.get('CN',{}).get('score',0))}

        # Crypto sub-classes - large cap stronger, meme weaker
        crypto_score = asset_sentiments.get('crypto', {}).get('score', 0)
        result['Large Cap Crypto'] = {'score': crypto_score, 'label': self._label(crypto_score)}
        result['Mid Cap Crypto'] = {'score': int(crypto_score * 0.8), 'label': self._label(int(crypto_score * 0.8))}
        result['Meme & Alt'] = {'score': int(crypto_score * 0.5), 'label': self._label(int(crypto_score * 0.5))}

        # Funds sub-classes
        funds_score = asset_sentiments.get('funds', {}).get('score', 0)
        result['ETFs'] = {'score': funds_score, 'label': self._label(funds_score)}
        result['Active Funds'] = {'score': funds_score, 'label': self._label(funds_score)}

        # Bullion sub-classes
        bullion_score = asset_sentiments.get('bullion', {}).get('score', 0)
        result['Gold'] = {'score': bullion_score, 'label': self._label(bullion_score)}
        result['Silver'] = {'score': int(bullion_score * 0.9), 'label': self._label(int(bullion_score * 0.9))}

        return result

    def _keyword_fallback_sentiment(self, news_items):
        """Last resort: infer sentiment from keyword analysis"""
        bullish_keywords = ['rally', 'surge', 'gain', 'rise', 'jump', 'soar', 'bull',
                        'upgrade', 'growth', 'record', 'high', 'strong', 'boost',
                        'recovery', 'optimism', 'breakthrough', 'truce', 'deal']
        bearish_keywords = ['crash', 'plunge', 'fall', 'drop', 'decline', 'slump', 'bear',
                        'downgrade', 'recession', 'low', 'weak', 'cut', 'crisis',
                        'war', 'conflict', 'hack', 'threat', 'fear', 'concern',
                        'sell-off', 'selloff', 'pressure', 'tension']

        # Count keywords across all news
        bull_count = 0
        bear_count = 0
        all_text = ' '.join([n.get('title','') + ' ' + n.get('summary','') for n in news_items]).lower()

        for kw in bullish_keywords:
            bull_count += all_text.count(kw)
        for kw in bearish_keywords:
            bear_count += all_text.count(kw)

        total = bull_count + bear_count
        if total == 0:
            overall_score = 0
        else:
            # Scale to -100 to +100
            overall_score = int(((bull_count - bear_count) / total) * 100)

        overall_score = self._clamp(overall_score)
        overall_label = self._label(overall_score)

        print(f"    📊 Keyword fallback: {bull_count} bullish, {bear_count} bearish → {overall_score:+d}")

        # Apply same score to all (crude but better than zeros)
        asset_sentiments = {
            a: {'score': overall_score, 'label': overall_label}
            for a in ['stocks','bonds','forex','crypto','funds','bullion']
        }

        regional_sentiments = {
            r: {'score': overall_score, 'label': overall_label}
            for r in ['US','EU','JP','CN','Nordics','DK','SE']
        }

        # Identify top drivers from most common keywords
        keyword_counts = {}
        for kw in bullish_keywords + bearish_keywords:
            c = all_text.count(kw)
            if c > 0:
                keyword_counts[kw] = c
        top_drivers = sorted(keyword_counts.items(), key=lambda x: x[1], reverse=True)[:3]
        drivers = [f"{kw} ({c}x)" for kw, c in top_drivers]

        return {
            'overall_sentiment': overall_score,
            'overall_label': overall_label,
            'asset_sentiments': asset_sentiments,
            'sub_class_sentiments': self._derive_subclass_sentiments(asset_sentiments, regional_sentiments),
            'regional_sentiments': regional_sentiments,
            'key_drivers': drivers if drivers else ['No clear sentiment drivers'],
            'sentiment_shift': 'stable'
        }

    def _extract_int(self, text):
        """Extract integer from text like '+25', '-30', '45', etc."""
        text = text.strip()
        # Try to find pattern like +25, -30, 45
        match = re.search(r'[+-]?\d+', text)
        if match:
            return self._clamp(int(match.group()))
        return 0

    def _clamp(self, v):
        try: return max(-100, min(100, int(v)))
        except: return 0

    def _label(self, score):
        if score >= 40: return "Bullish"
        if score >= 20: return "Mildly Bullish"
        if score >= -19: return "Neutral"
        if score >= -39: return "Mildly Bearish"
        return "Bearish"

    def _has_nonzero_scores(self, data):
        """Check if we got any non-zero scores"""
        if data.get('overall_sentiment', 0) != 0:
            return True
        for asset, d in data.get('asset_sentiments', {}).items():
            if isinstance(d, dict) and d.get('score', 0) != 0:
                return True
        return False

    def _extract_json(self, content):
        """Robust JSON extraction"""
        content = content.strip()

        # Remove markdown code blocks
        if '```' in content:
            content = re.sub(r'```(?:json)?\s*', '', content)
            content = content.replace('```', '')

        # Try direct parse
        try:
            return json.loads(content)
        except:
            pass

        # Find JSON object
        try:
            start = content.find('{')
            end = content.rfind('}') + 1
            if start != -1 and end > start:
                json_str = content[start:end]
                # Fix common issues
                json_str = re.sub(r',\s*}', '}', json_str)  # trailing comma
                json_str = re.sub(r',\s*]', ']', json_str)
                return json.loads(json_str)
        except:
            pass

        return None

    def _normalize_from_json(self, data):
        """Convert JSON response to standard format"""
        result = {
            'overall_sentiment': 0,
            'overall_label': 'Neutral',
            'asset_sentiments': {},
            'sub_class_sentiments': {},
            'regional_sentiments': {},
            'key_drivers': [],
            'sentiment_shift': 'stable'
        }

        # Overall
        if 'overall_sentiment' in data:
            score = self._clamp(data['overall_sentiment'])
            result['overall_sentiment'] = score
            result['overall_label'] = self._label(score)

        # Assets
        for asset in ['stocks','bonds','forex','crypto','funds','bullion']:
            d = data.get('asset_sentiments', {}).get(asset, {})
            if isinstance(d, dict):
                score = self._clamp(d.get('score', 0))
            else:
                score = self._clamp(d)
            result['asset_sentiments'][asset] = {'score': score, 'label': self._label(score)}

        # Regions
        for region in ['US','EU','JP','CN','Nordics','DK','SE']:
            d = data.get('regional_sentiments', {}).get(region, {})
            if isinstance(d, dict):
                score = self._clamp(d.get('score', 0))
            else:
                score = self._clamp(d)
            result['regional_sentiments'][region] = {'score': score, 'label': self._label(score)}

        # Sub-classes
        result['sub_class_sentiments'] = self._derive_subclass_sentiments(
            result['asset_sentiments'], result['regional_sentiments']
        )

        # Drivers
        drivers = data.get('key_drivers', [])
        if isinstance(drivers, list):
            result['key_drivers'] = [str(d) for d in drivers[:5]]

        return result

    def _empty_sentiment(self):
        return {
            'overall_sentiment': 0, 'overall_label': 'Neutral',
            'asset_sentiments': {a: {'score':0,'label':'Neutral'} for a in ['stocks','bonds','forex','crypto','funds','bullion']},
            'sub_class_sentiments': {sub: {'score':0,'label':'Neutral'} for subs in SUB_CLASSES.values() for sub in subs.keys()},
            'regional_sentiments': {r: {'score':0,'label':'Neutral'} for r in ['US','EU','JP','CN','Nordics','DK','SE']},
            'key_drivers': [], 'sentiment_shift': 'stable', 'historical_trend': []
        }

    def _save_to_history(self, sentiment_data):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        snapshot = {
            'timestamp': datetime.now().isoformat(),
            'overall_sentiment': sentiment_data['overall_sentiment'],
            'overall_label': sentiment_data['overall_label'],
            'asset_sentiments': sentiment_data['asset_sentiments'],
            'sub_class_sentiments': sentiment_data.get('sub_class_sentiments', {}),
            'regional_sentiments': sentiment_data['regional_sentiments']
        }
        history_file = os.path.join(self.history_dir, f'sentiment_{timestamp}.json')
        with open(history_file, 'w', encoding='utf-8') as f:
            json.dump(snapshot, f, indent=2, ensure_ascii=False)
        self._update_rolling_history(snapshot)

    def _update_rolling_history(self, snapshot):
        history_file = os.path.join(self.history_dir, 'sentiment_history.json')
        history = []
        if os.path.exists(history_file):
            try:
                with open(history_file, 'r', encoding='utf-8') as f:
                    history = json.load(f)
            except:
                history = []
        history.append(snapshot)
        history = history[-100:]
        with open(history_file, 'w', encoding='utf-8') as f:
            json.dump(history, f, indent=2, ensure_ascii=False)

    def get_historical_trend(self, periods=10):
        history_file = os.path.join(self.history_dir, 'sentiment_history.json')
        if not os.path.exists(history_file):
            return []
        try:
            with open(history_file, 'r', encoding='utf-8') as f:
                return json.load(f)[-periods:]
        except:
            return []