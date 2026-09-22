"""
CausalGate — a reusable causal-reasoning benchmark and deploy-gating engine.

Grades any model's answers to a set of test questions at each of Judea
Pearl's three causal levels (correlation, intervention, counterfactual),
and turns the per-level scores into a concrete deploy recommendation.

The engine is domain-agnostic: it operates purely on TestQuestion/Run
objects. A domain module (see domains/lending.py) is responsible for
supplying the actual questions and expected answers for a given problem
space.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List


class CausalLevel(Enum):
    CORRELATION = "correlation"
    INTERVENTION = "intervention"
    COUNTERFACTUAL = "counterfactual"


@dataclass
class Run:
    """A single graded attempt at a question."""
    answer: str
    correct: bool


@dataclass
class TestQuestion:
    """
    One test question at a given causal level, with N graded runs.

    `consistency` is defined as agreement with the epistemically CORRECT
    determination, not raw majority-vote agreement between runs. That is
    the same grading convention the original human-graded benchmark used
    (a run is "consistent" if it lands on the right answer, not merely if
    it matches what most other runs said) — so consistency and accuracy
    are, by this construction, the same number. This looks redundant at
    first glance but it is the faithful reproduction of the original
    methodology: a model that confidently and repeatably gives the WRONG
    answer is both 0% accurate and 0% consistent under this definition,
    not "100% consistent, 0% accurate."
    """
    level: CausalLevel
    question: str
    expected_answer: str
    runs: List[Run] = field(default_factory=list)

    @property
    def accuracy(self) -> float:
        if not self.runs:
            return 0.0
        return sum(1 for r in self.runs if r.correct) / len(self.runs)

    @property
    def consistency(self) -> float:
        return self.accuracy


@dataclass
class TestSuite:
    """A named collection of test questions for one problem domain."""
    domain: str
    questions: List[TestQuestion]

    def questions_at(self, level: CausalLevel) -> List[TestQuestion]:
        return [q for q in self.questions if q.level == level]

    def level_accuracy(self, level: CausalLevel) -> float:
        qs = self.questions_at(level)
        if not qs:
            return 0.0
        return sum(q.accuracy for q in qs) / len(qs)

    def level_consistency(self, level: CausalLevel) -> float:
        qs = self.questions_at(level)
        if not qs:
            return 0.0
        return sum(q.consistency for q in qs) / len(qs)


# Deploy-recommendation thresholds. A level scoring below these bands
# needs a compensating design (human review, confidence gating, etc.)
# before it is safe to hand fully to the model.
SAFE_THRESHOLD = 0.75
REVIEW_THRESHOLD = 0.50


def deploy_recommendation(accuracy: float) -> str:
    if accuracy >= SAFE_THRESHOLD:
        return "SAFE"
    if accuracy >= REVIEW_THRESHOLD:
        return "NEEDS REVIEW"
    return "DO NOT DEPLOY"


def run_report(suite: TestSuite) -> str:
    lines = [f"Causal benchmark report — domain: {suite.domain}", "=" * 60]
    for level in CausalLevel:
        acc = suite.level_accuracy(level)
        con = suite.level_consistency(level)
        rec = deploy_recommendation(acc)
        lines.append(
            f"{level.value.upper():<15} accuracy={acc*100:5.1f}%  "
            f"consistency={con*100:5.1f}%  -> {rec}"
        )
    return "\n".join(lines)
