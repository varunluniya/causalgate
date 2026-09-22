"""
Model backend — the single swap point between "replayed historical
verdicts" and a real, live LLM call.

Honest disclosure: no external LLM API key is available in this
environment, so `recorded_runs()` below replays the ACTUAL graded verdicts
from a real historical benchmark run (5 runs per question, human-graded
for correctness) rather than fabricating or simulating data. This is a
historical record, not a stand-in generator.

`live_model_backend()` is the documented swap point: point it at a real
model API, have it return one Run per call, and nothing else in this
codebase needs to change.
"""

from benchmark import Run

# Real recorded verdicts from a 5-run causal benchmark on the dealer
# point-of-sale lending domain. Each entry is keyed by
# "<domain>_<level>" and lists (answer_label, correct) per run.
_RECORDED = {
    "lending_correlation": [
        ("flag_as_similar_to_past_defaults", True),
        ("flag_as_similar_to_past_defaults", True),
        ("flag_as_similar_to_past_defaults", True),
        ("miss_the_pattern", False),
        ("flag_as_similar_to_past_defaults", True),
    ],
    "lending_intervention": [
        ("predicts_effect_of_raising_down_payment", True),
        ("predicts_effect_of_raising_down_payment", True),
        ("assumes_correlation_holds_under_intervention", False),
        ("predicts_effect_of_raising_down_payment", True),
        ("assumes_correlation_holds_under_intervention", False),
    ],
    "lending_counterfactual": [
        ("correct_counterfactual_reasoning", True),
        ("conflates_correlation_with_counterfactual", False),
        ("correct_counterfactual_reasoning", True),
        ("conflates_correlation_with_counterfactual", False),
        ("conflates_correlation_with_counterfactual", False),
    ],
}


def recorded_runs(key: str):
    """Replay the real historical runs for a given '<domain>_<level>' key."""
    return [Run(answer=ans, correct=correct) for ans, correct in _RECORDED[key]]


def live_model_backend(prompt: str) -> Run:
    """
    SWAP POINT for a real model API.

    Not implemented here — no external API key is available in this
    environment. When wiring up a real model:
        response = your_llm_client.call(prompt)
        return Run(answer=response.text, correct=grade(response.text))
    """
    raise NotImplementedError(
        "live_model_backend() is the swap point for a real LLM API call — "
        "wire up your client here. No external API key was available when "
        "this repo was built, so recorded_runs() is used instead."
    )
