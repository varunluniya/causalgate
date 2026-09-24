#!/usr/bin/env python3
"""
Seed CausalGate with synthetic benchmark history.

    python seed.py [--reset] [--if-empty]

Four benchmarks of the dealer point-of-sale lending domain over four months:
the recorded v1 verdicts, demo-model-a, demo-model-b, and demo-model-a again
after two human grading overrides, so /benchmarks history, regressions and
override memory all have data. The demo answer sets are illustrative and
written for the offline demo, not outputs of any real model.
"""

from pathlib import Path

from gen4 import Memory
from gen4.seedkit import already_seeded, args, iso, mark
from service import CausalGateService


def main():
    a, rng = args("data/causalgate.db", "Seed CausalGate with synthetic benchmark history")
    Path(a.db).parent.mkdir(parents=True, exist_ok=True)
    mem = Memory(a.db)
    if a.if_empty and already_seeded(mem):
        print(f"{a.db} already has data -- skipping seed")
        return
    svc = CausalGateService(memory=mem)
    plan = [("v1-recorded", "recorded_v1", 120), ("demo-model-a", "answers", 75), ("demo-model-b", "answers", 40)]
    for label, backend, days in plan:
        r = svc.benchmark(label, backend)
        mem.backdate(r["run_id"], iso(days))
        print(f"  {label:<14} " + " / ".join(f"{k[:4]} {v['accuracy']:.0%}" for k, v in r["levels"].items()))
    # a grader reviews two borderline rubric misses on model A, then re-runs it
    svc.override("F1", "Uncertain for this individual; it needs assumptions.", True, grader="risk-analyst")
    svc.override("I2", "Not necessarily; customers may shift to other dealers.", True, grader="risk-analyst")
    r = svc.benchmark("demo-model-a", "answers")
    mem.backdate(r["run_id"], iso(10))
    counts = {"benchmarks": 4, "overrides": 2}
    mark(mem, "causalgate", a.seed, counts)
    print(f"seeded {a.db}: {counts}")


if __name__ == "__main__":
    main()
