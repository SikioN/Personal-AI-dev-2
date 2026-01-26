import pytest

import sys
sys.path.insert(0, "../")
from src.utils import detect_lang, ReturnStatus

@pytest.mark.parametrize("text, expected", [
    ("Каждый охотник желает знать: где сидит фазан.", {'lang': 'ru', 'status': ReturnStatus.success}),
    ("Every hunter wants to know where the pheasant sits.", {'lang': 'en', 'status': ReturnStatus.success}),
    ("Jeder Jäger möchte wissen, wo der Fasan sitzt.", {'lang': None, 'status': ReturnStatus.not_supported_lang}),
    ("Chaque chasseur veut savoir où se trouve le faisan.", {'lang': None, 'status': ReturnStatus.not_supported_lang}),
    ("每個獵人都想知道野雞坐在哪裡。", {'lang': None, 'status': ReturnStatus.not_supported_lang}),
    ("", {'lang': None, 'status': ReturnStatus.empty_input_text}),
])
def test_detect_lang(text, expected):
    lang, status = detect_lang(text)

    assert status == expected['status']
    assert lang == expected['lang']
