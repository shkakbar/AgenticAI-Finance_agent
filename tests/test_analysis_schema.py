import json
import os

import pytest

PATH = 'data/reports/latest_analysis.json'


@pytest.fixture(scope='module')
def data():
    if not os.path.exists(PATH):
        pytest.skip('no analysis JSON yet')
    with open(PATH) as f:
        return json.load(f)


def test_sentiment_contract(data):
    sd = data.get('sentiment_data', {})
    assert 'overall_sentiment' in sd
    assert -100 <= sd['overall_sentiment'] <= 100
    for asset, v in sd.get('asset_sentiments', {}).items():
        assert -100 <= v['score'] <= 100, f'{asset} score out of range'


def test_impact_contract(data):
    ia = data.get('sentiment_data', {}).get('impact_analysis', {})
    for key in ('category_impact', 'opposing_impacts', 'delayed_impacts', 'se_impact'):
        assert key in ia, f'impact_analysis missing {key}'


def test_no_empty_prose_fields(data):
    cv = data.get('sentiment_data', {}).get('consolidated_view', {})
    for field in ('executive_summary', 'bottom_line'):
        val = cv.get(field, '')
        assert len(val) > 40, f'{field} looks like a bare score, not prose'
