"""
Micro Agent - Analyzes microeconomic and company-specific impacts.
"""
from agents.base_agent import BaseAgent

class MicroAgent(BaseAgent):
    def __init__(self, model_router=None, vector_db=None):
        super().__init__('MicroAgent', model_router, vector_db)

    def execute(self, all_news, market_summary):
        if not self.validate_input({'all_news': all_news}):
            return None

        news_context = "\n".join([f"- {n.get('title', '')}" for n in all_news[:20]])
        system_prompt = (
            "You are a disciplined equity research analyst focusing on microeconomic factors. "
            "You write institutional research notes: factual, concise, and grounded ONLY in the provided data."
        )
        user_prompt = (
            f"MARKET SUMMARY:\n{market_summary}\n\n"
            f"NEWS HEADLINES:\n{news_context}\n\n"
            "TASK: Identify the genuine MICROECONOMIC themes in these headlines "
            "(labor market shifts, supply chains, regulation, corporate actions, margins, sector structure). "
            "For each theme output exactly this structure:\n"
            "THEME: <short name>\n"
            "DRIVER: <which headline(s)>\n"
            "AFFECTED: <companies/sectors>\n"
            "IMPACT: <direction and mechanism, one sentence>\n\n"
            "STRICT RULES:\n"
            "1. IGNORE headlines with no financial relevance (crime, sports, lifestyle, entertainment, weather, celebrity, collectibles).\n"
            "2. Do NOT give investment advice or recommendations, and never say what investors 'should' do. You are an analyst, not an advisor.\n"
            "3. Do NOT use markdown symbols (no #, *, **, ###). Plain text only, using the structure above.\n"
            "4. Do NOT pad the analysis, do NOT restate the market summary, and do NOT invent themes. If only 3 themes are genuinely present, output only 3.\n"
            "5. Every claim must trace to a specific headline listed above."
        )

        self.log("Analyzing microeconomic impacts...")
        raw_analysis = self.model_router.generate_text(prompt=user_prompt, system_prompt=system_prompt, task_type='deep')

        return {'raw_analysis': raw_analysis if raw_analysis else "No microeconomic analysis available."}