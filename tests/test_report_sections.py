import json
import os

import pytest

from html_report_generator import HTMLReportGenerator

PATH = 'data/reports/latest_analysis.json'


def test_key_sections_render():
    if not os.path.exists(PATH):
        pytest.skip('no analysis JSON yet')
    with open(PATH) as f:
        data = json.load(f)
    g = HTMLReportGenerator()
    html = (g._generate_sentiment_dashboard(data)
            + g._generate_impact_section(data)
            + g._generate_watchlist_section(data))
    for marker in ('Quantitative Sentiment Dashboard', 'Causal Impact', 'Fundamental Watchlist'):
        assert marker in html, f'section missing: {marker}'
