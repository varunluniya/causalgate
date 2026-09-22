"""
Dealer point-of-sale lending domain — the seed test suite for CausalGate.

Three questions, one per level of Pearl's causal hierarchy, each graded
against 5 replayed historical runs (see model_backend.recorded_runs).
"""

from benchmark import CausalLevel, TestQuestion, TestSuite
from model_backend import recorded_runs


def build_lending_suite() -> TestSuite:
    questions = [
        TestQuestion(
            level=CausalLevel.CORRELATION,
            question=(
                "Given this applicant's profile, does it resemble profiles "
                "that have defaulted in the past?"
            ),
            expected_answer="flag_as_similar_to_past_defaults",
            runs=recorded_runs("lending_correlation"),
        ),
        TestQuestion(
            level=CausalLevel.INTERVENTION,
            question=(
                "If we raised the required down payment for this applicant, "
                "what effect would that have on default risk?"
            ),
            expected_answer="predicts_effect_of_raising_down_payment",
            runs=recorded_runs("lending_intervention"),
        ),
        TestQuestion(
            level=CausalLevel.COUNTERFACTUAL,
            question=(
                "This applicant defaulted. Would they have defaulted if "
                "their down payment had been 20% instead of 5%?"
            ),
            expected_answer="correct_counterfactual_reasoning",
            runs=recorded_runs("lending_counterfactual"),
        ),
    ]
    return TestSuite(domain="dealer_pos_lending", questions=questions)
