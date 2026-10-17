"""FastAPI service: the copilot, the timeline, the audit log and the reports.

Run with `make serve` (uvicorn on port 8000). The built interface in web/dist
is served from the same origin.
"""
from __future__ import annotations

import json
from functools import lru_cache

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .. import __version__, config as C
from ..agent import audit

app = FastAPI(title="Crescent Vigil AI", version=__version__,
              description="Time critical decision support for vaso occlusive crises with care plan first retrieval, "
                          "an acute chest syndrome deterioration model and an analgesia equity audit. Research and education only.")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET", "POST"], allow_headers=["*"])


class CopilotRequest(BaseModel):
    attendance_id: str = Field(..., examples=["ATT0000123"])
    now_min: float = Field(..., ge=0, le=72 * 60 + 600, description="Minutes since arrival")
    question: str = Field("", max_length=1000)


@lru_cache(maxsize=1)
def copilot():
    from ..agent.copilot import Copilot
    return Copilot()


def _json(path):
    if not path.exists():
        raise HTTPException(404, f"{path.name} has not been built yet")
    return json.loads(path.read_text())


@app.get("/api/health")
def health():
    return {"status": "ok", "version": __version__, "model": (C.MODELS / "acs_models.joblib").exists(),
            "index": (C.INDEX / "ranker.json").exists(), "audit_chain": audit.verify_chain()}


@app.post("/api/copilot")
def run_copilot(req: CopilotRequest):
    cp = copilot()
    if req.attendance_id not in cp.tl.att.index:
        raise HTTPException(404, "unknown attendance")
    return cp.run(req.attendance_id, req.now_min, req.question)


@app.get("/api/attendances")
def attendances(split: str | None = None, site: str | None = None, complaint: str | None = None,
                admitted: bool | None = None, acs: bool | None = None, limit: int = Query(50, le=500)):
    a = copilot().tl.att
    if split:
        a = a[a.split == split]
    if site:
        a = a[a.site == site]
    if complaint:
        a = a[a.complaint == complaint]
    if admitted is not None:
        a = a[a.admitted == admitted]
    if acs is not None:
        a = a[a.acs_72h == acs]
    cols = ["attendance_id", "patient_id", "site", "arrival", "complaint", "triage_category", "plan_visible", "admitted",
            "acs_72h", "door_to_analgesia_min", "split"]
    return json.loads(a[cols].head(limit).to_json(orient="records", date_format="iso"))


@app.get("/api/attendance/{attendance_id}")
def attendance(attendance_id: str):
    tl = copilot().tl
    if attendance_id not in tl.att.index:
        raise HTTPException(404, "unknown attendance")
    ev = tl.ev.get(attendance_id)
    obs = tl.obs.get(attendance_id)
    labs = tl.labs.get(attendance_id)
    return {"events": json.loads(ev.to_json(orient="records")) if ev is not None else [],
            "admitted_min": tl.admitted_min(attendance_id),
            "obs": json.loads(obs.to_json(orient="records")) if obs is not None else [],
            "labs": json.loads(labs.to_json(orient="records")) if labs is not None else []}


@app.get("/api/cards")
def cards():
    return _json(C.INDEX / "guidance_cards.json")


@app.get("/api/equity")
def equity():
    return _json(C.REPORTS / "equity_audit.json")


@app.get("/api/evaluation")
def evaluation():
    return _json(C.REPORTS / "evaluation_summary.json")


@app.get("/api/model")
def model():
    return _json(C.MODELS / "training_report.json")


@app.get("/api/audit")
def audit_log(limit: int = Query(100, le=1000)):
    return {"chain": audit.verify_chain(), "records": audit.read(limit=limit)[::-1]}


DIST = C.ROOT / "web" / "dist"
if DIST.exists():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets") if (DIST / "assets").exists() else None

    @app.get("/")
    def index():
        return FileResponse(DIST / "index.html")
