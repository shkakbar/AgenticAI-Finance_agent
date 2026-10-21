import json

from agents.news_tagger import NewsTagger


class StubRouter:
    def generate_text(self, prompt, system_prompt="", task_type='deep'):
        return '{"tags":[{"idx":0,"asset":"macro"},{"idx":1,"asset":"other"}]}'

    def _extract_json(self, text):
        return json.loads(text)


def test_retag_moves_only_valid_assets():
    nb = {'Other': [{'title': 'Fed hikes rates'},
                    {'title': 'Dog wins baking contest'},
                    {'title': 'Apple earnings beat'}],
          'stocks': []}
    tagger = NewsTagger(StubRouter())
    new_nb, moved = tagger.retag(nb)
    assert moved == 1                      # 'other' asset is not in ASSET_KEYS -> ignored
    assert len(new_nb['macro']) == 1
    assert len(new_nb['Other']) == 2       # untagged + invalid stay in Other
    assert new_nb['stocks'] == []