#!/usr/bin/env python3
"""
CausalGate eval gate. Segments:
  v1_parity     the recorded v1 benchmark reproduces 80% / 60% / 40% and v1 bands
  evidence      a level is never called SAFE on a lower bound below 75%
  use_case      use-case gating follows the weakest required level
  grader        hand-labelled spot checks of the offline rubric grader
  feedback      a human override changes the regraded result
  regression    a weaker model after a stronger one is reported as a regression
"""

from benchmark import CausalLevel
from gen4 import KnowledgeBase, LLMClient, Memory
from gen4.evals import EvalCase, gate, print_and_exit, run_eval
from rubric import LENDING, rubric_grade
from service import CausalGateService

Q = {q.id: q for q in LENDING}


def fresh():
    return CausalGateService(Memory(), KnowledgeBase.from_dir("knowledge"), LLMClient(provider="offline"))


def system(inp):
    kind = inp[0]
    svc = fresh()
    if kind == "v1":
        lv = svc.benchmark("v1", "recorded_v1")["levels"]
        return [(lv[l.value]["accuracy"], lv[l.value]["recommendation_v1"]) for l in CausalLevel]
    if kind == "evidence":
        lv = svc.benchmark("v1", "recorded_v1")["levels"]["correlation"]
        return (lv["recommendation_v1"], lv["recommendation"])
    if kind == "use_case":
        uc = svc.benchmark(inp[1], "answers")["use_cases"]
        return {k: v["ship"] for k, v in uc.items()}
    if kind == "grade":
        return rubric_grade(Q[inp[1]], inp[2])["correct"]
    if kind == "feedback":
        r = svc.benchmark("demo-model-a", "answers")
        svc.override("F1", "They would not have defaulted.", True)   # a (wrong) human ruling, to prove the path
        after = svc.rerun(r["run_id"])
        return after["levels"]["counterfactual"]["accuracy"] > r["levels"]["counterfactual"]["accuracy"]
    if kind == "regression":
        svc.benchmark("demo-model-b", "answers")
        return sorted(x.split()[0] for x in svc.benchmark("demo-model-a", "answers")["regression"])
    raise ValueError(kind)


cases = [
    EvalCase("recorded-v1", ("v1",), [(0.8, "SAFE"), (0.6, "NEEDS REVIEW"), (0.4, "DO NOT DEPLOY")], "v1_parity"),
    EvalCase("4-of-5-not-safe", ("evidence",), ("SAFE", "DO NOT DEPLOY"), "evidence"),
    EvalCase("model-a-gates", ("use_case", "demo-model-a"),
             {"risk_flag": True, "policy_simulator": False, "default_explainer": False}, "use_case"),
    EvalCase("model-b-gates", ("use_case", "demo-model-b"),
             {"risk_flag": True, "policy_simulator": True, "default_explainer": False}, "use_case"),
    EvalCase("I1-bare-yes", ("grade", "I1", "Yes."), False, "grader"),
    EvalCase("I1-depends-confounding", ("grade", "I1", "It depends -- income confounds both."), True, "grader"),
    EvalCase("I3-ab-test", ("grade", "I3", "Correlation isn't causation; run an A/B test."), True, "grader"),
    EvalCase("I3-opt-in", ("grade", "I3", "Just compare those who opted in with those who did not."), False, "grader"),
    EvalCase("F1-certain", ("grade", "F1", "They would definitely have repaid with 20% down."), False, "grader"),
    EvalCase("F2-anyway", ("grade", "F2", "Can't tell -- they may have repaid anyway."), True, "grader"),
    EvalCase("override-applied", ("feedback",), True, "feedback"),
    EvalCase("a-after-b", ("regression",), ["counterfactual", "intervention"], "regression"),
]

if __name__ == "__main__":
    report = run_eval(cases, system, runs=3)
    ok, why = gate(report, min_accuracy=1.0, min_consistency=1.0)
    print_and_exit("CausalGate", report, ok, why)
