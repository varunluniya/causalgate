# CausalGate

A reusable causal-reasoning benchmark and deploy-gating engine. CausalGate
grades a model's answers at each of Judea Pearl's three causal levels —
correlation, intervention, and counterfactual — and turns those scores
into a concrete, per-level deploy recommendation, instead of a single
average accuracy number that hides where a model actually breaks down.

## Why causal level matters

A model can look highly reliable on a correlation-shaped question ("does
this resemble a past default?") while being unsafe on a counterfactual one
("would this applicant have defaulted with a bigger down payment?"). The
three levels sit on a hierarchy of increasing difficulty, and treating
them as one blended score hides exactly the failure mode that matters most
for deployment decisions: the level where the model quietly stops being
trustworthy.

## Deploy recommendation thresholds

| Accuracy | Recommendation |
|---|---|
| ≥ 75% | SAFE |
| 50–75% | NEEDS REVIEW |
| < 50% | DO NOT DEPLOY |

A level scoring below SAFE needs a compensating design — human review,
confidence gating, explicit uncertainty surfacing — before it's handed
fully to the model.

## Demo — dealer point-of-sale lending

```
$ python cli.py
Causal benchmark report — domain: dealer_pos_lending
============================================================
CORRELATION     accuracy= 80.0%  consistency= 80.0%  -> SAFE
INTERVENTION    accuracy= 60.0%  consistency= 60.0%  -> NEEDS REVIEW
COUNTERFACTUAL  accuracy= 40.0%  consistency= 40.0%  -> DO NOT DEPLOY
```

Reliability drops steadily moving up the causal hierarchy — exactly the
pattern the benchmark is built to surface. The counterfactual level is
flagged DO NOT DEPLOY on its own, meaning any product decision resting on
counterfactual reasoning in this domain needs a human in the loop.

## Honest disclosure on the model backend

No external LLM API key was available when this was built, so
`model_backend.py`'s `recorded_runs()` replays the actual, human-graded
verdicts from a real 5-run benchmark on this domain — a historical record,
not simulated or fabricated data — disclosed honestly in the code.
`live_model_backend()` is the documented swap point for a real API call;
nothing else in the codebase needs to change once it's wired up.

## Consistency vs. accuracy

`TestQuestion.consistency` is defined as agreement with the *correct*
answer, not raw majority-vote agreement between runs. A model that
confidently and repeatably gives the wrong answer is 0% consistent under
this definition, not "highly consistent, just wrong" — see the docstring
in `benchmark.py` for the full rationale, and `test_causalgate.py` for a
test that pins this behavior down explicitly.

## Project layout

```
benchmark.py          Domain-agnostic scoring engine (CausalLevel, TestQuestion,
                       TestSuite, deploy_recommendation, run_report)
model_backend.py       Swap point for a live LLM call + the honest historical replay
domains/lending.py     The seed test suite: 3 questions, 1 per causal level
cli.py                 Entry point — runs the lending suite and prints the report
test_causalgate.py     pytest suite (7/7 passing)
run_output.txt          Captured real output from `python cli.py`
```

## Adding a new domain

Write a new `domains/<name>.py` that builds a `TestSuite` out of
`TestQuestion` objects (see `domains/lending.py`), point `cli.py` at it,
and the same scoring/reporting engine applies unchanged.

## Tests

```
$ python -m pytest test_causalgate.py -v
7 passed
```
