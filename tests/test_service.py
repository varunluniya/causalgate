import pytest

from gen4 import KnowledgeBase, LLMClient, Memory
from service import CausalGateService, evidence_needed


@pytest.fixture
def svc():
    return CausalGateService(Memory(), KnowledgeBase.from_dir("knowledge"), LLMClient(provider="offline"))


def test_v1_numbers_reproduced_and_report_printed(svc):
    r = svc.benchmark("v1", "recorded_v1")
    assert [r["levels"][k]["accuracy"] for k in ("correlation", "intervention", "counterfactual")] == [0.8, 0.6, 0.4]
    assert "CORRELATION" in r["report"]


def test_weak_levels_cite_causal_model(svc):
    r = svc.benchmark("demo-model-a", "answers")
    headings = {c["heading"] for c in r["trace"]["retrieval"]}
    assert "Counterfactual questions (Level 3)" in headings or "Intervention questions (Level 2)" in headings


def test_evidence_needed_is_monotone_sensible():
    assert evidence_needed(1.0) == 12
    assert evidence_needed(0.7) is None
    assert evidence_needed(0.9) < evidence_needed(0.8)


def test_live_backend_requires_a_key(svc):
    with pytest.raises(ValueError):
        svc.benchmark("x", "live")


def test_custom_answers_and_override_memory(svc):
    ans = {"I3": ["Look at the historical opt-in data carefully."]}
    r = svc.benchmark("mine", "answers", ans)
    assert r["levels"]["intervention"]["accuracy"] == 0.0
    svc.override("I3", "Look at the historical opt-in data carefully.", True)
    again = svc.benchmark("mine", "answers", ans)
    assert again["questions"][5]["verdicts"][0]["method"] == "human_override"


def test_unknown_question_override_rejected(svc):
    with pytest.raises(KeyError):
        svc.override("Z9", "x", True)
