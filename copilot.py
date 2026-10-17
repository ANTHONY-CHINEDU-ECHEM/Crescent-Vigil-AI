"""The Crescent Vigil copilot: a small state machine over one attendance.

    guard -> situate -> assess_risk -> plan_actions -> ground_actions
          -> answer_question -> verify -> audit

Each node reads and writes one shared state dictionary and records its timing,
so the interface can show exactly what ran. The guard can short circuit the
question path (injection, off topic) but never the clinical actions: a
clinician asking an off topic question still sees what is due for the patient.

Grounding rules:
* the patient's signed plan outranks generic guidance for analgesia;
* every sentence cites the record, the plan, a history passage, the model
  output or a guidance card, and is verified before it is shown;
* no sentence ever contains a dose.
"""
from __future__ import annotations

import json
import os
import re
import time
from functools import lru_cache

import numpy as np

from .. import config as C
from ..knowledge.cards import history_passages, parse_cards, plan_passages, source_text
from ..retrieval.index import Index, Ranker, phase_from_minute, situations_for
from ..retrieval.text import tokens
from . import audit
from .engine import actions_for, record_evidence
from .guard import check
from .verifier import verify

SENT = re.compile(r"(?<=[.!?])\s+(?=[A-Z])")
# Stemmed tokens (see retrieval.text) that mark a question about analgesia choice or about past attendances.
ANALGESIA_WORDS = {"analgesia", "opioid", "morphine", "diamorphine", "oxycodone", "plan", "route", "dose", "agent",
                   "first", "line", "subcutaneou", "intravenou", "oral"}
HISTORY_WORDS = {"previou", "last", "history", "time", "usual", "prior", "earlier"}

# Situations implied by the live record, used by retrieval alongside the question.
def record_situations(snap: dict) -> list[str]:
    s = set()
    c = snap["attendance"]["complaint"]
    s |= {"pain"} if c in ("pain", "chest", "abdominal", "priapism") else set()
    s |= {"chest"} if c == "chest" else set()
    s |= {"neuro", "stroke"} if c == "neuro" else set()
    s |= {"priapism"} if c == "priapism" else set()
    s |= {"abdominal"} if c == "abdominal" else set()
    s |= {"fever", "infection"} if c == "fever" else set()
    v = snap["vitals"]
    if v:
        if v["temp"] >= C.PROTOCOL.temp_flag:
            s |= {"fever", "infection"}
        if v["spo2"] < C.PROTOCOL.spo2_flag or snap["patient"]["baseline_spo2"] - v["spo2"] >= C.PROTOCOL.spo2_drop_flag:
            s |= {"chest", "deterioration"}
    if snap["plan"]:
        s.add("plan")
    return sorted(s)


def best_sentence(text: str, qtoks: set[str]) -> str:
    sents = [x.strip() for x in SENT.split(text) if x.strip()]
    if not sents:
        return text
    scores = [len(set(tokens(x)) & qtoks) for x in sents]
    return sents[int(np.argmax(scores))]


class Copilot:
    def __init__(self, timeline=None, index: Index | None = None, ranker: Ranker | None = None, model=None,
                 audit_path=C.AUDIT_LOG, writer=None, log=True):
        from ..timeline.store import default_timeline
        self.tl = timeline or default_timeline()
        self.index = index or Index.build(parse_cards())
        self.ranker = ranker or (Ranker.load() if (C.INDEX / "ranker.json").exists() else Ranker())
        self.model = model
        if self.model is None and (C.MODELS / "acs_models.joblib").exists():
            from ..models.acs import ACSModel
            self.model = ACSModel()
        self.audit_path = audit_path
        self.log = log
        self.writer = writer or default_writer()
        self.cards = {p.pid: p for p in self.index.passages}
        self._cache = {}

    # ---- retrieval helpers -------------------------------------------
    def rank(self, query: str, minute, admitted_min, sits, mask=None):
        key = (query, phase_from_minute(minute, admitted_min), tuple(sits), tuple(mask or ()))
        if key not in self._cache:
            F = self.index.features(query, minute, admitted_min, sits)
            s = self.ranker.score(F, mask)
            order = np.argsort(-s, kind="stable")
            self._cache[key] = [(self.index.passages[i].pid, float(s[i])) for i in order[:8]]
        return self._cache[key]

    # ---- nodes -----------------------------------------------------------
    def run(self, attendance_id: str, now_min: float, question: str = "", ablate: dict | None = None) -> dict:
        ablate = ablate or {}
        st = {"attendance_id": attendance_id, "now_min": float(now_min), "question": question, "trace": []}

        def node(name, fn):
            t = time.perf_counter()
            fn(st)
            st["trace"].append({"node": name, "ms": round(1000 * (time.perf_counter() - t), 2)})

        node("guard", self.n_guard)
        node("situate", self.n_situate)
        node("assess_risk", lambda s: self.n_risk(s, ablate))
        node("plan_actions", self.n_actions)
        node("ground_actions", lambda s: self.n_ground(s, ablate))
        node("answer_question", lambda s: self.n_answer(s, ablate))
        node("verify", lambda s: self.n_verify(s, ablate))
        node("audit", self.n_audit)
        return self.result(st)

    def n_guard(self, st):
        g = check(st["question"])
        st["guard"] = {"redacted": g.redacted, "sha256": g.original_sha256, "redactions": g.redactions, "flags": g.flags}

    def n_situate(self, st):
        snap = self.tl.snapshot(st["attendance_id"], st["now_min"]).to_dict()
        st["snap"] = snap
        st["phase"] = phase_from_minute(st["now_min"], snap["derived"]["admitted_min"])
        st["record_situations"] = record_situations(snap)

    def n_risk(self, st, ablate):
        st["risk"] = None
        if self.model is None or ablate.get("no_model"):
            return
        from ..models.features import snapshot_features
        f = snapshot_features(st["snap"])
        if f is not None:
            r = self.model.predict(f)
            r["features"] = f
            st["risk"] = r

    def n_actions(self, st):
        st["actions"] = [a.to_dict() for a in actions_for(st["snap"], st["risk"])]
        st["evidence"] = record_evidence(st["snap"], st["risk"])
        for p in plan_passages(st["snap"]["plan"]) + history_passages(st["snap"]["history"], st["snap"]["patient"]["patient_id"]):
            st["evidence"][p.pid] = p.text
            st.setdefault("patient_passages", []).append(p.to_dict())
        st.setdefault("patient_passages", [])

    def n_ground(self, st, ablate):
        snap = st["snap"]
        adm = snap["derived"]["admitted_min"]
        mask = ablate.get("mask")
        sits = [] if ablate.get("no_record_situations") else st["record_situations"]
        sentences = []
        for a in st["actions"]:
            ranked = self.rank(a["query"], st["now_min"], adm, sits, mask)
            card = ranked[0][0]
            a["card"] = card
            a["card_score"] = round(ranked[0][1], 3)
            st["evidence"][card] = self.cards[card].text
            cites = list(a["evidence"]) + list(a["plan_cite"]) + [card]
            if ablate.get("no_plan_first") and a["plan_cite"]:
                cites = list(a["evidence"]) + [card]
            sentences.append({"text": a["text"], "cites": cites, "kind": "action", "code": a["code"], "section": "actions"})
        st["sentences"] = sentences

    def n_answer(self, st, ablate):
        q = st["guard"]["redacted"].strip()
        flags = st["guard"]["flags"]
        st["retrieved"] = []
        if not q:
            return
        out = []
        def system(text):
            out.append({"text": text, "cites": [], "kind": "system", "section": "answer"})
        def cite_card(pid, sentence=None):
            p = self.cards[pid]
            st["evidence"][pid] = p.text
            out.append({"text": sentence or p.body, "cites": [pid], "kind": "guidance", "section": "answer"})
        if "injection" in flags:
            system("This request asks the system to set aside its instructions or the patient's plan, so it has not been acted on. The actions above still apply.")
            st["answer"] = out
            return
        if "off_topic" in flags:
            system("This question is outside what Crescent Vigil covers: emergency and ward care of adults with sickle cell disease.")
            st["answer"] = out
            return
        if "crisis" in flags:
            cite_card("G063")
        if "paediatric_scope" in flags:
            cite_card("G059")
        if "pregnancy_scope" in flags:
            cite_card("G060")
        plan = st["snap"]["plan"]
        if "dose_request" in flags:
            cite_card("G062")
            if plan:
                out.append({"text": f"The signed plan names {plan['first_line_agent']} by the {plan['route']} route; {plan['dose_text'].lower()}.",
                            "cites": [f"{plan['plan_id']}.A"], "kind": "plan", "section": "answer"})
            st["answer"] = out
            return
        if "pethidine" in flags:
            cite_card("G007")
        adm = st["snap"]["derived"]["admitted_min"]
        qt = set(tokens(q))
        sits = [] if ablate.get("no_record_situations") else st["record_situations"]
        ranked = self.rank(q, st["now_min"], adm, sits, ablate.get("mask"))
        st["retrieved"] = [{"pid": pid, "score": round(s, 3), "title": self.cards[pid].title} for pid, s in ranked[:5]]
        # Plan first: analgesia questions are answered from the patient's own plan before any guidance.
        if plan and not ablate.get("no_plan_first") and (qt & ANALGESIA_WORDS):
            out.append({"text": f"The signed plan names {plan['first_line_agent']} by the {plan['route']} route as first line; "
                                f"the dose is as written in the signed individual plan.",
                        "cites": [f"{plan['plan_id']}.A"], "kind": "plan", "section": "answer"})
            if plan["avoid"]:
                out.append({"text": "The plan says to avoid " + ", ".join(plan["avoid"]) + ".",
                            "cites": [f"{plan['plan_id']}.B"], "kind": "plan", "section": "answer"})
        if qt & HISTORY_WORDS and st["snap"]["history"]["attendances"]:
            hp = [p for p in st["patient_passages"] if p["kind"] == "history"]
            if hp:
                out.append({"text": hp[0]["body"], "cites": [hp[0]["pid"]], "kind": "history", "section": "answer"})
        used = {c for s in out for c in s["cites"]}
        top = ranked[0][1]
        written = self.writer(q, [(pid, self.cards[pid]) for pid, s in ranked[:3] if pid not in used and s >= top - 2.0]) if self.writer else None
        if written:
            for s in written:
                for c in s["cites"]:
                    if c in self.cards:
                        st["evidence"][c] = self.cards[c].text
                out.append({**s, "kind": "guidance", "section": "answer"})
        else:
            for pid, s in ranked[:3]:
                if pid in used or s < top - 2.0 or len([o for o in out if o["kind"] == "guidance"]) >= 2:
                    continue
                cite_card(pid, best_sentence(self.cards[pid].body, qt))
        st["answer"] = out

    def n_verify(self, st, ablate):
        plan = st["snap"]["plan"]
        forbidden = {"pethidine"} | ({x for x in plan["avoid"] if x != "NSAIDs"} if plan else set())
        agent = plan["first_line_agent"] if plan else None
        allsent = st["sentences"] + st.get("answer", [])
        if ablate.get("no_verifier"):
            kept, dropped = [dict(s, verified=None) for s in allsent], []
        else:
            kept, dropped = verify(allsent, st["evidence"], forbidden, agent)
        codes_kept = {s.get("code") for s in kept}
        for d in dropped:
            if d.get("code") and d["code"] not in codes_kept:
                kept.append({"text": "One step could not be verified against its sources and is withheld; check it with the haematology team.",
                             "cites": [], "kind": "system", "section": d["section"], "code": d["code"], "withheld": True})
        st["final"] = kept
        st["dropped"] = dropped

    def n_audit(self, st):
        rec = {"attendance_id": st["attendance_id"], "now_min": st["now_min"], "question_redacted": st["guard"]["redacted"],
               "question_sha256": st["guard"]["sha256"], "redactions": st["guard"]["redactions"], "flags": st["guard"]["flags"],
               "actions": [a["code"] for a in st["actions"]],
               "overdue": [a["code"] for a in st["actions"] if a["overdue"]],
               "sentences": len(st["final"]), "dropped": len(st["dropped"]),
               "risk_24h": round(st["risk"]["risk_24h"], 4) if st["risk"] else None}
        st["audit"] = audit.append(rec, self.audit_path) if self.log else rec

    def result(self, st) -> dict:
        snap = st["snap"]
        risk = st["risk"]
        if risk:
            risk = {k: v for k, v in risk.items() if k != "features"}
        cited = sorted({c for s in st["final"] for c in s["cites"]})
        sources = []
        for c in cited:
            if c in self.cards:
                p = self.cards[c]
                sources.append({"id": c, "kind": "guidance", "title": p.title, "text": p.body, "source": source_text(p.source) if p.source.startswith("S") else p.source})
            elif c.startswith(("R.", "M.")):
                sources.append({"id": c, "kind": "record" if c.startswith("R.") else "model", "title": c, "text": st["evidence"][c]})
            else:
                pp = next((p for p in st["patient_passages"] if p["pid"] == c), None)
                if pp:
                    sources.append({"id": c, "kind": pp["kind"], "title": pp["title"], "text": pp["body"]})
        return {
            "attendance_id": st["attendance_id"], "now_min": st["now_min"], "phase": st["phase"],
            "patient": snap["patient"], "attendance": snap["attendance"], "plan": snap["plan"], "derived": snap["derived"],
            "vitals": snap["vitals"], "vitals_series": snap["vitals_series"], "labs": {k: v for k, v in snap["labs"].items() if k != "series"},
            "history": snap["history"], "guard": st["guard"], "risk": risk, "actions": st["actions"],
            "sentences": st["final"], "dropped": st["dropped"], "sources": sources, "retrieved": st["retrieved"],
            "record_situations": st["record_situations"], "trace": st["trace"], "audit_hash": st["audit"].get("hash"),
        }


def default_writer():
    """Optional generative writer through a local Ollama server; extractive when unset."""
    if os.environ.get("CRESCENT_LLM", "").lower() != "ollama":
        return None
    import httpx
    url = os.environ.get("OLLAMA_URL", "http://localhost:11434") + "/api/generate"
    model = os.environ.get("CRESCENT_LLM_MODEL", "llama3.1:8b")

    def write(question, passages):
        if not passages:
            return None
        ev = "\n".join(f"[{pid}] {p.text}" for pid, p in passages)
        prompt = ("Answer the clinician's question in at most three short sentences using only the evidence below. "
                  "End every sentence with the id of the evidence it uses in square brackets. Never give drug doses.\n\n"
                  f"Evidence:\n{ev}\n\nQuestion: {question}\nAnswer:")
        try:
            r = httpx.post(url, json={"model": model, "prompt": prompt, "stream": False}, timeout=30)
            text = r.json().get("response", "")
        except Exception:
            return None
        out = []
        for s in SENT.split(text.strip()):
            ids = re.findall(r"\[(G\d{3})\]", s)
            clean = re.sub(r"\s*\[[^\]]+\]", "", s).strip()
            if clean:
                out.append({"text": clean, "cites": ids})
        return out or None
    return write


@lru_cache(maxsize=1)
def default_copilot() -> Copilot:
    return Copilot()
