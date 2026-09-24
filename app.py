"""
CausalGate API.   uvicorn app:app --reload    ->  http://127.0.0.1:8000/docs
"""

from __future__ import annotations

from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from gen4.api import common_router
from rubric import USE_CASES
from service import CausalGateService

service = CausalGateService()
app = FastAPI(title="CausalGate", version="2.0.0",
              description="Benchmark a model at each causal level (correlation, intervention, counterfactual), "
                          "gate deployment on evidence rather than point estimates, and answer which product "
                          "use cases the model is safe for.")
app.include_router(common_router(service, "causalgate"))


class BenchmarkIn(BaseModel):
    model_label: str
    backend: Literal["answers", "live", "recorded_v1"] = "answers"
    answers: dict[str, list[str]] | None = Field(
        None, description="Free-text answers per question id (C1..F3). Omit to use the bundled demo "
                          "answer set for model_label (demo-model-a / demo-model-b).")
    runs: int = Field(3, ge=1, le=10, description="Answers per question for backend=live")


class OverrideIn(BaseModel):
    question_id: str
    answer: str
    correct: bool
    grader: str = "human"


@app.get("/", tags=["ops"])
def root():
    return {"service": "CausalGate", "docs": "/docs",
            "flow": "GET /questions -> POST /benchmarks -> POST /overrides -> POST /benchmarks/{id}/rerun"}


@app.get("/questions", tags=["benchmark"])
def questions():
    return [{"id": q.id, "level": q.level.value, "question": q.question, "use_cases": q.use_cases}
            for q in service.questions.values()]


@app.get("/use-cases", tags=["benchmark"])
def use_cases():
    return USE_CASES


@app.post("/benchmarks", tags=["benchmark"])
def benchmark(body: BenchmarkIn):
    try:
        return service.benchmark(body.model_label, body.backend, body.answers, body.runs)
    except KeyError:
        raise HTTPException(404, f"no bundled answers for {body.model_label}; pass `answers`")
    except ValueError as e:
        raise HTTPException(422, str(e))


@app.get("/benchmarks/{run_id}", tags=["benchmark"])
def get_benchmark(run_id: str):
    d = service.memory.get_decision(run_id)
    if not d:
        raise HTTPException(404, "unknown run")
    return {"run_id": run_id, **d["output"]}


@app.post("/benchmarks/{run_id}/rerun", tags=["feedback"])
def rerun(run_id: str):
    try:
        return service.rerun(run_id)
    except KeyError:
        raise HTTPException(404, "unknown run or run has no stored answers")


@app.post("/overrides", tags=["feedback"])
def override(body: OverrideIn):
    try:
        return service.override(body.question_id, body.answer, body.correct, body.grader)
    except KeyError:
        raise HTTPException(404, "unknown question id")
