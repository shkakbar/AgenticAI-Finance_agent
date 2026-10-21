"""
Sentiment Agent - AI-driven sentiment analysis with LLM-powered sub-sentiments.
Replaces keyword counting with batched LLM scoring for nuanced, context-aware results.
Falls back to keyword scoring if LLM fails.
"""
from agents.base_agent import BaseAgent
from schemas import TimeHorizonSentiment, ConsolidatedMarketView, BatchedCategorySentiments, ImpactBatch
import config, re

# Mapping from sub-class display names to schema field names

SUB_CLASS_FIELD_MAP = {
 'US Stocks': 'sub_US_Stocks',
 'EU Stocks': 'sub_EU_Stocks',
 'Asia Stocks': 'sub_Asia_Stocks',
 'Nordic Stocks': 'sub_Nordic_Stocks',
 'Government Bonds': 'sub_Gov_Bonds',
 'Yield Curve': 'sub_Yield_Curve',
 'Major FX': 'sub_Major_FX',
 'Nordic FX': 'sub_Nordic_FX',
 'EM FX': 'sub_EM_FX',
 'Large Cap Crypto': 'sub_Large_Cap_Crypto',
 'Mid Cap Crypto': 'sub_Mid_Cap_Crypto',
 'Meme & Alt': 'sub_Meme_Alt',
 'ETFs': 'sub_ETFs',
 'Active Funds': 'sub_Active_Funds',
 'Gold': 'sub_Gold',
 'Silver': 'sub_Silver',
}

REGION_FIELD_MAP = {
 'US': 'region_US',
 'EU': 'region_EU',
 'JP': 'region_JP',
 'CN': 'region_CN',
 'Nordics': 'region_Nordics',
 'DK': 'region_DK',
 'SE': 'region_SE',
}

class SentimentAgent(BaseAgent):
    def __init__(self, model_router=None, vector_db=None):
        super().__init__('SentimentAgent', model_router, vector_db)

    def execute(self, all_news, market_summary=""):
        if not self.validate_input(all_news):
            return None

        news_context = "\n".join([f"- {n.get('title', '')}" for n in all_news[:30]])

        system_prompt = """You are an elite quantitative analyst. Output STRICT JSON.
            CRITICAL: current_sentiment_score and overall_trend_score are INTEGERS from -100 to 100 (not decimals).
            confidence_score is a decimal between 0 and 1.
            The outlook fields (short_term_outlook, medium_term_outlook, long_term_outlook) and every key_drivers entry MUST be full prose sentences, never bare numbers.
            GROUNDING RULES:
            - Every key_drivers entry MUST trace to a specific headline or data point in the inputs. Never name a company or asset that does not appear in the MARKET SUMMARY or NEWS HEADLINES.
            - Sentiment direction must match the data: if an index or sector is negative in the inputs, do not describe it as driving positive sentiment.
            - Outlooks are CONDITIONAL SCENARIOS grounded in today's data, not promises. Use 'could', 'may', 'if'. Never give advice."""

        cv_system_prompt = """You are an elite quantitative analyst writing for institutional investors. Output STRICT JSON.
            CRITICAL: executive_summary, price_action_synthesis, macro_synthesis and bottom_line MUST each be full prose paragraphs of 2-4 complete sentences describing market conditions.
            NEVER place a bare number, score or digit alone in these fields - they are narrative text, not scores.
            GROUNDING RULES (a violation makes your output invalid):
            1. DATA CITATION: The MARKET SUMMARY contains exact prices and % changes. Every directional claim must cite the exact figure from that data (e.g., 'the Dow rose 0.83%'). Never invent, round up, or approximate figures.
            2. ADJECTIVE DISCIPLINE: Words like 'significant', 'sharp', 'surge', 'plunge', 'robust' may ONLY describe moves of at least 2% in one day or 5% over one week. Moves under 1% must be called 'marginal', 'modest', or 'flat'.
            3. NO INVENTED RALLIES: Do not describe a 'recovery' or 'rally' in any asset or sector unless its reported change is positive. If an index is negative on the week, state that plainly.
            4. NO UNSUPPORTED MACRO CLAIMS: Do not mention debt levels, recession indicators, inflation, or central-bank policy unless a specific headline or data point in the inputs supports it. If the data is absent, state that it is not covered today.
            5. CLOSED UNIVERSE: Reference ONLY companies, assets, and events that appear in the MARKET SUMMARY or NEWS HEADLINES. Never introduce outside names.
            6. TONE: Dry, factual, institutional research desk. No cheerleading, no advice, and no 'investors should capitalize' language in any field including bottom_line."""

        user_prompt = f"MARKET SUMMARY:\n{market_summary}\n\nNEWS HEADLINES:\n{news_context}"

        # === Phase 1: Deep structured outputs (DEEP model) ===
        self.log("Generating Time-Horizon Sentiment [DEEP model + JSON]...")
        time_horizon = self.model_router.generate_structured_output(
            prompt=user_prompt, system_prompt=system_prompt,
            schema=TimeHorizonSentiment, task_type='deep'
        )

        self.log("Generating Consolidated Market View [DEEP model + JSON]...")
        consolidated_view = self.model_router.generate_structured_output(
            prompt=user_prompt, system_prompt=cv_system_prompt,
            schema=ConsolidatedMarketView, task_type='deep'
        )

        # === Phase 2: Batched LLM scoring (FAST model) ===
        self.log("Generating batched category sentiments [FAST model + JSON]...")
        batched_prompt = self._build_batched_prompt(all_news, market_summary)
        batched_system = """You are a quantitative sentiment classifier.
    Score EACH category from -100 (very bearish) to +100 (very bullish) based on the news.
    Output ONLY valid JSON with integer values. Use 0 if news is neutral or irrelevant to a category."""
        
        batched_scores = self.model_router.generate_structured_output(
            prompt=batched_prompt,
            system_prompt=batched_system,
            schema=BatchedCategorySentiments,
            task_type='fast'
        )
        # === Phase 2.5: Per-news causal impact analysis (DEEP model) ===   # <-- EDIT 1
        try:
            self.log("Running per-news causal impact analysis [FAST model]...")
            impact_analysis = self._analyze_impacts(all_news)
        except Exception as e:
            self.log(f"⚠️ Impact analysis failed; continuing without it: {str(e)[:120]}", 'WARN')
            impact_analysis = {}

        # === Phase 3: Build output using LLM scores, with keyword fallback ===
        asset_sentiments = self._build_asset_sentiments(all_news, batched_scores)
        regional_sentiments = self._build_regional_sentiments(all_news, batched_scores)
        sub_class_sentiments = self._build_sub_class_sentiments(all_news, batched_scores)

        # P1-3 / 2A-3: ONE deterministic source of truth for every gauge.
        overall_score, reconciliation = self._reconcile_scores(asset_sentiments, impact_analysis)
        overall_label = (self._score_to_label(overall_score)
                         if overall_score is not None else 'Insufficient Data')

        # Retire the independent LLM trend estimate. Both gauges now read the same
        # evidence base. A genuine multi-session PRICE trend is scoped to Sprint 4,
        # at which point the two horizons may legitimately diverge — and will be
        # labelled and bridged explicitly rather than silently contradicted.
        try:
            numeric = overall_score if overall_score is not None else 0
            time_horizon.current_sentiment_score = numeric
            time_horizon.current_label = overall_label
            time_horizon.overall_trend_score = numeric
            time_horizon.overall_label = overall_label
        except Exception as e:
            self.log(f"Reconciliation write-back failed: {e}", 'WARN')

        # 2A-4: explicit zero-coverage entries become null, never fake Neutral.
        # Defensive: only acts where news_count is explicitly present and zero.
        for collection in (sub_class_sentiments, regional_sentiments):
            if not isinstance(collection, dict):
                continue
            for key, entry in list(collection.items()):
                if isinstance(entry, dict) and entry.get('news_count') == 0:
                    entry['score'] = None
                    entry['label'] = 'Insufficient Data'

        if overall_score > 15:
            sentiment_shift = 'improving'
        elif overall_score < -15:
            sentiment_shift = 'deteriorating'
        else:
            sentiment_shift = 'stable'

        return {
            'overall_sentiment': overall_score,
            'overall_label': overall_label,
            'sentiment_shift': sentiment_shift,
            'key_drivers': time_horizon.key_drivers,
            'asset_sentiments': asset_sentiments,
            'sub_class_sentiments': sub_class_sentiments,
            'regional_sentiments': regional_sentiments,
            'time_horizon': time_horizon.model_dump(),
            'consolidated_view': consolidated_view.model_dump(),
            '_scoring_method': 'llm_batched',
            'impact_analysis': impact_analysis,   # <-- EDIT 2
            'reconciliation': reconciliation,
        }
        

    def _normalize_batched_scores(self, batched_scores, raw_output):
        """Normalize LLM scores if Pydantic validation missed some fields."""
        import json
        
        try:
            # Try to parse raw output as JSON
            raw_dict = json.loads(raw_output)
            
            # Map common variations to our field names
            field_mappings = {
                # Regions - various formats
                'United States': 'region_US',
                'USA': 'region_US',
                'America': 'region_US',
                'US': 'region_US',
                'Europe': 'region_EU',
                'European Union': 'region_EU',
                'Eurozone': 'region_EU',
                'EU': 'region_EU',
                'Japan': 'region_JP',
                'JP': 'region_JP',
                'China': 'region_CN',
                'CN': 'region_CN',
                'Sweden': 'region_SE',
                'SE': 'region_SE',
                'Denmark': 'region_DK',
                'DK': 'region_DK',
                'Nordics': 'region_Nordics',
                
                # Sub-classes - various formats
                'US Stock': 'sub_US_Stocks',
                'US Stocks': 'sub_US_Stocks',
                'European Stocks': 'sub_EU_Stocks',
                'EU Stocks': 'sub_EU_Stocks',
                'Asian Stocks': 'sub_Asia_Stocks',
                'Asia Stocks': 'sub_Asia_Stocks',
                'Nordic Stock': 'sub_Nordic_Stocks',
                'Nordic Stocks': 'sub_Nordic_Stocks',
                'Gov Bonds': 'sub_Gov_Bonds',
                'Government Bond': 'sub_Gov_Bonds',
                'Government Bonds': 'sub_Gov_Bonds',
                'Large Cap': 'sub_Large_Cap_Crypto',
                'Large Cap Crypto': 'sub_Large_Cap_Crypto',
                'Mid Cap': 'sub_Mid_Cap_Crypto',
                'Mid Cap Crypto': 'sub_Mid_Cap_Crypto',
                'Meme': 'sub_Meme_Alt',
                'Meme & Alt': 'sub_Meme_Alt',
                'ETF': 'sub_ETFs',
                'ETFs': 'sub_ETFs',
                'Active Fund': 'sub_Active_Funds',
                'Active Funds': 'sub_Active_Funds',
            }
            
            # Update batched_scores with normalized values
            updated_fields = []
            for raw_key, value in raw_dict.items():
                if isinstance(value, (int, float)):
                    int_value = int(value)
                    
                    # Direct match - check if field exists
                    if hasattr(batched_scores, raw_key):
                        setattr(batched_scores, raw_key, int_value)
                        updated_fields.append(raw_key)
                    
                    # Mapped match - convert common variations
                    elif raw_key in field_mappings:
                        mapped_field = field_mappings[raw_key]
                        if hasattr(batched_scores, mapped_field):
                            setattr(batched_scores, mapped_field, int_value)
                            updated_fields.append(f"{raw_key} -> {mapped_field}")
            
            if updated_fields:
                self.log(f"Normalized {len(updated_fields)} fields: {', '.join(updated_fields[:10])}...", 'INFO')
            
        except json.JSONDecodeError as e:
            self.log(f"Could not parse raw JSON for normalization: {e}", 'WARN')
        except Exception as e:
            self.log(f"Normalization error: {e}", 'WARN')
        
        return batched_scores

    def _build_batched_prompt(self, all_news, market_summary):
        """Build a compact prompt for batched scoring."""
        headlines = []
        for n in all_news[:40]:
            region = n.get('region_code', '?')
            title = n.get('title', '')[:120]
            headlines.append(f"[{region}] {title}")
        
        return f"""Market Summary: {market_summary}

    Recent Headlines (region code in brackets):
    {chr(10).join(headlines)}

    CRITICAL: Output a FLAT JSON object with these exact field names. Do NOT group them into nested objects.

    Asset class scores (integers from -100 to +100):
    "stocks", "bonds", "forex", "crypto", "funds", "bullion", "volatility"

    Region scores (integers from -100 to +100):
    "region_US", "region_EU", "region_JP", "region_CN", "region_Nordics", "region_DK", "region_SE"

    Sub-class scores (integers from -100 to +100):
    "sub_US_Stocks", "sub_EU_Stocks", "sub_Asia_Stocks", "sub_Nordic_Stocks", "sub_Gov_Bonds", "sub_Yield_Curve", "sub_Major_FX", "sub_Nordic_FX", "sub_EM_FX", "sub_Large_Cap_Crypto", "sub_Mid_Cap_Crypto", "sub_Meme_Alt", "sub_ETFs", "sub_Active_Funds", "sub_Gold", "sub_Silver"

    Rules:
    - Score 0 if there is no DIRECTLY relevant headline for that category. Do NOT guess or extrapolate from general market news. If you have no Japan-specific headline, region_JP and sub_Asia_Stocks must reflect only what is evidenced.
    - Direction: rate cuts, strong earnings, GDP growth = positive. Inflation spikes, recession fears, geopolitical escalation = negative.
    - MAGNITUDE CALIBRATION (critical):
        ±5  to ±10 : a single relevant headline, mild signal
        ±15 to ±25 : multiple corroborating headlines around one clear theme
        ±30 to ±40 : strong, overwhelming evidence across many headlines
      NEVER exceed ±40 in any category.
    - Volatility is a RISK STATE, not a direction: positive = rising fear/uncertainty, negative = calming. Do not treat it as bullish/bearish.
    - Region to sub-class mapping: [US]→region_US, sub_US_Stocks. [EU]→region_EU, sub_EU_Stocks. [CN]→region_CN, sub_Asia_Stocks. [SE]→region_SE, sub_Nordic_Stocks, sub_Nordic_FX. [DK]→region_DK, sub_Nordic_Stocks.
    - Only score a sub-class when a headline specifically addresses it. Do NOT infer a sub-class move from broad market news.
    - Output ONLY the flat JSON object. No explanations, no nested structures.

    Example format:
    {{"stocks": 25, "bonds": -10, "forex": 0, "region_US": 30, "region_SE": 15, "sub_Nordic_Stocks": 20, ...}}
    """

    def _normalize_batched_scores(self, batched_scores, raw_output):
        """Normalize LLM scores if Pydantic validation missed some fields."""
        import json
        
        try:
            # Try to parse raw output as JSON
            raw_dict = json.loads(raw_output)
            
            # Map common variations to our field names
            field_mappings = {
                # Regions
                'United States': 'region_US',
                'USA': 'region_US',
                'America': 'region_US',
                'Europe': 'region_EU',
                'European Union': 'region_EU',
                'Japan': 'region_JP',
                'China': 'region_CN',
                'Sweden': 'region_SE',
                'Denmark': 'region_DK',
                
                # Sub-classes
                'US Stock': 'sub_US_Stocks',
                'European Stocks': 'sub_EU_Stocks',
                'Asian Stocks': 'sub_Asia_Stocks',
                'Nordic Stock': 'sub_Nordic_Stocks',
                'Gov Bonds': 'sub_Gov_Bonds',
                'Government Bond': 'sub_Gov_Bonds',
                'Large Cap': 'sub_Large_Cap_Crypto',
                'Mid Cap': 'sub_Mid_Cap_Crypto',
                'Meme': 'sub_Meme_Alt',
                'Alt': 'sub_Meme_Alt',
                'ETF': 'sub_ETFs',
                'Active Fund': 'sub_Active_Funds',
            }
            
            # Update batched_scores with normalized values
            for raw_key, value in raw_dict.items():
                if isinstance(value, (int, float)):
                    # Direct match
                    if hasattr(batched_scores, raw_key):
                        setattr(batched_scores, raw_key, int(value))
                    # Mapped match
                    elif raw_key in field_mappings:
                        mapped_field = field_mappings[raw_key]
                        if hasattr(batched_scores, mapped_field):
                            setattr(batched_scores, mapped_field, int(value))
        except Exception as e:
            self.log(f"Warning: Could not normalize scores: {e}", 'WARN')
        
        return batched_scores

    def _build_asset_sentiments(self, all_news, batched_scores):
        """2A-4: Null — never 0 — when an asset class has no coverage.
        Removes the pre-loop debug print (it logged an empty dict)."""
        asset_classes = getattr(config, 'ASSET_CLASSES', {})
        sentiments = {}

        for asset_key in asset_classes.keys():
            llm_score = getattr(batched_scores, asset_key, None)
            keywords = asset_classes[asset_key].get('keywords', [])
            relevant = [n for n in all_news
                        if any(kw.lower() in n.get('title', '').lower() for kw in keywords)]
            news_count = len(relevant)

            if llm_score is not None and llm_score != 0:
                # LLM saw signal in the batch — primary source
                score = max(-40, min(40, int(llm_score)))   # materiality cap: a single day's headlines cannot justify extremes
            elif news_count > 0:
                # LLM silent but keyword coverage exists — deterministic fallback
                score = self._calculate_score_fallback(relevant)
            else:
                score = None   # NO DATA is not NEUTRAL

            """sentiments[asset_key] = {
                'score': score,
                'label': self._score_to_label(score),
                'news_count': news_count
            }"""
                        # ... if / elif / else sets score ...
            # Materiality cap on ALL paths (LLM and keyword fallback)
            if score is not None:
                score = max(-40, min(40, score))
            sentiments[asset_key] = {
                'score': score,
                'label': self._score_to_label(score),
                'news_count': news_count
            }

        if getattr(config, 'VERBOSE_LOGGING', False):
            print(f"🔍 [DEBUG] Asset sentiments being set: { {k: v['score'] for k, v in sentiments.items()} }")

        return sentiments
    
    def _build_regional_sentiments(self, all_news, batched_scores):
        """2A-4: Score EVERY region (prior indentation bug silently dropped any
        region where the LLM returned a non-zero score). Null — never 0 —
        when a region has no coverage."""
        regions = getattr(config, 'REGIONS', {})
        sentiments = {}

        for region_code, region_info in regions.items():
            field_name = REGION_FIELD_MAP.get(region_code)
            llm_score = getattr(batched_scores, field_name, None) if field_name else None
            keywords = region_info.get('keywords', [])
            region_name = region_info.get('name', region_code)

            relevant = [n for n in all_news
                        if region_name.lower() in (n.get('region_name', '') or '').lower()
                        or any(kw.lower() in n.get('title', '').lower() for kw in keywords)]
            news_count = len(relevant)

            if llm_score is not None and llm_score != 0:
                # LLM saw regional signal — primary source
                score = max(-40, min(40, int(llm_score)))   # materiality cap: a single day's headlines cannot justify extremes
            elif news_count > 0:
                # LLM silent but region-tagged news exists — deterministic fallback
                score = self._calculate_score_fallback(relevant)
            else:
                score = None   # NO DATA is not NEUTRAL

            """sentiments[region_code] = {
                'score': score,
                'label': self._score_to_label(score),
                'news_count': news_count
            }"""
            # ... if / elif / else sets score ...
            # Materiality cap on ALL paths (LLM and keyword fallback)
            if score is not None:
                score = max(-40, min(40, score))
            sentiments[region_code] = {
                'score': score,
                'label': self._score_to_label(score),
                'news_count': news_count
            }

        if getattr(config, 'VERBOSE_LOGGING', False):
            print(f"🔍 [DEBUG] Regional sentiments being set: { {k: v['score'] for k, v in sentiments.items()} }")

        return sentiments
    
    def _build_sub_class_sentiments(self, all_news, batched_scores):
        """2A-4: Score EVERY sub-class (prior indentation bug scored only the
        last sub-class per asset group). Null — never 0 — when no coverage."""
        sub_classes = getattr(config, 'SUB_CLASSES', {})
        sentiments = {}

        for asset_key, subs in sub_classes.items():
            for sub_name, sub_info in subs.items():
                field_name = SUB_CLASS_FIELD_MAP.get(sub_name)
                llm_score = getattr(batched_scores, field_name, None) if field_name else None
                keywords = sub_info.get('keywords', [])
                news_count = self._count_relevant_news(all_news, keywords)

                if llm_score is not None and llm_score != 0:
                    # LLM saw signal in the batch — primary source
                    score = max(-40, min(40, int(llm_score)))   # materiality cap: a single day's headlines cannot justify extremes
                elif news_count > 0:
                    # LLM silent but keyword coverage exists — deterministic fallback
                    relevant = [n for n in all_news
                                if any(kw.lower() in n.get('title', '').lower() for kw in keywords)]
                    score = self._calculate_score_fallback(relevant)
                else:
                    score = None  # NO DATA is not NEUTRAL

                """sentiments[sub_name] = {
                    'score': score,
                    'label': self._score_to_label(score),
                    'news_count': news_count
                }"""

            # ... if / elif / else sets score ...
            # Materiality cap on ALL paths (LLM and keyword fallback)
            if score is not None:
                score = max(-40, min(40, score))
            sentiments[sub_name] = {
                'score': score,
                'label': self._score_to_label(score),
                'news_count': news_count
            }
        return sentiments
    
    def _count_relevant_news(self, all_news, keywords):
        """Count news articles matching any of the keywords."""
        if not keywords:
            return 0
        
        count = 0
        for n in all_news:
            title_lower = n.get('title', '').lower()
            if any(kw.lower() in title_lower for kw in keywords):
                count += 1
        return count

    def _calculate_score_fallback(self, news_list):
        """Keyword-based fallback scoring when LLM is unavailable.
        Word-boundary matching (no substring false positives), capped at ±40
        to stay within the same materiality bound as the LLM path."""
        if not news_list:
            return 0

        pos_words = ['rally', 'rallies', 'rallied', 'surge', 'surges', 'surged', 'surging',
                     'gain', 'gains', 'gained', 'growth', 'rise', 'rises', 'rose', 'rising',
                     'bullish', 'record high', 'strong', 'beat', 'beats', 'upgrade', 'upgraded',
                     'recovery', 'optimism', 'profit', 'profits', 'outperform', 'outperformed',
                     'breakout', 'momentum', 'boost', 'boosted', 'soar', 'soars', 'soared',
                     'jump', 'jumps', 'jumped', 'rate cut', 'cuts rates']
        neg_words = ['crash', 'crashes', 'crashed', 'fall', 'falls', 'fell', 'falling',
                     'drop', 'drops', 'dropped', 'decline', 'declines', 'declined', 'bearish',
                     'recession', 'weak', 'weaker', 'weaken', 'miss', 'misses', 'missed',
                     'downgrade', 'downgraded', 'crisis', 'fear', 'fears', 'loss', 'losses',
                     'underperform', 'underperformed', 'selloff', 'sell-off', 'plunge', 'plunges',
                     'plunged', 'slump', 'slumps', 'slumped', 'tumble', 'tumbles', 'tumbled',
                     'warning', 'warnings', 'warned', 'inflation surge', 'rate hike', 'hikes rates']

        pos_patterns = [re.compile(r'\b' + re.escape(w) + r'\b') for w in pos_words]
        neg_patterns = [re.compile(r'\b' + re.escape(w) + r'\b') for w in neg_words]

        pos_count = 0
        neg_count = 0
        for news in news_list:
            title_lower = news.get('title', '').lower()
            pos_count += sum(1 for p in pos_patterns if p.search(title_lower))
            neg_count += sum(1 for p in neg_patterns if p.search(title_lower))

        total = pos_count + neg_count
        if total == 0:
            return 0

        raw_score = ((pos_count - neg_count) / total) * 100
        return max(-40, min(40, int(raw_score * 0.7)))   # capped to match LLM-path materiality bound
    
    def _score_to_label(self, score):
        if score is None: return 'Insufficient Data' 
        if score >= 40: return 'Bullish'
        if score >= 15: return 'Slightly Positive'
        if score >= 0: return 'Neutral'
        if score >= -15: return 'Slightly Negative'
        if score >= -40: return 'Bearish'
        return 'Very Bearish'

    # Class-level noise filter (Nasdaq admin notices carry no market signal)
    
    # Class-level noise filter — canonical list, mirrored in html_report_generator
    NOISE_PATTERNS = ['delisting', 'listing of', 'notices', 'circuit breaker',
                    'change in the amount', 'new strikes', 'mini futures',
                    'leverage certificates', 'warrants', 'certificates',
                    'admitted to trading', 'adjustment in', 'suspension of trading',
                    'monthly report', 'membership change', 'expiration value',
                    'pledged as collateral', 'record id',
                    # crime / lifestyle / consumer junk
                    'hidden camera', 'rape', 'stabbing', 'knivstikkeri', 'nabostridighed',
                    'fængsel', 'idømt', 'terrorhandling', 'offender tracking', 'care home warden',
                    'frat part', 'comedian', 'poesi', 'digter', 'skibsvrag',
                    'book a flight', 'with points', 'debt settlement', 'debt forgiveness',
                    'familiebiler', 'trapped in lifts', 'minibus', 'motorregistret',
                    'flash step', 'voter roll',
                    # advice/clickbait that creates phantom causal signals
                    'how to profit', 'buy recommendations', 'risk-adjusted upside']

    def _analyze_impacts(self, all_news):
        """Per-news causal impact analysis (requirements 1-4). BOUNDED RUNTIME:
        max 30 headlines, 2 batches of 15, FAST model, hard token cap."""
        meaningful = [n for n in all_news
                        if not any(p in n.get('title', '').lower() for p in self.NOISE_PATTERNS)]

        # Bounded input: 30 headlines -> exactly 2 batches -> exactly 2 LLM calls
        meaningful = meaningful[:30]
        #batches = [meaningful[i:i+15] for i in range(0, len(meaningful), 15)]
        batches = [meaningful[i:i+5] for i in range(0, len(meaningful), 5)]

        system = """You are a cross-asset impact analyst. Headlines are numbered 0..N-1.
    For EACH headline that moves markets, output one record:
    {"idx": <number>, "relevant": true, "se_score": <-100..100>, "se_why": "<=10 words",
    "impacts": [{"segment": "...", "sub_class": "...", "region": "...", "score": <-100..100>, "timing": "immediate|days|weeks", "why": "<=10 words"}]}
    Rules:
    - idx MUST match the headline number exactly. Do NOT repeat the headline text.
    - A headline may be NEGATIVE for one segment and POSITIVE for another: emit BOTH impacts.
    - Only include segments actually affected; irrelevant headline => relevant=false, empty impacts.
    - segment in: stocks,bonds,forex,crypto,bullion,volatility,funds
    - sub_class (optional) in: US Stocks,EU Stocks,Asia Stocks,Nordic Stocks,Government Bonds,Yield Curve,Major FX,Nordic FX,EM FX,Large Cap Crypto,Mid Cap Crypto,Meme & Alt,ETFs,Active Funds,Gold,Silver
    - region (optional) in: US,EU,JP,CN,Nordics,DK,SE
    - se_score = net impact on the SWEDISH market (SEK, exporters, global risk); 0 if none.
    - Keep every why under 10 words.
    - If a headline hurts one segment and helps another, emit BOTH impacts and prefer DIFFERENT segments where true (e.g., stocks -30 AND bonds +20), not two effects inside the same segment.
    - Every impact with score != 0 MUST carry timing: "immediate", "days", or "weeks". Never omit timing.
    - In "why" and "headline" fields NEVER use double-quote characters; use single quotes (') instead to prevent JSON breakage.
    - Respond in English ONLY. Never use characters from any other language.
    Output ONLY: {"records":[...]}"""

        records = []
        for b_idx, batch in enumerate(batches, 1):
            self.log(f"  Impact batch {b_idx}/{len(batches)} ({len(batch)} headlines, FAST model)...", 'INFO')
            lines = "\n".join(f"{i}. {self._clean_title(n.get('title', ''))}" for i, n in enumerate(batch))

            out = None
            attempts = [
                ('fast', system),
                ('fast', system + "\n\nCRITICAL RETRY: Your previous output was invalid JSON. Output ONLY valid JSON. Absolutely NO double-quote characters inside string values."),
                ('deep', system + "\n\nCRITICAL FINAL ATTEMPT: Output ONLY a valid JSON object matching the schema. No prose, no markdown, no double quotes inside strings."),
            ]
            for attempt, (tier, active_system) in enumerate(attempts, 1):
                try:
                    raw = self.model_router.generate_text(
                        prompt=f"Headlines:\n{lines}\n\nRespond with ONLY the JSON object.",
                        system_prompt=active_system,
                        task_type=tier)
                    parsed = self.model_router._extract_json(raw) if raw else None
                    if parsed and isinstance(parsed, dict) and 'records' in parsed:
                        out = ImpactBatch(**parsed)
                        if out.records:
                            self.log(f"  Batch {b_idx}: {len(out.records)} records parsed (attempt {attempt}, {tier}).", 'INFO')
                            break
                        out = None
                    else:
                        self.log(f"  Batch {b_idx}: extraction failed on attempt {attempt} ({tier}).", 'WARN')
                except Exception as e:
                    self.log(f"  Batch {b_idx}: exception on attempt {attempt} ({tier}): {str(e)[:60]}.", 'WARN')
            if out is None:
                self.log(f"  Batch {b_idx}: no parseable JSON after 3 attempts; skipping.", 'WARN')

            if out:
                for rec in out.records:
                    if 0 <= rec.idx < len(batch):
                        rec.headline = batch[rec.idx].get('title', '')
                records.extend(out.records)
            #else:
            #    self.log(f"  Batch {b_idx}: no parseable JSON after 2 attempts; skipping.", 'WARN')

        
        self.log(f"Impact analysis complete: {len(records)} impact records.", 'SUCCESS')
        # Sprint 2B phase-1 guardrails (deterministic, no LLM involved):
        #  (a) strip non-ASCII from rationale text -> imp.why and rec.se_why
        #      (the old code targeted rec.why, which does not exist on NewsImpact)
        #  (b) cap any single-headline impact at +/-40 (materiality bound)
        MAX_SINGLE_IMPACT = 40
        for rec in records:
            if getattr(rec, 'se_why', ''):
                rec.se_why = re.sub(r'[^\x00-\x7F]+', '', rec.se_why).strip()
            if getattr(rec, 'se_score', 0):
                rec.se_score = max(-MAX_SINGLE_IMPACT, min(MAX_SINGLE_IMPACT, int(rec.se_score)))
            for imp in getattr(rec, 'impacts', []):
                if getattr(imp, 'why', ''):
                    imp.why = re.sub(r'[^\x00-\x7F]+', '', imp.why).strip()
                if getattr(imp, 'score', 0):
                    imp.score = max(-MAX_SINGLE_IMPACT, min(MAX_SINGLE_IMPACT, int(imp.score)))
        return self._aggregate_impacts(records)
    
    #def _analyze_impacts(self, all_news):
    #    """Per-news causal impact analysis (requirements 1-4)."""
    #    # Pre-filter noise, cap batches to bound runtime
    #    meaningful = [n for n in all_news
    #                if not any(p in n.get('title', '').lower() for p in self.NOISE_PATTERNS)]
    #    batches = [meaningful[i:i+12] for i in range(0, min(len(meaningful), 72), 12)]

        system = """You are a cross-asset impact analyst. For EACH headline decide which market
    segments it moves, in which direction, and when.
    Rules:
    - A headline can be NEGATIVE for one segment and POSITIVE for another. Emit BOTH as separate impacts, each with its own 'why'.
    - score: -100..+100 for THAT segment (0 = no effect).
    - timing: "immediate" | "days" | "weeks".
    - segment in: stocks,bonds,forex,crypto,bullion,volatility,funds.
    - sub_class (optional) in: US Stocks,EU Stocks,Asia Stocks,Nordic Stocks,Government Bonds,Yield Curve,Major FX,Nordic FX,EM FX,Large Cap Crypto,Mid Cap Crypto,Meme & Alt,ETFs,Active Funds,Gold,Silver.
    - region (optional) in: US,EU,JP,CN,Nordics,DK,SE.
    - se_score: net impact on the SWEDISH market; se_why explains transmission (SEK, exporters, global risk).
    - Administrative noise => relevant=false, empty impacts.
    Output ONLY JSON: {"records":[...]}"""

    #    records = []
    #   for batch in batches:
    #        lines = "\n".join(f"- {n.get('title','')}" for n in batch)
    #        out = self.model_router.generate_structured_output(
    #            prompt=f"Headlines:\n{lines}", system_prompt=system,
    #            schema=ImpactBatch, task_type='deep')
    #        if out:
    #            records.extend(out.records)
    #    return self._aggregate_impacts(records)

    def _reconcile_scores(self, asset_sentiments, impact_analysis):
        """
        P1-3: One reproducible sentiment reading from evidenced buckets only.
        Returns (canonical_score, audit_dict). No LLM-generated numeric field
        survives this function.

        Design assumptions (tunable, NOT calibrated predictors):
          - tone weight 0.60, causal-pressure weight 0.40
          - bucket weight capped at 10 headlines so a crowded bucket cannot dominate
          - volatility excluded: it is a risk state, not a directional view
          - no coverage => None, never 0
        """
        TONE_WEIGHT = 0.60
        PRESSURE_WEIGHT = 0.40
        MAX_BUCKET_WEIGHT = 10

        # --- 1. Coverage-weighted tone: evidenced buckets ONLY ---
        tone_num = tone_den = 0.0
        tone_parts = {}
        for name, entry in (asset_sentiments or {}).items():
            if not isinstance(entry, dict):
                continue
            score = entry.get('score')
            count = entry.get('news_count') or 0
            if score is None or not isinstance(score, (int, float)) or count <= 0:
                continue                      # NO DATA is not NEUTRAL
            w = min(float(count), MAX_BUCKET_WEIGHT)
            tone_num += float(score) * w
            tone_den += w
            tone_parts[name] = {'score': score, 'n': count, 'weight': w}
        tone = round(tone_num / tone_den) if tone_den else None

        # --- 2. Causal pressure: already weighted-averaged by P1-2 ---
        cat = (impact_analysis or {}).get('category_impact', {}) or {}
        pres_num = pres_den = 0.0
        pres_parts = {}
        for seg, score in cat.items():
            if str(seg).lower() == 'volatility':
                continue                      # risk state, not direction
            if score is None or not isinstance(score, (int, float)):
                continue
            pres_num += float(score)
            pres_den += 1
            pres_parts[seg] = score
        pressure = round(pres_num / pres_den) if pres_den else None

        # --- 3. Canonical reading ---
        if tone is not None and pressure is not None:
            canonical = round(TONE_WEIGHT * tone + PRESSURE_WEIGHT * pressure)
        elif tone is not None:
            canonical = tone
        elif pressure is not None:
            canonical = pressure
        else:
            canonical = None

        if canonical is not None:
            canonical = max(-100, min(100, int(canonical)))

        return canonical, {
            'tone_score': tone,
            'pressure_score': pressure,
            'canonical_score': canonical,
            'tone_components': tone_parts,
            'pressure_components': pres_parts,
            'tone_weight': TONE_WEIGHT,
            'pressure_weight': PRESSURE_WEIGHT,
            'method': 'coverage_weighted_tone_60_causal_pressure_40',
        }

    def _aggregate_impacts(self, records):
        """P1-2: Weighted average aggregation instead of clipped sum.
        Tracks counts and returns null for insufficient data."""
        # Track sums AND counts for weighted averaging
        cat_sum, cat_count = {}, {}
        sub_sum, sub_count = {}, {}
        reg_sum, reg_count = {}, {}
        opposing, delayed, se_sub_sum, se_sub_count = [], [], {}, {}
        se_total, se_n = 0, 0

        valid_subs = set()
        for subs in getattr(config, 'SUB_CLASSES', {}).values():
            valid_subs.update(subs.keys())

        for rec in records:
            if not rec.relevant:
                continue
            dirs = [i.score for i in rec.impacts if i.score != 0]
            # Req 2: opposing directions across segments
            if any(d > 0 for d in dirs) and any(d < 0 for d in dirs):
                opposing.append({
                    'headline': rec.headline,
                    'effects': [{'segment': i.segment, 'score': i.score, 'why': i.why}
                                for i in rec.impacts if i.score != 0]})
            for imp in rec.impacts:
                if imp.score == 0:
                    continue
                # Category aggregation (weighted average)
                cat_sum[imp.segment] = cat_sum.get(imp.segment, 0) + imp.score
                cat_count[imp.segment] = cat_count.get(imp.segment, 0) + 1
                
                if imp.sub_class:
                    sub_sum[imp.sub_class] = sub_sum.get(imp.sub_class, 0) + imp.score
                    sub_count[imp.sub_class] = sub_count.get(imp.sub_class, 0) + 1
                
                if imp.region:
                    reg_sum[imp.region] = reg_sum.get(imp.region, 0) + imp.score
                    reg_count[imp.region] = reg_count.get(imp.region, 0) + 1
                
                # Req 3: forward-looking
                if imp.timing in ('days', 'weeks'):
                    delayed.append({'headline': rec.headline, 'segment': imp.segment,
                                    'score': imp.score, 'timing': imp.timing, 'why': imp.why})
                
                # Req 4: Sweden sub-class transmission (hygiene-filtered)
                if imp.region == 'SE' or imp.sub_class in ('Nordic Stocks', 'Nordic FX'):
                    sub_key = imp.sub_class if imp.sub_class in valid_subs else None
                    if sub_key and imp.region == 'SE' and sub_key.startswith(('US ', 'EU ', 'Asia ')):
                        sub_key = None  # region-inconsistent mislabel
                    if sub_key:
                        se_sub_sum[sub_key] = se_sub_sum.get(sub_key, 0) + imp.score
                        se_sub_count[sub_key] = se_sub_count.get(sub_key, 0) + 1
            
            if rec.se_score != 0:
                se_total += rec.se_score
                se_n += 1

        # Compute weighted averages; return null if insufficient data (< 2 headlines)
        MIN_HEADLINES = 2
        cat = {k: round(cat_sum[k] / cat_count[k]) if cat_count[k] >= MIN_HEADLINES else None 
               for k in cat_sum}
        sub = {k: round(sub_sum[k] / sub_count[k]) if sub_count[k] >= MIN_HEADLINES else None 
               for k in sub_sum}
        reg = {k: round(reg_sum[k] / reg_count[k]) if reg_count[k] >= MIN_HEADLINES else None 
               for k in reg_sum}
        se_sub = {k: round(se_sub_sum[k] / se_sub_count[k]) if se_sub_count[k] >= MIN_HEADLINES else None 
                  for k in se_sub_sum}
        
        # Compute overall SE impact (weighted average of se_scores)
        se_overall = round(se_total / se_n) if se_n >= MIN_HEADLINES else None

        clamp = lambda v: max(-100, min(100, v))
        return {
            'category_impact': cat,
            'sub_class_impact': sub,
            'regional_impact': reg,
            'opposing_impacts': opposing,
            'delayed_impacts': delayed,
            'se_impact': {'overall': se_overall, 'by_sub_class': se_sub},
            '_method': 'weighted_average',  # For debugging
            '_min_headlines': MIN_HEADLINES
        }

    def _clean_title(self, title):
        """Neutralize smart quotes/newlines/non-ASCII that can trip JSON grammar decoding."""
        for bad, good in {'\u2018': "'", '\u2019': "'", '\u201c': '"', '\u201d': '"',
                          '\u2013': '-', '\u2014': '-', '\u2026': '...'}.items():
            title = title.replace(bad, good)
        title = title.replace('\n', ' ').replace('\r', ' ')
        title = title.encode('ascii', 'ignore').decode('ascii')
        return ' '.join(title.split())[:90]
    