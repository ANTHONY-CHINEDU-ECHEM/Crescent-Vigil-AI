"""Event sourced timeline store.

Every attendance is a sequence of timestamped events plus observation and
laboratory series. A snapshot replays that sequence up to a chosen minute and
returns only what a clinician could have known at that moment: results are
visible from the time they are reported, not the time the sample was taken,
and outcomes that have not happened yet are never included.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import lru_cache

import duckdb
import numpy as np
import pandas as pd

from .. import config as C

ARRIVAL_VITALS_MIN = 6       # triage observations are recorded six minutes after arrival
ARRIVAL_LABS_MIN = 60        # arrival bloods are reported one hour after arrival
LATER_LAB_DELAY_MIN = 60     # ward bloods are reported one hour after sampling


def build_db(path=C.TIMELINE_DB) -> None:
    """Load the synthetic parquet tables into a DuckDB file with indexes."""
    if path.exists():
        path.unlink()
    con = duckdb.connect(str(path))
    for name in ("sites", "patients", "care_plans", "attendances", "events", "obs", "labs"):
        con.execute(f"CREATE TABLE {name} AS SELECT * FROM read_parquet('{(C.SYNTH / (name + '.parquet')).as_posix()}')")
    con.execute("CREATE INDEX ev_att ON events(attendance_id)")
    con.execute("CREATE INDEX obs_att ON obs(attendance_id)")
    con.execute("CREATE INDEX lab_att ON labs(attendance_id)")
    con.execute("CREATE INDEX att_id ON attendances(attendance_id)")
    con.execute("CREATE INDEX att_pt ON attendances(patient_id)")
    con.close()


@dataclass
class Snapshot:
    attendance_id: str
    now_min: float
    patient: dict
    attendance: dict
    plan: dict | None
    events: list
    vitals: dict
    vitals_series: list
    labs: dict
    history: dict
    derived: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {k: getattr(self, k) for k in ("attendance_id", "now_min", "patient", "attendance", "plan", "events",
                                              "vitals", "vitals_series", "labs", "history", "derived")}


class Timeline:
    """Read only access to the event store, from DuckDB or from in memory frames."""

    def __init__(self, path=C.TIMELINE_DB, frames: dict | None = None):
        if frames is None:
            if not path.exists():
                build_db(path)
            con = duckdb.connect(str(path), read_only=True)
            frames = {n: con.execute(f"SELECT * FROM {n}").df() for n in
                      ("patients", "care_plans", "attendances", "events", "obs", "labs", "sites")}
            con.close()
        self.f = frames
        self.att = frames["attendances"].set_index("attendance_id", drop=False)
        self.pat = frames["patients"].set_index("patient_id", drop=False)
        self.plan = frames["care_plans"].set_index("patient_id", drop=False)
        self.ev = {k: g for k, g in frames["events"].groupby("attendance_id", sort=False)}
        self.obs = {k: g for k, g in frames["obs"].groupby("attendance_id", sort=False)}
        self.labs = {k: g for k, g in frames["labs"].groupby("attendance_id", sort=False)}
        a = frames["attendances"].sort_values(["patient_id", "arrival"])
        self.by_patient = {k: g for k, g in a.groupby("patient_id", sort=False)}

    def admitted_min(self, att_id: str) -> float | None:
        ev = self.ev.get(att_id)
        if ev is None:
            return None
        r = ev[ev.event == "admitted"]
        return float(r.minute.iat[0]) if len(r) else None

    def snapshot(self, att_id: str, now_min: float) -> Snapshot:
        a = self.att.loc[att_id]
        p = self.pat.loc[a.patient_id]
        start = pd.Timestamp(C.START_DATE)
        patient = {
            "patient_id": p.patient_id, "age": int(a.age), "sex": p.sex, "genotype": p.genotype,
            "steady_state_hb": float(p.steady_state_hb), "baseline_spo2": float(p.baseline_spo2),
            "hydroxyurea": bool(p.hydroxyurea), "hbf_pct": float(p.hbf_pct), "prior_acs": int(p.prior_acs),
            "asthma": bool(p.asthma), "renal_impairment": bool(p.renal_impairment),
        }
        attendance = {
            "site": a.site, "arrival": str(a.arrival), "complaint": a.complaint,
            "triage_category": int(a.triage_category), "pain_score_arrival": float(a.pain_score_arrival),
            "crowding_index": float(a.crowding_index), "night": bool(a.night),
            "high_frequency_attender": bool(a.high_frequency_attender), "prior_attend_365d": int(a.prior_attend_365d),
        }
        plan = None
        if bool(a.plan_visible) and a.patient_id in self.plan.index:
            pl = self.plan.loc[a.patient_id]
            age_days = int((pl.reviewed_days_before_2021 + (pd.Timestamp(a.arrival) - start).days) % pl.review_cycle_days)
            plan = {
                "plan_id": pl.plan_id, "first_line_agent": pl.first_line_agent, "route": pl.route,
                "adjuncts": [x for x in pl.adjuncts.split(";") if x], "avoid": [x for x in pl.avoid.split(";") if x],
                "intolerance": pl.intolerance, "notes": pl.notes, "reassess_min": int(pl.reassess_min),
                "dose_text": pl.dose_text, "days_since_review": age_days,
            }
        ev = self.ev.get(att_id, pd.DataFrame(columns=["minute", "event", "payload"]))
        ev = ev[ev.minute <= now_min]
        events = [{"minute": float(m), "event": e, **json.loads(pl)} for m, e, pl in zip(ev.minute, ev.event, ev.payload)]

        series = []
        if now_min >= ARRIVAL_VITALS_MIN:
            series.append({"minute": ARRIVAL_VITALS_MIN, "spo2": float(a.spo2_arrival), "rr": float(a.rr_arrival),
                           "hr": float(a.hr_arrival), "temp": float(a.temp_arrival), "pain": float(a.pain_score_arrival),
                           "opioid_load": 0.0, "source": "triage"})
        adm = self.admitted_min(att_id)
        if adm is not None and att_id in self.obs:
            o = self.obs[att_id]
            mins = adm + o.hour.to_numpy() * 60
            keep = mins <= now_min
            for (_, r), m in zip(o[keep].iterrows(), mins[keep]):
                series.append({"minute": float(m), "spo2": float(r.spo2), "rr": float(r.rr), "hr": float(r.hr),
                               "temp": float(r.temp), "pain": float(r.pain), "opioid_load": float(r.opioid_load),
                               "spirometry_done": bool(r.spirometry_done), "source": "ward", "hour": float(r.hour)})
        vitals = series[-1] if series else {}

        labs = {}
        if now_min >= ARRIVAL_LABS_MIN:
            labs = {"minute": ARRIVAL_LABS_MIN, "hb": float(a.hb_arrival), "wbc": float(a.wbc_arrival),
                    "plt": float(a.plt_arrival), "retic": float(a.retic_arrival), "ldh": float(a.ldh_arrival),
                    "bili": float(a.bili_arrival), "crp": float(a.crp_arrival)}
        lab_series = [dict(labs)] if labs else []
        if adm is not None and att_id in self.labs:
            L = self.labs[att_id]
            for _, r in L.iterrows():
                m = adm + r.hour * 60 + LATER_LAB_DELAY_MIN
                if r.hour > 0 and m <= now_min:
                    d = {"minute": float(m), "hb": float(r.hb), "wbc": float(r.wbc), "plt": float(r.plt),
                         "crp": float(r.crp), "ldh": float(r.ldh)}
                    lab_series.append(d)
                    labs = {**labs, **d}
        labs["series"] = lab_series

        # History: previous attendances of this patient before this arrival.
        h = self.by_patient[a.patient_id]
        prev = h[h.arrival < a.arrival]
        history = {
            "attendances": int(len(prev)),
            "admissions": int(prev.admitted.sum()),
            "acs_after_admission": int(prev.acs_72h.sum()),
            "acs_at_arrival": int(prev.acs_at_arrival.sum()),
            "median_door_to_analgesia_min": float(prev.door_to_analgesia_min.median()) if prev.door_to_analgesia_min.notna().any() else None,
            "recent": [
                {"arrival": str(r.arrival)[:10], "complaint": r.complaint, "admitted": bool(r.admitted),
                 "acs": bool(r.acs_72h or r.acs_at_arrival), "first_agent": r.first_agent, "first_route": r.first_route,
                 "door_to_analgesia_min": None if np.isnan(r.door_to_analgesia_min) else float(r.door_to_analgesia_min),
                 "acs_diagnosis_h": None if np.isnan(r.acs_diagnosis_h) else float(r.acs_diagnosis_h)}
                for _, r in prev.tail(5).iloc[::-1].iterrows()
            ],
        }
        derived = derive(events, adm, now_min)
        return Snapshot(att_id, float(now_min), patient, attendance, plan, events, vitals, series, labs, history, derived)


def derive(events: list, admitted_min, now_min: float) -> dict:
    first = next((e for e in events if e["event"] == "analgesia_given"), None)
    re = [e for e in events if e["event"] == "pain_reassessed"]
    adm = next((e for e in events if e["event"] == "admitted"), None)
    acs = next((e for e in events if e["event"] == "acs_diagnosed"), None)
    left = any(e["event"] == "left_department" for e in events)
    disch = any(e["event"] == "discharged" for e in events)
    return {
        "analgesia_given_min": first["minute"] if first else None,
        "analgesia_agent": first.get("agent") if first else None,
        "analgesia_route": first.get("route") if first else None,
        "reassessed_min": re[0]["minute"] if re else None,
        "admitted_min": adm["minute"] if adm else None,
        "hours_since_admission": (now_min - adm["minute"]) / 60 if adm else None,
        "acs_diagnosed_min": acs["minute"] if acs else None,
        "left_department": left,
        "discharged": disch,
    }


def phase_of(now_min: float, admitted_min: float | None) -> str:
    if admitted_min is not None and now_min >= admitted_min:
        h = (now_min - admitted_min) / 60
        return "ward" if h < 24 else "late"
    if now_min <= 30:
        return "arrival"
    return "early" if now_min <= 120 else "ward"


@lru_cache(maxsize=1)
def default_timeline() -> Timeline:
    return Timeline()
