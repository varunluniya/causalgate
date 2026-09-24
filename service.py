"""
CausalGate intelligent service — live causal benchmarking and deploy gating.

    Retrieval  domain causal model + gating policy, cited for weak levels
    Context    model under test, backend, sample size -> evidence-adjusted bands
    Memory     every benchmark, per-answer verdicts, human grading overrides
    Feedback   overrides are applied to identical answers in future runs;
               each run is compared with the previous one for regressions

v1 replayed pre-graded verdicts and printed three bands. v2 benchmarks a
live model (or recorded text answers), grades free text, refuses to call a
level SAFE on too little evidence, answers the real product question
("can we ship the policy simulator on this model?"), and remembers.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path

from benchmark import CausalLevel, deploy_recommendation
from domains.lending import build_lending_suite
from gen4 import Context, KnowledgeBase, LLMClient, Memory, Trace
from gen4.feedback import wilson_lower
from rubric import LENDING, USE_CASES, RubricQuestion, rubric_grade

SYSTEM = "causalgate"
HERE = Path(__file__).parent
DOMAIN = "dealer_pos_lending"
REGRESSION_DROP = 0.15
LEVEL_HEADINGS = {"correlation": "Correlation questions (Level 1)",
                  "intervention": "Intervention questions (Level 2)",
                  "counterfactual": "Counterfactual questions (Level 3)"}


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.lower().strip().rstrip(".!"))


def _okey(qid: str, answer: str) -> str:
    return hashlib.sha1(f"{qid}|{_norm(answer)}".encode()).hexdigest()[:16]


def evidence_needed(p: float, threshold: float = 0.75, cap: int = 2000) -> int | None:
    """Smallest n at which accuracy p would have a Wilson lower bound >= threshold."""
    if p <= threshold:
        return None
    for n in range(1, cap + 1):
        if wilson_lower(round(p * n), n) >= threshold:
            return n
    return None


class CausalGateService:
    def __init__(self, memory: Memory | None = None, kb: KnowledgeBase | None = None,
                 llm: LLMClient | None = None):
        self.memory = memory or Memory(os.environ.get("GEN4_DB", HERE / "data" / f"{SYSTEM}.db"))
        self.kb = kb or KnowledgeBase.from_dir(HERE / "knowledge")
        self.llm = llm or LLMClient()
        self.questions = {q.id: q for q in LENDING}
        self.sample_answers = json.loads((HERE / "sample_data" / "answers.json").read_text())

    # -- grading ------------------------------------------------------------------------
    def grade(self, q: RubricQuestion, answer: str) -> dict:
        o = self.memory.fact(f"override:{_okey(q.id, answer)}", "verdict")
        if o is not None:
            return {"correct": o, "method": "human_override", "detail": "remembered human verdict"}
        if self.llm.is_live:
            causal = " ".join(p.text for p in self.kb.search(LEVEL_HEADINGS[q.level.value], k=2))
            r = self.llm.complete_json(
                f"Causal model notes: {causal}\nQuestion ({q.level.value}): {q.question}\n"
                f"Reference answer: {q.reference}\nCandidate answer: {answer}\n"
                'Is the candidate causally correct? Return {"correct": true|false, "reason": "..."}',
                offline=lambda: {"correct": None}, validate=lambda d: isinstance(d.get("correct"), bool))
            if isinstance(r.get("correct"), bool):
                return {"correct": r["correct"], "method": "llm_judge", "detail": str(r.get("reason", ""))[:200]}
        return rubric_grade(q, answer)

    def _ask_live(self, q: RubricQuestion, runs: int) -> list[str]:
        return [self.llm.complete(q.question + "\nAnswer in 2-3 sentences.", offline=lambda: "",
                                  temperature=0.7, max_tokens=200) for _ in range(runs)]

    # -- benchmark ----------------------------------------------------------------------------
    def benchmark(self, model_label: str, backend: str = "answers",
                  answers: dict[str, list[str]] | None = None, runs: int = 3) -> dict:
        trace = Trace()
        per_level: dict[str, list[bool]] = {lv.value: [] for lv in CausalLevel}
        detail = []
        if backend == "recorded_v1":
            for q in build_lending_suite().questions:
                per_level[q.level.value] += [r.correct for r in q.runs]
                detail.append({"id": q.level.value, "question": q.question,
                               "verdicts": [{"answer": r.answer, "correct": r.correct, "method": "recorded"}
                                            for r in q.runs]})
        else:
            if backend == "live":
                if not self.llm.is_live:
                    raise ValueError("backend=live needs ANTHROPIC_API_KEY or OPENAI_API_KEY")
                answers = {qid: self._ask_live(q, runs) for qid, q in self.questions.items()}
            elif answers is None:
                answers = self.sample_answers.get(model_label)
                if answers is None:
                    raise KeyError(model_label)
            for qid, q in self.questions.items():
                vs = []
                for a in answers.get(qid, []):
                    g = self.grade(q, a)
                    vs.append({"answer": a, **g})
                    per_level[q.level.value].append(g["correct"])
                detail.append({"id": qid, "level": q.level.value, "question": q.question, "verdicts": vs})

        levels = {}
        for lv, oks in per_level.items():
            n, k = len(oks), sum(oks)
            acc = k / n if n else 0.0
            lo = wilson_lower(k, n) if n else 0.0
            point = deploy_recommendation(acc)
            adjusted = deploy_recommendation(lo)
            label = adjusted if adjusted == point else f"{point} (insufficient evidence: {adjusted} on lower bound)"
            levels[lv] = {"n": n, "accuracy": round(acc, 4), "wilson_lower": round(lo, 4),
                          "recommendation_v1": point, "recommendation": adjusted, "label": label,
                          "answers_needed_for_safe": evidence_needed(acc) if point == "SAFE" and adjusted != "SAFE" else None}

        use_cases = {}
        for uc, spec in USE_CASES.items():
            blockers = [lv for lv in spec["levels"] if levels[lv]["recommendation"] != "SAFE"]
            use_cases[uc] = {"ship": not blockers, "blocked_by": blockers, "description": spec["description"]}

        prev = next(iter(self.memory.history(f"domain:{DOMAIN}", limit=1)), None)
        regression = []
        if prev:
            for lv, s in levels.items():
                before = prev["output"]["levels"][lv]["accuracy"]
                if before - s["accuracy"] >= REGRESSION_DROP:
                    regression.append(f"{lv} fell {before:.0%} -> {s['accuracy']:.0%} vs {prev['output']['model_label']}")

        weak = [lv for lv, s in levels.items() if s["recommendation"] != "SAFE"]
        q = "evidence-adjusted recommendation use-case gating " + " ".join(LEVEL_HEADINGS[w] for w in weak)
        trace.cite(self.kb.search(q, k=3))
        trace.context = (Context().add("model_label", model_label).add("backend", backend)
                         .add("graded_answers", sum(s["n"] for s in levels.values()))).as_dict()
        trace.memory = {"previous_run": prev and prev["id"],
                        "overrides_on_file": len(self.memory.facts(predicate="verdict"))}
        trace.model = {"judge": "llm_judge" if self.llm.is_live else "rubric (offline)"}
        out = {"domain": DOMAIN, "model_label": model_label, "backend": backend, "levels": levels,
               "use_cases": use_cases, "regression": regression, "questions": detail}
        rid = self.memory.record_decision(SYSTEM, f"domain:{DOMAIN}", {"model_label": model_label,
                                          "answers": answers}, out)
        return {"run_id": rid, **out, "report": self.report_text(out), "trace": trace.as_dict()}

    @staticmethod
    def report_text(out: dict) -> str:
        lines = [f"Causal benchmark -- {out['domain']} -- {out['model_label']} ({out['backend']})", "=" * 72]
        for lv, s in out["levels"].items():
            extra = f"  need ~{s['answers_needed_for_safe']} answers" if s["answers_needed_for_safe"] else ""
            lines.append(f"{lv.upper():<15} acc={s['accuracy']:6.1%}  lower95={s['wilson_lower']:6.1%}  "
                         f"n={s['n']:<3} -> {s['label']}{extra}")
        lines.append("-" * 72)
        for uc, g in out["use_cases"].items():
            lines.append(f"use case {uc:<18} {'SHIP' if g['ship'] else 'BLOCKED by ' + ', '.join(g['blocked_by'])}")
        for r in out["regression"]:
            lines.append(f"REGRESSION: {r}")
        return "\n".join(lines)

    # -- feedback -------------------------------------------------------------------------------
    def override(self, qid: str, answer: str, correct: bool, grader: str = "human") -> dict:
        if qid not in self.questions:
            raise KeyError(qid)
        self.memory.add_fact(f"override:{_okey(qid, answer)}", "verdict", bool(correct), source=grader)
        return {"question": qid, "answer": answer, "correct": correct}

    def rerun(self, run_id: str) -> dict:
        d = self.memory.get_decision(run_id)
        if not d or d["features"]["answers"] is None:
            raise KeyError(run_id)
        return self.benchmark(d["features"]["model_label"] + " (regraded)", "answers", d["features"]["answers"])
