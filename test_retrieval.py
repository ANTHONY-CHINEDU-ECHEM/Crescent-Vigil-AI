from crescent_vigil.knowledge.cards import parse_cards
from crescent_vigil.retrieval.index import Index, Ranker, phase_from_minute
from crescent_vigil.retrieval.text import stem, tokens


def test_tokeniser():
    assert tokens("Sats dropping on the ward")[:2] == ["oxygen", "saturation"]
    assert stem("observations") == "observation"
    assert "acute" in tokens("ACS")


def test_phases():
    assert phase_from_minute(10) == "arrival"
    assert phase_from_minute(90) == "early"
    assert phase_from_minute(500, admitted_min=200) == "ward"
    assert phase_from_minute(200 + 30 * 60, admitted_min=200) == "late"


def test_known_questions_rank_their_card():
    idx = Index.build(parse_cards())
    rk = Ranker.load()
    ids = [p.pid for p in idx.passages]
    for q, gold in [("can pethidine be used", "G007"), ("priapism for five hours", "G032"), ("is ketamine used for refractory pain", "G014")]:
        s = rk.score(idx.features(q))
        top3 = [ids[i] for i in (-s).argsort()[:3]]
        assert gold in top3, (q, top3)
