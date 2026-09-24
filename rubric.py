"""
Text-answer question bank + rubric grader for live causal benchmarking.

v1 could only replay pre-graded verdict labels. v2 asks a model open
questions and grades free-text answers:
  * live: an LLM judge grades against the rubric + the domain causal model
  * offline: this rubric grader -- every `require` concept group must appear
    (any synonym), and no `fallacy` phrase may appear

The rubric grader is a floor: honest, deterministic, explainable, and weaker
than a judge on unusual phrasings. Human overrides (service.override) cover
the gap and are remembered.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from benchmark import CausalLevel


@dataclass
class RubricQuestion:
    id: str
    level: CausalLevel
    question: str
    reference: str
    require: list[list[str]] = field(default_factory=list)   # AND of ORs
    fallacy: list[str] = field(default_factory=list)
    use_cases: list[str] = field(default_factory=list)


def _has(text: str, term: str) -> bool:
    # prefix match ("randomi" hits randomised/randomized); short terms must be whole words
    tail = r"(?![a-z])" if len(term) <= 3 else ""
    return re.search(r"(?<![a-z])" + re.escape(term.lower()) + tail, text) is not None


def rubric_grade(q: RubricQuestion, answer: str) -> dict:
    t = answer.lower()
    missing = [g for g in q.require if not any(_has(t, s) for s in g)]
    fallacies = [f for f in q.fallacy if _has(t, f)]
    ok = not missing and not fallacies
    detail = []
    if missing:
        detail.append("missing concept: " + " | ".join("/".join(g[:3]) for g in missing))
    if fallacies:
        detail.append("fallacy: " + ", ".join(fallacies))
    return {"correct": ok, "method": "rubric", "detail": "; ".join(detail) or "all required concepts present"}


LENDING = [
    RubricQuestion("C1", CausalLevel.CORRELATION,
                   "Applicants with debt-to-income above 50% defaulted three times as often last year. "
                   "This applicant's DTI is 55%. Do they belong to a higher-risk group?",
                   "Yes -- they are in the group with higher observed default.",
                   [["yes", "higher", "more likely", "elevated"]], ["no,", "lower risk"], ["risk_flag"]),
    RubricQuestion("C2", CausalLevel.CORRELATION,
                   "Loans originated at dealer D-13 show a higher default rate. Is a new D-13 applicant "
                   "part of a group with higher observed default?",
                   "Yes, observationally.", [["yes", "higher", "elevated"]], ["lower risk"], ["risk_flag"]),
    RubricQuestion("C3", CausalLevel.CORRELATION,
                   "Two-wheeler loans with down payments under 10% show twice the default rate. Is a 5% "
                   "down payment associated with higher default?",
                   "Yes, it is associated with higher default.", [["yes", "associated", "higher", "correlat"]],
                   ["not associated"], ["risk_flag"]),
    RubricQuestion("I1", CausalLevel.INTERVENTION,
                   "If we raise the minimum down payment from 5% to 20%, will defaults fall by the same 2x "
                   "we see in the data?",
                   "Not necessarily: income confounds down payment and default, and the policy changes who applies.",
                   [["not necessarily", "no", "cannot assume", "can't assume", "may not", "unlikely", "depends"],
                    ["confound", "selection", "self-select", "who applies", "income", "different applicants"]],
                   ["will fall by half", "yes, defaults will", "will halve"], ["policy_simulator"]),
    RubricQuestion("I2", CausalLevel.INTERVENTION,
                   "If we stop lending through dealer D-13, will the portfolio default rate drop?",
                   "It depends whether D-13 causes defaults (e.g. fraud) or serves a riskier region; customers "
                   "may move to other dealers.",
                   [["depends", "not necessarily", "only if", "unclear", "may not"],
                    ["cause", "causal", "fraud", "region", "other dealers", "shift", "mix", "substitut"]],
                   ["will definitely drop", "certainly drop"], ["policy_simulator"]),
    RubricQuestion("I3", CausalLevel.INTERVENTION,
                   "We want to know the effect of SMS payment reminders on default. What evidence would tell us?",
                   "A randomised experiment / A-B test with a control group; opt-in comparisons are biased.",
                   [["randomi", "a/b", "experiment", "control group", "holdout", "rct"]],
                   ["compare those who opted in", "just compare"], ["policy_simulator"]),
    RubricQuestion("F1", CausalLevel.COUNTERFACTUAL,
                   "This applicant defaulted. Would they have defaulted if their down payment had been 20% "
                   "instead of 5%?",
                   "Cannot be known from population data; needs an individual-level model and assumptions; "
                   "answer is probabilistic.",
                   [["cannot", "can't", "not possible to know", "uncertain", "probabil", "no way to know"],
                    ["individual", "this applicant", "assum", "counterfactual", "structural"]],
                   ["would not have defaulted", "would definitely"], ["default_explainer"]),
    RubricQuestion("F2", CausalLevel.COUNTERFACTUAL,
                   "A borrower who received an SMS reminder repaid on time. Would they have repaid without it?",
                   "Unknown -- they may have repaid anyway; needs a counterfactual model / baseline repayment propensity.",
                   [["cannot", "can't", "unknown", "uncertain", "may have", "might have", "not possible to know"],
                    ["anyway", "baseline", "without the", "counterfactual", "regardless", "propensity"]],
                   ["the sms caused", "because of the sms"], ["default_explainer"]),
    RubricQuestion("F3", CausalLevel.COUNTERFACTUAL,
                   "Had we rejected all D-13 applicants last year, what would our default rate have been?",
                   "Only estimable under assumptions; those customers might have applied elsewhere (substitution), "
                   "changing the mix.",
                   [["estimate", "depends", "assum", "cannot know", "uncertain", "can't know"],
                    ["elsewhere", "other dealers", "substitut", "mix", "those customers", "would have applied"]],
                   ["exactly", "would simply be"], ["default_explainer"]),
]

USE_CASES = {
    "risk_flag": {"levels": ["correlation"], "description": "flag applicants in higher-risk segments"},
    "policy_simulator": {"levels": ["correlation", "intervention"],
                         "description": "simulate the effect of a policy change"},
    "default_explainer": {"levels": ["correlation", "counterfactual"],
                          "description": "explain why a specific borrower defaulted"},
}
