import pytest

from benchmark import (
    CausalLevel,
    Run,
    TestQuestion,
    TestSuite,
    deploy_recommendation,
    SAFE_THRESHOLD,
    REVIEW_THRESHOLD,
)
from domains.lending import build_lending_suite


def test_accuracy_computed_from_runs():
    q = TestQuestion(
        level=CausalLevel.CORRELATION,
        question="q",
        expected_answer="a",
        runs=[Run("a", True), Run("a", True), Run("b", False), Run("a", True), Run("a", True)],
    )
    assert q.accuracy == pytest.approx(0.8)


def test_consistency_equals_accuracy_not_majority_agreement():
    # Three runs give the SAME wrong answer, two give different wrong
    # answers -- majority-vote "consistency" would call this highly
    # consistent even though it's 0% correct. This benchmark's definition
    # (agreement with the CORRECT answer) must score it 0%, not high.
    q = TestQuestion(
        level=CausalLevel.COUNTERFACTUAL,
        question="q",
        expected_answer="right_answer",
        runs=[
            Run("wrong_answer", False),
            Run("wrong_answer", False),
            Run("wrong_answer", False),
            Run("other_wrong_answer", False),
            Run("other_wrong_answer", False),
        ],
    )
    assert q.accuracy == 0.0
    assert q.consistency == 0.0


def test_deploy_recommendation_thresholds():
    assert deploy_recommendation(0.80) == "SAFE"
    assert deploy_recommendation(SAFE_THRESHOLD) == "SAFE"
    assert deploy_recommendation(0.60) == "NEEDS REVIEW"
    assert deploy_recommendation(REVIEW_THRESHOLD) == "NEEDS REVIEW"
    assert deploy_recommendation(0.40) == "DO NOT DEPLOY"


def test_suite_level_accuracy_averages_its_questions():
    suite = TestSuite(
        domain="test",
        questions=[
            TestQuestion(CausalLevel.CORRELATION, "q1", "a", [Run("a", True), Run("a", True)]),
            TestQuestion(CausalLevel.CORRELATION, "q2", "a", [Run("a", True), Run("b", False)]),
        ],
    )
    assert suite.level_accuracy(CausalLevel.CORRELATION) == pytest.approx(0.75)


def test_lending_suite_has_one_question_per_level():
    suite = build_lending_suite()
    for level in CausalLevel:
        assert len(suite.questions_at(level)) == 1


def test_lending_suite_reproduces_published_scores():
    suite = build_lending_suite()
    assert suite.level_accuracy(CausalLevel.CORRELATION) == pytest.approx(0.80)
    assert suite.level_consistency(CausalLevel.CORRELATION) == pytest.approx(0.80)
    assert suite.level_accuracy(CausalLevel.INTERVENTION) == pytest.approx(0.60)
    assert suite.level_consistency(CausalLevel.INTERVENTION) == pytest.approx(0.60)
    assert suite.level_accuracy(CausalLevel.COUNTERFACTUAL) == pytest.approx(0.40)
    assert suite.level_consistency(CausalLevel.COUNTERFACTUAL) == pytest.approx(0.40)


def test_lending_suite_deploy_recommendations_match_thresholds():
    suite = build_lending_suite()
    assert deploy_recommendation(suite.level_accuracy(CausalLevel.CORRELATION)) == "SAFE"
    assert deploy_recommendation(suite.level_accuracy(CausalLevel.INTERVENTION)) == "NEEDS REVIEW"
    assert deploy_recommendation(suite.level_accuracy(CausalLevel.COUNTERFACTUAL)) == "DO NOT DEPLOY"
