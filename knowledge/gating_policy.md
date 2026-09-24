# CausalGate Deployment Gating Policy

## Recommendation bands
Accuracy of at least 75% at a causal level is SAFE, 50 to 75% is NEEDS REVIEW, below 50% is DO NOT DEPLOY.

## Evidence-adjusted recommendation
A point estimate from a handful of runs is not evidence. The evidence-adjusted recommendation uses the Wilson 95% lower bound
of accuracy in place of the point estimate. A level that is SAFE on the point estimate but not on the lower bound is reported as
"SAFE (insufficient evidence)", together with the number of graded answers needed.

## Use-case gating
A product feature is gated by the causal levels it depends on. A pricing-policy simulator depends on intervention.
A "why did this borrower default" explainer depends on counterfactual. A risk-segment flag depends only on correlation.
The feature ships only if every level it depends on is SAFE on the evidence-adjusted recommendation.

## Grading
With a live model, an LLM judge grades against the question's rubric and the causal model.
Offline, a rubric grader checks for required concepts and known fallacy phrases. It is a floor, not a replacement for judgement.
Human graders can override any verdict. Overrides are remembered and applied to identical answers in future runs.

## Regression between model versions
Each benchmark is compared with the previous run on the same domain. A level that drops by 15 points or more is reported as a regression.
