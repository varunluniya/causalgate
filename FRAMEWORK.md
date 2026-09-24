# CausalGate — FDE Framework Build Notes

## Part 1 — Problem Reframing

| Step | Output |
|---|---|
| Ordinary problem | "Score a model's causal reasoning at three levels." |
| Lever 1: Data liquidity | The causal structure of the domain (confounders, selection effects) lives in analysts' heads, not in the grader. Human grading judgements are made once and lost. |
| Lever 2: Network effect | Every benchmark run and every human override accumulates. Model versions are compared automatically, and remembered verdicts make grading more consistent over time. |
| Lever 3: Algorithmic leverage | Evidence-adjusted gating (Wilson lower bound instead of point accuracy), plus use-case gating: a feature ships only if every causal level it depends on is safe. |
| Lever 4: First principles × JTBD | The product owner's job is not "know the model's causal score". It is "know whether I can ship *this feature* on *this model*". 4 correct answers out of 5 is not evidence of safety. |
| Extraordinary problem | **Answer "can we ship feature X on model Y?" with statistical honesty**: benchmark free-text answers at each causal level, refuse to call a level safe on thin evidence, say how much more evidence is needed, and catch regressions between model versions. |
| Rating | 5 / 5. It changes the output from a score to a ship/no-ship decision per feature. |

## Part 2 — Design the Eval

**Outcome of intelligence**
- v1's recorded numbers are reproduced exactly (80% / 60% / 40%).
- No level is called SAFE when its 95% lower bound is under 75%. The report says how many answers would be needed.
- Use-case gating follows the weakest required level. A weaker model after a stronger one is flagged as a regression.

**EQ(PRE)**
| Angle | Hypothesis |
|---|---|
| Causal | The grader itself can confuse "mentions confounding" with "reasons correctly about confounding". |
| Context | Point accuracy on 5 answers is treated as evidence. |
| Consistency | The same answer is graded differently across runs or graders. |

**EQ(POST), cheapest first**
1. Prompt: the LLM judge gets the causal-model notes for the question's level and must return a strict boolean.
2. Context/retrieval: the rubric (required concept groups and fallacy phrases) is the offline floor, and the causal model is cited for weak levels.
3. Feedback: human overrides are remembered by answer and applied on rerun. Run history drives regression detection.

**Executable:** `python run_evals.py` runs 12 cases × 3 runs (v1 parity, evidence, use-case gating, grader spot checks, feedback, regression).

## Part 3 — Gen-4 Architecture

| Layer | What CausalGate does |
|---|---|
| Retrieval | `knowledge/lending_causal_model.md` (confounders, selection, what each level needs) and `gating_policy.md`. The sections for weak levels are cited, and the judge reads them. |
| Context | Model label, backend (live, answers or recorded_v1), graded-answer count → evidence-adjusted bands and answers needed. |
| Memory | Every benchmark with its raw answers, human overrides keyed by (question, normalised answer), previous run per domain. |
| Feedback | `POST /overrides` then `POST /benchmarks/{id}/rerun`. Automatic regression detection against the previous run. |

The model: `backend=live` asks a real model each question N times and uses an LLM judge. Offline, bundled illustrative answer sets (clearly labelled as not real model outputs) and the rubric grader keep the pipeline runnable.

## Part 4 — Implementation Plan

| Component | Priority | Estimate | Status |
|---|---|---|---|
| 9-question text bank with rubrics (3 per level) | MVP | 0.5 day | done |
| Rubric grader + LLM judge + override memory | MVP | 0.5 day | done |
| Evidence-adjusted bands + answers-needed | MVP | 0.25 day | done |
| Use-case gating | MVP | 0.25 day | done |
| Regression vs previous run | MVP | 0.1 day | done |
| API, Docker, CI | MVP | 0.5 day | done |
| Insurance-intake domain (second question bank) | nice-to-have | 0.5 day | future |
| Larger bank (30+ per level) so SAFE is reachable with fewer runs | nice-to-have | 1 day | future |
| Nightly scheduled benchmark of the production model | future | 0.5 day | future |

## Part 5 — Prove It

**Visible change** (`python compare_v1_v2.py`, output in `run_output_v1_vs_v2.txt`):

| On the same recorded evidence (5 answers per level) | v1 | v2 |
|---|---|---|
| Correlation, 4/5 correct | SAFE | **SAFE on the point estimate, DO NOT DEPLOY on the lower bound (37.5%)**: needs about 272 answers to prove 80% ≥ 75% |
| Intervention, 3/5 | NEEDS REVIEW | NEEDS REVIEW, insufficient evidence |
| Counterfactual, 2/5 | DO NOT DEPLOY | DO NOT DEPLOY |

| Free-text answers, 15 per level | demo-model-b | demo-model-a |
|---|---|---|
| Correlation / Intervention / Counterfactual | 100% / 100% / 80% | 100% / 60% / 27% |
| risk_flag feature | SHIP | SHIP |
| policy_simulator feature | SHIP | **BLOCKED** by intervention |
| default_explainer feature | BLOCKED by counterfactual (80% is not proven ≥ 75%) | BLOCKED |
| Regression flagged when A follows B | — | intervention 100→60%, counterfactual 80→27% |

An outside observer would see that v1's "SAFE" was statistically unsupported, and that v2 turns a benchmark into the decision a product team actually needs: which features can ship on which model.
