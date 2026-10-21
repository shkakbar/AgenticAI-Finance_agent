"""
Macro Agent - Analyzes macroeconomic impact with regional deep-dive.
"""
from agents.base_agent import BaseAgent
from schemas import RegionalDeepDive

class MacroAgent(BaseAgent):
    def __init__(self, model_router=None, vector_db=None):
        super().__init__('MacroAgent', model_router, vector_db)

    def execute(self, all_news, market_summary):
        if not self.validate_input({'all_news': all_news, 'market_summary': market_summary}):
            return None

        """
        news_context = "\n".join([f"- {n.get('title', '')}" for n in all_news[:30]])
        system_prompt = "You are a global macroeconomist. Output strict JSON."
        user_prompt = f"MARKET SUMMARY:\n{market_summary}\n\nNEWS HEADLINES:\n{news_context}"
        """

        # ── Phase 5a: region-balanced news selection ──
        # The old all_news[:30] slice was dominated by US/EU wire copy, starving the
        # Sweden outlook. Bucket Swedish/Nordic items first, then fill with global news.
        sweden_news, other_news = [], []
        for n in all_news:
            region = str(n.get('region') or n.get('country') or '').lower()
            source = str(n.get('source') or '').lower()
            is_sweden = region in ('sweden', 'sverige', 'se')
            is_nordic = region in ('denmark', 'norway', 'finland', 'nordic countries', 'nordics', 'dk', 'no', 'fi')
            is_se_source = any(s in source for s in ('finanswatch', 'di.se', 'dagens industri', 'placera'))
            if is_sweden or is_se_source or is_nordic:
                sweden_news.append(n)
            else:
                other_news.append(n)

        se_block, global_block = sweden_news[:12], other_news[:18]
        sweden_context = "\n".join([f"- {n.get('title', '')}" for n in se_block]) or "- (no Sweden-specific headlines today)"
        global_context = "\n".join([f"- {n.get('title', '')}" for n in global_block])
        self.log(f"News split: {len(sweden_news)} Sweden/Nordic, {len(other_news)} global", 'INFO')

        system_prompt = (
            "You are a global macroeconomist writing an institutional research note. Output strict JSON. "
            "GROUNDING RULES: "
            "1. The SWEDISH & NORDIC NEWS section MUST inform sweden_outlook. If it contains items, reference the specific companies, sectors, or labor-market events named there. "
            "2. If there are genuinely no Sweden-specific items, state that plainly. Never invent Swedish data. "
            "3. Every claim must trace to a headline in the inputs or a figure in MARKET SUMMARY. Never invent indicators, figures, or events. "
            "4. No investment advice. Dry, analytical, institutional tone."
        )
        user_prompt = (
            f"MARKET SUMMARY:\n{market_summary}\n\n"
            f"SWEDISH & NORDIC NEWS ({len(se_block)} items):\n{sweden_context}\n\n"
            f"GLOBAL NEWS ({len(global_block)} items):\n{global_context}"
        )

        self.log("Generating US & Sweden Regional Deep-Dive [DEEP model + JSON]...")
        regional_dive = self.model_router.generate_structured_output(
            prompt=user_prompt, system_prompt=system_prompt, schema=RegionalDeepDive, task_type='deep'
        )

        raw_text = f"US OUTLOOK: {regional_dive.us_outlook}\n\nSWEDEN OUTLOOK: {regional_dive.sweden_outlook}\n\nCROSS-BORDER IMPACT: {regional_dive.cross_border_impact}\n\nKEY DIFFERENTIAL: {regional_dive.key_differential}"

        return {
            'raw_analysis': raw_text,
            'regional_deep_dive': regional_dive.model_dump()
        }