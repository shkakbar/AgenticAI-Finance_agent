"""
News Tagger - LLM re-classification of headlines stuck in the 'Other' bucket.
Reduces the catch-all category so Correlation/Micro/Sector agents get real signal.
Pattern: idx-mapping + free-text JSON + 3-tier retry ladder (fast/fast-strict/deep).
"""
from schemas import NewsTagBatch


class NewsTagger:
    BATCH_SIZE = 25
    MAX_HEADLINES = 200

    ASSET_KEYS = ['stocks', 'bonds', 'forex', 'crypto', 'bullion',
                  'volatility', 'funds', 'macro']
    
    ASSET_ALIASES = {
        # Core singular/plural normalization
        'stock': 'stocks', 'equities': 'stocks', 'equity': 'stocks',
        'bond': 'bonds',
        'gold': 'bullion', 'silver': 'bullion',
        'fx': 'forex', 'currencies': 'forex',
        'vix': 'volatility', 'derivatives': 'volatility', 'options': 'volatility',
        # Sector/synonym → canonical buckets (observed FAST-model outputs)
        'banks': 'stocks', 'banking': 'stocks',
        'tech': 'stocks', 'technology': 'stocks', 'technological': 'stocks',
        'telecoms': 'stocks', 'telecom': 'stocks',
        'real_estate': 'stocks',
        'analyst calls': 'stocks', 'analyst call': 'stocks',
        # Macro-family
        'macroeconomic': 'macro', 'macroeconomics': 'macro',
        'geopolitics': 'macro', 'geopolitical': 'macro', 'geo-political': 'macro',
        'geo': 'macro', 'politics': 'macro',
        # Energy/commodity family
        'oil': 'macro', 'energy': 'macro',
        'commodity': 'oil_and_commodities', 'commodities': 'oil_and_commodities',
        'oil and commodities': 'oil_and_commodities',
    }

    @staticmethod
    def _headline(n):
        """Extract headline text from whatever shape the news bucket stores."""
        if isinstance(n, str):
            return n
        if isinstance(n, dict):
            # Handle the nested structure from the keyword tagger: {'news': {'title': ...}, 'score': ..., 'label': ...}
            if 'news' in n and isinstance(n['news'], dict):
                return n['news'].get('title') or n['news'].get('headline') or ''
            # Fallback to top-level keys (just in case)
            return n.get('title') or n.get('headline') or n.get('text') or n.get('name') or ''
        return ''

    SYSTEM = """You are a financial news classifier for a market intelligence platform.
Most headlines in a financial news feed ARE market-relevant. Classify each numbered headline into EXACTLY one category:
- stocks: companies, earnings, equity markets, sectors, IPOs, analyst calls (e.g., 'PepsiCo cuts earnings forecast', 'Zealand-aktien dykker: Analytiker nedjusterer')
- bonds: government/corporate debt, yields, credit markets (e.g., 'French bond sell-off prompts bottom fishing')
- forex: currencies, exchange rates (e.g., 'Kronan weakens against the euro')
- crypto: digital assets, blockchain (e.g., 'Bitcoin rallies amid ETF inflows')
- bullion: gold, silver, precious metals
- volatility: VIX, options activity, market stress
- funds: ETFs, mutual funds, fund flows, asset managers
- macro: central banks, interest rates, inflation, GDP, jobs, fiscal policy, geopolitics, oil and commodities (e.g., 'Fed officials see another hike coming', 'Thedéen: Starka skäl att höja räntan', 'Oil prices jump on tanker attacks')
- other: ONLY clearly non-financial news — crime, sports, culture, weather, lifestyle (e.g., '43-årig mand varetægtsfængslet i drabssag', 'Makreltuber tilbagekaldes')
Rules:
- idx MUST match the headline number.
- Headlines may be in English, Swedish, Danish, or Chinese — classify by meaning, not language.
- When uncertain between two financial categories, pick the CLOSEST financial one. Use 'other' ONLY when the headline has no plausible market relevance.
- In a typical news feed, MOST headlines map to stocks or macro. If you find yourself tagging everything as 'other', your classifications are wrong.
- Never use double-quote characters inside string values.
Output ONLY JSON: {"tags":[{"idx":0,"asset":"stocks"},...]}"""

    def __init__(self, model_router):
        self.model_router = model_router

    def retag(self, news_by_asset):
        """Re-classify 'Other' headlines. Returns (new_news_by_asset, moved_count)."""
        other_key = 'Other' if 'Other' in news_by_asset else ('other' if 'other' in news_by_asset else None)
        if other_key is None:
            return news_by_asset, 0
        others = news_by_asset.get(other_key, [])
        if not others:
            return news_by_asset, 0

        candidates = others[:self.MAX_HEADLINES]
        leftover = others[self.MAX_HEADLINES:]
        batches = [candidates[i:i + self.BATCH_SIZE] for i in range(0, len(candidates), self.BATCH_SIZE)]

        assign = {}  # position within candidates -> asset
        print(f"  ℹ️ [NewsTagger] Found {len(candidates)} headlines in '{other_key}'. Processing in {len(batches)} batches...")
        for b_idx, batch in enumerate(batches, 1):
            b_start = (b_idx - 1) * self.BATCH_SIZE
            lines = "\n".join(f"{i}. {self._headline(n)}" for i, n in enumerate(batch))
            print(f"  ℹ️ [NewsTagger]   Batch {b_idx}/{len(batches)} ({len(batch)} headlines)... e.g. '{self._headline(batch[0])[:70]}'")
            out = None
            
            for attempt, tier in ((1, 'fast'), (2, 'fast'), (3, 'deep')):
                try:
                    system = self.SYSTEM if attempt == 1 else (
                        self.SYSTEM + "\n\nCRITICAL RETRY: Output ONLY valid JSON. "
                                      "No prose, no markdown, no double quotes inside strings.")
                    raw = self.model_router.generate_text(
                        prompt=f"Headlines:\n{lines}\n\nRespond with ONLY the JSON object.",
                        system_prompt=system,
                        task_type=tier)
                    parsed = self.model_router._extract_json(raw) if raw else None
                    
                    if parsed and isinstance(parsed, dict) and 'tags' in parsed:
                        out = NewsTagBatch(**parsed)
                        print(f"  ℹ️ [NewsTagger]     -> Parsed {len(out.tags)} tags on attempt {attempt} ({tier}).")
                        break
                    else:
                        print(f"  ⚠️ [NewsTagger]     -> Extraction failed on attempt {attempt} ({tier}). Raw head: {repr(raw[:80]) if raw else 'None'}")
                except Exception as e:
                    print(f"  ⚠️ [NewsTagger]     -> Exception on attempt {attempt} ({tier}): {str(e)[:60]}")
                    
            if out is None:
                print(f"  ⚠️ [NewsTagger]   Batch {b_idx}: LLM extraction failed on all attempts.")
                continue
            
            # Debug: show what the LLM actually decided
            assigned_assets = [t.asset for t in out.tags if 0 <= t.idx < len(batch)]
            print(f"  ℹ️ [NewsTagger]   Batch {b_idx} LLM assignments: {assigned_assets}")
            
            for t in out.tags:
                if 0 <= t.idx < len(batch):
                    asset = self.ASSET_ALIASES.get(t.asset, t.asset)
                    if asset in self.ASSET_KEYS:
                        assign[b_start + t.idx] = asset

        added = {k: [] for k in self.ASSET_KEYS}
        new_other = []
        for pos, n in enumerate(candidates):
            a = assign.get(pos)
            if a:
                added[a].append(n)
            else:
                new_other.append(n)

        new_by_asset = {k: list(v) for k, v in news_by_asset.items()}
        new_by_asset[other_key] = new_other + leftover
        moved = 0
        for a, items in added.items():
            if items:
                new_by_asset.setdefault(a, [])
                new_by_asset[a].extend(items)
                moved += len(items)

        if moved == 0 and len(candidates) > 20:
            print("  ⚠️ [NewsTagger] Zero re-classifications — model may be defaulting to 'other'.")

        return new_by_asset, moved