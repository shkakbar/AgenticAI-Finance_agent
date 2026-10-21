"""
Pydantic Schemas for Structured AI Outputs (OPT-1).
Enforces strict JSON formatting and auto-corrects LLM scale/type errors.
All fields have defaults so partial responses don't crash the pipeline.
"""
from pydantic import BaseModel, Field, field_validator, model_validator
from typing import List, Optional

class TimeHorizonSentiment(BaseModel):
    """Schema for AI-SENT-1: Time-Horizon Sentiment Splicing"""
    current_sentiment_score: float = Field(default=0, ge=-100.0, le=100.0)
    current_label: str = "Neutral"

    overall_trend_score: float = Field(default=0, ge=-100.0, le=100.0)
    overall_label: str = "Neutral"

    short_term_outlook: str = "No data available."
    medium_term_outlook: str = "No data available."
    long_term_outlook: str = "No data available."

    confidence_score: float = Field(default=0.5, ge=0.0, le=1.0)
    key_drivers: List[str] = Field(default_factory=list)

    @field_validator('current_sentiment_score', 'overall_trend_score', mode='before')
    @classmethod
    def normalize_sentiment_score(cls, v):
        """Auto-corrects if the LLM uses a -1.0 to 1.0 scale instead of -100 to 100."""
        try:
            v = float(v)
            if -1.0 <= v <= 1.0:
                return int(v * 100)
            return int(v)
        except (ValueError, TypeError):
            return 0

    @field_validator('confidence_score', mode='before')
    @classmethod
    def normalize_confidence(cls, v):
        """Ensures confidence is a float between 0 and 1."""
        try:
            v = float(v)
            if v > 1.0:
                return min(v / 100.0, 1.0)
            return max(v, 0.0)
        except (ValueError, TypeError):
            return 0.5

    @field_validator('key_drivers', mode='before')
    @classmethod
    def ensure_list(cls, v):
        if isinstance(v, str):
            return [v]
        if isinstance(v, list):
            return [str(item) for item in v]
        return []

class ConsolidatedMarketView(BaseModel):
    """Schema for AI-SENT-2: Deep Consolidated Sentiment View"""
    executive_summary: str = "No consolidated view available."
    price_action_synthesis: str = "No data available."
    macro_synthesis: str = "No data available."
    bottom_line: str = "No data available."

    @field_validator('executive_summary', 'price_action_synthesis', 'macro_synthesis', 'bottom_line', mode='before')
    @classmethod
    def ensure_string(cls, v):
        if v is None:
            return "No data available."
        return str(v)

class RegionalDeepDive(BaseModel):
    """Schema for AI-REG-1: US & Sweden Deep-Dive Focus"""
    us_outlook: str = "No data available."
    sweden_outlook: str = "No data available."
    cross_border_impact: str = "No data available."
    key_differential: str = "No data available."

    @field_validator('us_outlook', 'sweden_outlook', 'cross_border_impact', 'key_differential', mode='before')
    @classmethod
    def ensure_string(cls, v):
        if v is None:
            return "No data available."
        return str(v)


class SegmentImpact(BaseModel):
    """Impact of ONE headline on ONE segment."""
    segment: str = ""                                   # stocks|bonds|forex|crypto|bullion|volatility|funds
    sub_class: str = ""                                 # e.g. Nordic Stocks, Government Bonds
    region: str = ""                                    # US|EU|JP|CN|Nordics|DK|SE
    score: int = Field(default=0, ge=-100, le=100)      # signed impact on THIS segment
    timing: str = "immediate"                           # immediate|days|weeks
    why: str = ""

class NewsImpact(BaseModel):
    """Impact record for ONE headline."""
    idx: int = -1                                       # 0-based index of headline in batch
    headline: str = ""
    relevant: bool = True
    impacts: List[SegmentImpact] = Field(default_factory=list)
    se_score: int = Field(default=0, ge=-100, le=100)   # net impact on Sweden market
    se_why: str = ""

class ImpactBatch(BaseModel):
    records: List[NewsImpact] = Field(default_factory=list)

    @model_validator(mode='before')
    @classmethod
    def salvage_records(cls, data):
        """Drop malformed records/impacts instead of failing the whole batch."""
        if not isinstance(data, dict):
            return data
        raw = data.get('records', [])
        clean = []
        if isinstance(raw, list):
            for rec in raw:
                if not isinstance(rec, dict):
                    continue
                impacts = []
                raw_imps = rec.get('impacts', [])
                if isinstance(raw_imps, list):
                    for imp in raw_imps:
                        if isinstance(imp, dict) and isinstance(imp.get('segment'), str):
                            try:
                                imp['score'] = max(-100, min(100, int(imp.get('score', 0))))
                            except Exception:
                                imp['score'] = 0
                            impacts.append(imp)
                rec['impacts'] = impacts
                clean.append(rec)
        data['records'] = clean
        return data

    
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict
from typing import Any, Dict

class BatchedCategorySentiments(BaseModel):
    """LLM-generated sentiment scores across all categories in one call.
    Handles multiple field name formats and nested structures automatically."""
    
    model_config = ConfigDict(
        populate_by_name=True,
        extra='allow',
        str_strip_whitespace=True
    )
    
    # Asset classes
    stocks: int = Field(default=0, ge=-100, le=100)
    bonds: int = Field(default=0, ge=-100, le=100)
    forex: int = Field(default=0, ge=-100, le=100)
    crypto: int = Field(default=0, ge=-100, le=100)
    funds: int = Field(default=0, ge=-100, le=100)
    bullion: int = Field(default=0, ge=-100, le=100)
    volatility: int = Field(default=0, ge=-100, le=100)
    
    # Regions
    region_US: int = Field(default=0, ge=-100, le=100)
    region_EU: int = Field(default=0, ge=-100, le=100)
    region_JP: int = Field(default=0, ge=-100, le=100)
    region_CN: int = Field(default=0, ge=-100, le=100)
    region_Nordics: int = Field(default=0, ge=-100, le=100)
    region_DK: int = Field(default=0, ge=-100, le=100)
    region_SE: int = Field(default=0, ge=-100, le=100)
    
    # Sub-classes
    sub_US_Stocks: int = Field(default=0, ge=-100, le=100)
    sub_EU_Stocks: int = Field(default=0, ge=-100, le=100)
    sub_Asia_Stocks: int = Field(default=0, ge=-100, le=100)
    sub_Nordic_Stocks: int = Field(default=0, ge=-100, le=100)
    sub_Gov_Bonds: int = Field(default=0, ge=-100, le=100)
    sub_Yield_Curve: int = Field(default=0, ge=-100, le=100)
    sub_Major_FX: int = Field(default=0, ge=-100, le=100)
    sub_Nordic_FX: int = Field(default=0, ge=-100, le=100)
    sub_EM_FX: int = Field(default=0, ge=-100, le=100)
    sub_Large_Cap_Crypto: int = Field(default=0, ge=-100, le=100)
    sub_Mid_Cap_Crypto: int = Field(default=0, ge=-100, le=100)
    sub_Meme_Alt: int = Field(default=0, ge=-100, le=100)
    sub_ETFs: int = Field(default=0, ge=-100, le=100)
    sub_Active_Funds: int = Field(default=0, ge=-100, le=100)
    sub_Gold: int = Field(default=0, ge=-100, le=100)
    sub_Silver: int = Field(default=0, ge=-100, le=100)
    
    @field_validator('*', mode='before')
    @classmethod
    def coerce_to_int(cls, v: Any) -> int:
        """Ensure all values are integers."""
        if v is None:
            return 0
        try:
            return int(float(v))
        except (ValueError, TypeError):
            return 0
    
    @model_validator(mode='before')
    @classmethod
    def flatten_and_map_fields(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """Flatten nested structures and map field name variations."""
        if not isinstance(data, dict):
            return data
        
        # Step 1: Flatten nested structures
        flattened = {}
        for key, value in data.items():
            if isinstance(value, dict):
                # Flatten nested dict - add all inner keys to top level
                for inner_key, inner_value in value.items():
                    flattened[inner_key] = inner_value
            else:
                flattened[key] = value
        
        # Step 2: Map field name variations
        field_mappings = {
            # Regions - various formats to region_XXX
            'US': 'region_US',
            'United States': 'region_US',
            'USA': 'region_US',
            'America': 'region_US',
            'us': 'region_US',
            'EU': 'region_EU',
            'Europe': 'region_EU',
            'European Union': 'region_EU',
            'Eurozone': 'region_EU',
            'eu': 'region_EU',
            'JP': 'region_JP',
            'Japan': 'region_JP',
            'jp': 'region_JP',
            'CN': 'region_CN',
            'China': 'region_CN',
            'cn': 'region_CN',
            'SE': 'region_SE',
            'Sweden': 'region_SE',
            'se': 'region_SE',
            'DK': 'region_DK',
            'Denmark': 'region_DK',
            'dk': 'region_DK',
            'Nordics': 'region_Nordics',
            'nordics': 'region_Nordics',
            
            # Sub-classes - various formats
            'US Stocks': 'sub_US_Stocks',
            'US Stock': 'sub_US_Stocks',
            'us_stocks': 'sub_US_Stocks',
            'EU Stocks': 'sub_EU_Stocks',
            'European Stocks': 'sub_EU_Stocks',
            'eu_stocks': 'sub_EU_Stocks',
            'Asia Stocks': 'sub_Asia_Stocks',
            'Asian Stocks': 'sub_Asia_Stocks',
            'asia_stocks': 'sub_Asia_Stocks',
            'Nordic Stocks': 'sub_Nordic_Stocks',
            'Nordic Stock': 'sub_Nordic_Stocks',
            'nordic_stocks': 'sub_Nordic_Stocks',
            'Government Bonds': 'sub_Gov_Bonds',
            'Gov Bonds': 'sub_Gov_Bonds',
            'gov_bonds': 'sub_Gov_Bonds',
            'government_bonds': 'sub_Gov_Bonds',
            'Yield Curve': 'sub_Yield_Curve',
            'yield_curve': 'sub_Yield_Curve',
            'Major FX': 'sub_Major_FX',
            'major_fx': 'sub_Major_FX',
            'Nordic FX': 'sub_Nordic_FX',
            'nordic_fx': 'sub_Nordic_FX',
            'EM FX': 'sub_EM_FX',
            'em_fx': 'sub_EM_FX',
            'Large Cap Crypto': 'sub_Large_Cap_Crypto',
            'Large Cap': 'sub_Large_Cap_Crypto',
            'large_cap_crypto': 'sub_Large_Cap_Crypto',
            'Mid Cap Crypto': 'sub_Mid_Cap_Crypto',
            'Mid Cap': 'sub_Mid_Cap_Crypto',
            'mid_cap_crypto': 'sub_Mid_Cap_Crypto',
            'Meme & Alt': 'sub_Meme_Alt',
            'Meme': 'sub_Meme_Alt',
            'meme_alt': 'sub_Meme_Alt',
            'ETFs': 'sub_ETFs',
            'ETF': 'sub_ETFs',
            'etfs': 'sub_ETFs',
            'Active Funds': 'sub_Active_Funds',
            'Active Fund': 'sub_Active_Funds',
            'active_funds': 'sub_Active_Funds',
            'Gold': 'sub_Gold',
            'gold': 'sub_Gold',
            'Silver': 'sub_Silver',
            'silver': 'sub_Silver',
        }
        
        # Apply mappings
        mapped_data = {}
        for key, value in flattened.items():
            if key in field_mappings:
                mapped_key = field_mappings[key]
                mapped_data[mapped_key] = value
            else:
                mapped_data[key] = value
        
        return mapped_data

class NewsTag(BaseModel):
    idx: int = -1
    asset: str = 'other'


class NewsTagBatch(BaseModel):
    tags: List[NewsTag] = Field(default_factory=list)