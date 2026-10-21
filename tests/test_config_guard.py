import config

SANCTIONED_FAST = {'qwen2.5:7b-instruct'}
SANCTIONED_DEEP = {'qwen2.5:32b-instruct'}

def test_model_stack_sanctioned():
    assert config.FAST_MODEL in SANCTIONED_FAST, f"FAST_MODEL drifted: {config.FAST_MODEL}"
    assert config.DEEP_MODEL in SANCTIONED_DEEP, f"DEEP_MODEL drifted: {config.DEEP_MODEL}"
