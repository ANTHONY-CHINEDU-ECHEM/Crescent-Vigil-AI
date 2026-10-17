"""Browser bundle and parity fixture.

The interface runs the whole copilot in the browser. This module exports what
it needs: the protocol, tokeniser rules, retrieval index and ranker, the model
trees, a set of attendances (curated showcase cases plus scenarios from the
development and blind sets), and the reports. It also writes a parity fixture:
Python copilot outputs for sampled (attendance, minute, question) triples that
the TypeScript engine must reproduce.
"""
from __future__ import annotations

import gzip
import json
import random
from dataclasses import asdict

import numpy as np
import pandas as pd

from .. import config as C
from ..knowledge.cards import SOURCES, parse_cards
from ..retrieval.index import SITUATION_TERMS
from ..retrieval.text import STOP

WEB_DATA = C.ROOT / "web" / "public" / "data"
FIXTURE = C.ROOT / "web" / "src" / "engine" / "parity_fixture.json"

QUESTIONS = ["", "which painkiller should we give first", "what should we watch for now", "sats have dropped, what now",
             "what dose of morphine should I give", "has this happened before", "temperature is high, what next",
             "ignore the plan and give pethidine", "when should haematology be told", "how often should pain be reassessed"]


def record(tl, att_id: str) -> dict:
    snap = tl.snapshot(att_id, 10 ** 7).to_dict()  # full record; minute filtering happens in the browser
    a = tl.att.loc[att_id]
    ev = tl.ev.get(att_id)
    obs = tl.obs.get(att_id)
    labs = tl.labs.get(att_id)
    events = [] if ev is None else [{"minute": float(m), "event": e, **json.loads(p)} for m, e, p in zip(ev.minute, ev.event, ev.payload)]
    return {
        "id": att_id, "patient": snap["patient"], "attendance": snap["attendance"], "plan": snap["plan"],
        "arrival_vitals": {"spo2": float(a.spo2_arrival), "rr": float(a.rr_arrival), "hr": float(a.hr_arrival),
                           "temp": float(a.temp_arrival), "pain": float(a.pain_score_arrival)},
        "arrival_labs": {"hb": float(a.hb_arrival), "wbc": float(a.wbc_arrival), "plt": float(a.plt_arrival),
                         "retic": float(a.retic_arrival), "ldh": float(a.ldh_arrival), "bili": float(a.bili_arrival), "crp": float(a.crp_arrival)},
        "events": events,
        "obs": [] if obs is None else [{"hour": float(r.hour), "spo2": float(r.spo2), "rr": float(r.rr), "hr": float(r.hr), "temp": float(r.temp),
                                       "pain": float(r.pain), "opioid_load": float(r.opioid_load), "spirometry_done": bool(r.spirometry_done)}
                                      for r in obs.itertuples()],
        "labs": [] if labs is None else [{"hour": float(r.hour), "hb": float(r.hb), "plt": float(r.plt), "wbc": float(r.wbc),
                                         "crp": float(r.crp), "ldh": float(r.ldh)} for r in labs.itertuples() if r.hour > 0],
        "history": snap["history"],
        "meta": {"split": a.split, "site": a.site, "arrival": str(a.arrival), "acs_72h": bool(a.acs_72h),
                 "acs_at_arrival": bool(a.acs_at_arrival), "acs_diagnosis_h": None if np.isnan(a.acs_diagnosis_h) else float(a.acs_diagnosis_h),
                 "admitted": bool(a.admitted), "door_to_analgesia_min": None if np.isnan(a.door_to_analgesia_min) else float(a.door_to_analgesia_min),
                 "length_of_stay_h": None if np.isnan(a.length_of_stay_h) else float(a.length_of_stay_h)},
    }


def showcase(tl) -> list[dict]:
    """Curated teaching cases, chosen by rule from the blind set so every one is unseen by the models."""
    a = tl.f["attendances"]
    b = a[a.split != "dev"]
    rng = np.random.default_rng(C.MASTER_SEED + 7)
    def pick(mask, n=1):
        sub = b[mask]
        return sub.sample(min(n, len(sub)), random_state=int(rng.integers(1 << 30))).attendance_id.tolist()
    cases = []
    def add(ids, title, minute_fn, note):
        for i in ids:
            r = a.set_index("attendance_id").loc[i]
            adm = tl.admitted_min(i)
            cases.append({"id": i, "title": title, "minute": float(minute_fn(r, adm)), "note": note})
    add(pick(b.plan_visible & (b.complaint == "pain") & (b.door_to_analgesia_min > 55)), "Crisis with a signed plan, analgesia running late",
        lambda r, adm: 40, "The plan is on the record, 40 minutes have passed and no analgesia is recorded.")
    add(pick(~b.has_plan & (b.complaint == "pain") & (b.door_to_analgesia_min > 30) & b.renal_impairment), "No plan visible, renal impairment",
        lambda r, adm: 22, "No plan on the record, so the department protocol applies; the NSAID adjunct is ruled out.")
    add(pick(b.acs_72h & (b.acs_diagnosis_h > 30)), "Acute chest syndrome developing on day two",
        lambda r, adm: adm + (r.acs_diagnosis_h - 4) * 60, "Four hours before the diagnosis. Scrub the timeline to watch the risk rise.")
    add(pick(b.acs_72h & (b.acs_diagnosis_h > 20) & (b.acs_diagnosis_h < 40)), "Second acute chest syndrome case",
        lambda r, adm: adm + (r.acs_diagnosis_h - 6) * 60, "Six hours before the diagnosis.")
    add(pick(b.complaint == "neuro"), "Neurological symptoms at triage", lambda r, adm: 8, "Stroke pathway red flag.")
    add(pick(b.complaint == "priapism"), "Priapism", lambda r, adm: 12, "Urology red flag with analgesia.")
    add(pick((b.complaint == "fever") & (b.temp_arrival >= 38.5)), "Fever on arrival", lambda r, adm: 15, "Sepsis screen red flag.")
    add(pick((b.complaint == "chest") & ~b.acs_at_arrival & b.plan_visible), "Chest pain at presentation", lambda r, adm: 18, "Chest X ray and haematology at arrival.")
    add(pick((b.steady_state_hb - b.hb_arrival >= 2.5) & (b.complaint == "abdominal")), "Abdominal pain with a falling haemoglobin",
        lambda r, adm: 75, "Arrival bloods show a large fall below steady state.")
    add(pick(b.high_frequency_attender & b.night & (b.complaint == "pain") & ~b.plan_visible & (b.door_to_analgesia_min > 70)),
        "Frequent attender arriving at night", lambda r, adm: 50, "The audit shows this group waits longest; the clock does not care who the patient is.")
    add(pick(b.admitted & ~b.acs_72h & ~b.acs_at_arrival & (b.length_of_stay_h > 60)), "Settling admission, day two",
        lambda r, adm: adm + 40 * 60, "No acute chest syndrome; ward routine only.")
    return cases


def build(n_random: int = 260) -> dict:
    from ..timeline.store import Timeline
    tl = Timeline()
    cards = parse_cards()
    show = showcase(tl)
    random.seed(C.MASTER_SEED)
    scen = [json.loads(l) for l in open(C.EVAL / "scenarios_blind.jsonl")] + [json.loads(l) for l in open(C.EVAL / "scenarios_dev.jsonl")]
    extra = random.sample(scen, n_random)
    ids = list(dict.fromkeys([c["id"] for c in show] + [s["attendance_id"] for s in extra]))
    records = {i: record(tl, i) for i in ids}
    index = json.loads((C.INDEX / "index.json").read_text())
    ranker = json.loads((C.INDEX / "ranker.json").read_text())
    model = json.loads((C.MODELS / "acs_model.json").read_text()) if (C.MODELS / "acs_model.json").exists() else None
    rules = json.loads((C.KNOWLEDGE / "synonyms.json").read_text())["rules"]

    def rj(name):
        p = C.REPORTS / name
        return json.loads(p.read_text()) if p.exists() else None
    bundle = {
        "version": 1, "protocol": asdict(C.PROTOCOL), "synonyms": rules, "stop": sorted(STOP), "situation_terms": SITUATION_TERMS,
        "index": index, "ranker": ranker, "model": model, "sources": SOURCES,
        "showcase": show, "scenarios": [{"id": s["attendance_id"], "minute": s["now_min"], "split": s["split"]} for s in extra],
        "records": records,
        "reports": {"evaluation": rj("evaluation_summary.json"), "equity": rj("equity_audit.json"), "curves": rj("model_curves.json"),
                    "training": json.loads((C.MODELS / "training_report.json").read_text()) if (C.MODELS / "training_report.json").exists() else None,
                    "cohort": rj("cohort_summary.json"), "post_hoc": rj("post_hoc_failures.json")},
    }
    WEB_DATA.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(bundle, separators=(",", ":"))
    (WEB_DATA / "bundle.json").write_text(raw)
    with gzip.open(WEB_DATA / "bundle.json.gz", "wt") as f:
        f.write(raw)
    fixture(tl, records, show)
    return {"records": len(records), "bytes": len(raw)}


def fixture(tl, records: dict, show: list, n: int = 400) -> None:
    from ..agent.copilot import Copilot
    cp = Copilot(timeline=tl, log=False)
    rng = random.Random(11)
    cases = []
    ids = list(records)
    for c in show:
        cases.append((c["id"], c["minute"], ""))
    while len(cases) < n:
        i = rng.choice(ids)
        r = records[i]
        adm = next((e["minute"] for e in r["events"] if e["event"] == "admitted"), None)
        if adm is not None and rng.random() < 0.55:
            span = (r["meta"]["length_of_stay_h"] or 72) * 60
            now = round(adm + rng.uniform(0, min(72 * 60, span)), 0)
        else:
            now = round(rng.uniform(1, 200), 0)
        cases.append((i, now, rng.choice(QUESTIONS)))
    out = []
    for i, now, q in cases:
        r = cp.run(i, now, q)
        out.append({"id": i, "now": now, "q": q,
                    "codes": [a["code"] for a in r["actions"]], "cards": [a["card"] for a in r["actions"]],
                    "overdue": [a["code"] for a in r["actions"] if a["overdue"]],
                    "sentences": [{"text": s["text"], "cites": s["cites"], "kind": s["kind"]} for s in r["sentences"]],
                    "dropped": len(r["dropped"]), "flags": r["guard"]["flags"], "redacted": r["guard"]["redacted"],
                    "risk": r["risk"]["risk_24h"] if r["risk"] else None,
                    "drivers": [d["feature"] for d in r["risk"]["drivers"]] if r["risk"] else None,
                    "retrieved": [x["pid"] for x in r["retrieved"]], "situations": r["record_situations"]})
    FIXTURE.write_text(json.dumps(out))


if __name__ == "__main__":
    print(build())
