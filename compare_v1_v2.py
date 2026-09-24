#!/usr/bin/env python3
"""Prove-It: what v1 said vs what v2 says, on the same evidence and beyond."""
from benchmark import run_report
from domains.lending import build_lending_suite
from gen4 import KnowledgeBase, LLMClient, Memory
from service import CausalGateService

print("v1 (recorded verdicts, point estimates)\n")
print(run_report(build_lending_suite()))
svc = CausalGateService(Memory(), KnowledgeBase.from_dir("knowledge"), LLMClient(provider="offline"))
print("\n\nv2 on the SAME recorded evidence\n")
print(svc.benchmark("v1-recorded", "recorded_v1")["report"])
for m in ("demo-model-b", "demo-model-a"):
    print(f"\n\nv2 on free-text answers ({m}, bundled illustrative answer set)\n")
    print(svc.benchmark(m, "answers")["report"])
