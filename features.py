"""Features for the deterioration models.

Two routes compute the same feature vector:

* `person_period_table` builds every (attendance, observation hour) row at once
  from the observation and laboratory tables, for training and evaluation.
* `snapshot_features` builds one row from a live snapshot, for the copilot.

A test asserts that both routes agree on sampled attendances, and the browser
port is checked against the same fixture.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .. import config as C

STATIC = ["age", "female", "severe_genotype", "hbf_pct", "hydroxyurea", "prior_acs_capped", "asthma", "history_acs",
          "high_frequency_attender", "renal_impairment", "complaint_abdominal", "complaint_fever", "complaint_other",
          "pain_arrival", "spo2_gap_arrival", "temp_arrival", "rr_arrival", "hr_arrival", "hb_drop_arrival",
          "wbc_arrival", "plt_arrival", "retic_arrival", "ldh_arrival", "crp_arrival"]
DYNAMIC = ["hours", "spo2", "spo2_gap", "spo2_change_8h", "spo2_min", "rr", "rr_change_8h", "hr", "hr_change_8h",
           "temp", "temp_max", "pain", "pain_change_8h", "opioid_load", "opioid_8h", "spirometry_frac",
           "lab_available", "lab_hb_change", "lab_plt_ratio", "lab_wbc_change", "lab_crp_change", "lab_ldh_ratio"]
FEATURES = STATIC + DYNAMIC
ADMISSION_FEATURES = STATIC

LAB_REPORT_DELAY_H = 1.0


def _history_acs(att: pd.DataFrame) -> pd.Series:
    a = att.sort_values(["patient_id", "arrival"])
    ev = (a.acs_72h.astype(int) + a.acs_at_arrival.astype(int))
    prev = ev.groupby(a.patient_id).cumsum() - ev
    return prev.reindex(att.index)


def static_frame(att: pd.DataFrame) -> pd.DataFrame:
    s = pd.DataFrame(index=att.index)
    s["age"] = att.age
    s["female"] = (att.sex == "F").astype(float)
    s["severe_genotype"] = att.severe_genotype.astype(float)
    s["hbf_pct"] = att.hbf_pct
    s["hydroxyurea"] = att.hydroxyurea.astype(float)
    s["prior_acs_capped"] = np.minimum(att.prior_acs, 4)
    s["asthma"] = att.asthma.astype(float)
    s["history_acs"] = _history_acs(att)
    s["high_frequency_attender"] = att.high_frequency_attender.astype(float)
    s["renal_impairment"] = att.renal_impairment.astype(float)
    s["complaint_abdominal"] = (att.complaint == "abdominal").astype(float)
    s["complaint_fever"] = (att.complaint == "fever").astype(float)
    s["complaint_other"] = (~att.complaint.isin(["pain", "abdominal", "fever"])).astype(float)
    s["pain_arrival"] = att.pain_score_arrival
    s["spo2_gap_arrival"] = att.baseline_spo2 - att.spo2_arrival
    s["temp_arrival"] = att.temp_arrival
    s["rr_arrival"] = att.rr_arrival
    s["hr_arrival"] = att.hr_arrival
    s["hb_drop_arrival"] = att.steady_state_hb - att.hb_arrival
    s["wbc_arrival"] = att.wbc_arrival
    s["plt_arrival"] = att.plt_arrival
    s["retic_arrival"] = att.retic_arrival
    s["ldh_arrival"] = att.ldh_arrival
    s["crp_arrival"] = att.crp_arrival
    return s


def person_period_table(att: pd.DataFrame, obs: pd.DataFrame, labs: pd.DataFrame) -> pd.DataFrame:
    """One row per admitted attendance and observation hour, with 24 h and 72 h labels."""
    a = att[att.admitted & ~att.acs_at_arrival].copy()
    st = static_frame(att).loc[a.index]
    st["attendance_id"] = a.attendance_id.to_numpy()
    o = obs[obs.attendance_id.isin(a.attendance_id)].sort_values(["attendance_id", "hour"]).copy()
    arr = a.set_index("attendance_id")
    g = o.groupby("attendance_id", sort=False)
    o["spo2_min"] = np.minimum(g.spo2.cummin(), o.attendance_id.map(arr.spo2_arrival))
    o["temp_max"] = np.maximum(g.temp.cummax(), o.attendance_id.map(arr.temp_arrival))
    o["spirometry_frac"] = g.spirometry_done.cumsum() / (g.cumcount() + 1)
    lag = o[["attendance_id", "hour", "spo2", "rr", "hr", "pain", "opioid_load"]].copy()
    lag["hour"] = lag.hour + 8
    o = o.merge(lag, on=["attendance_id", "hour"], how="left", suffixes=("", "_lag"))
    # At hours 0 and 4 the comparison point is the triage set at arrival.
    for col, acol in (("spo2", "spo2_arrival"), ("rr", "rr_arrival"), ("hr", "hr_arrival"), ("pain", "pain_score_arrival")):
        o[col + "_lag"] = o[col + "_lag"].fillna(o.attendance_id.map(arr[acol]))
    o["opioid_load_lag"] = o.opioid_load_lag.fillna(0.0)
    base = o.attendance_id.map(arr.baseline_spo2)
    d = pd.DataFrame({
        "attendance_id": o.attendance_id, "hours": o.hour, "spo2": o.spo2, "spo2_gap": base - o.spo2,
        "spo2_change_8h": o.spo2 - o.spo2_lag, "spo2_min": o.spo2_min, "rr": o.rr, "rr_change_8h": o.rr - o.rr_lag,
        "hr": o.hr, "hr_change_8h": o.hr - o.hr_lag, "temp": o.temp, "temp_max": o.temp_max, "pain": o.pain,
        "pain_change_8h": o.pain - o.pain_lag, "opioid_load": o.opioid_load, "opioid_8h": o.opioid_load - o.opioid_load_lag,
        "spirometry_frac": o.spirometry_frac,
    })
    # Latest ward laboratory result reported by this hour.
    L = labs[(labs.hour > 0) & labs.attendance_id.isin(a.attendance_id)].copy()
    L["avail_h"] = L.hour + LAB_REPORT_DELAY_H
    d["lab_available"] = 0.0
    for c in ("lab_hb_change", "lab_plt_ratio", "lab_wbc_change", "lab_crp_change", "lab_ldh_ratio"):
        d[c] = 0.0 if c.endswith("change") else 1.0
    for lh in (24, 48):
        Lh = L[L.hour == lh].set_index("attendance_id")
        avail = d.attendance_id.isin(Lh.index) & (d.hours >= lh + LAB_REPORT_DELAY_H)
        idx = d.attendance_id[avail]
        d.loc[avail, "lab_available"] = 1.0
        d.loc[avail, "lab_hb_change"] = Lh.hb.reindex(idx).to_numpy() - arr.hb_arrival.reindex(idx).to_numpy()
        d.loc[avail, "lab_plt_ratio"] = Lh.plt.reindex(idx).to_numpy() / arr.plt_arrival.reindex(idx).to_numpy()
        d.loc[avail, "lab_wbc_change"] = Lh.wbc.reindex(idx).to_numpy() - arr.wbc_arrival.reindex(idx).to_numpy()
        d.loc[avail, "lab_crp_change"] = Lh.crp.reindex(idx).to_numpy() - arr.crp_arrival.reindex(idx).to_numpy()
        d.loc[avail, "lab_ldh_ratio"] = Lh.ldh.reindex(idx).to_numpy() / arr.ldh_arrival.reindex(idx).to_numpy()
    d = d.merge(st, on="attendance_id", how="left")
    d["acs_72h"] = d.attendance_id.map(arr.acs_72h).astype(int)
    d["acs_diagnosis_h"] = d.attendance_id.map(arr.acs_diagnosis_h.where(arr.acs_72h))
    d = d[~(d.acs_diagnosis_h <= d.hours)].copy()  # stop once the diagnosis is made
    d["label_24h"] = ((d.acs_diagnosis_h > d.hours) & (d.acs_diagnosis_h <= d.hours + C.ALERT_HORIZON_H)).astype(int)
    d["split"] = d.attendance_id.map(arr.split)
    d["site"] = d.attendance_id.map(arr.site)
    d["patient_id"] = d.attendance_id.map(arr.patient_id)
    return d.reset_index(drop=True)


def snapshot_features(snap: dict) -> dict | None:
    """Feature row from a live snapshot, or None when the patient is not on the ward."""
    d = snap["derived"]
    if d["admitted_min"] is None or snap["now_min"] < d["admitted_min"]:
        return None
    ward = [v for v in snap["vitals_series"] if v.get("source") == "ward"]
    if not ward:
        return None
    pt, at = snap["patient"], snap["attendance"]
    tri = next(v for v in snap["vitals_series"] if v.get("source") == "triage")
    arrival_labs = snap["labs"]["series"][0]
    h = snap["history"]
    f = {
        "age": at.get("age", pt["age"]), "female": float(pt["sex"] == "F"),
        "severe_genotype": float(pt["genotype"] in ("HbSS", "HbSbeta0", "HbSD")), "hbf_pct": pt["hbf_pct"],
        "hydroxyurea": float(pt["hydroxyurea"]), "prior_acs_capped": min(pt["prior_acs"], 4), "asthma": float(pt["asthma"]),
        "history_acs": h["acs_after_admission"] + h["acs_at_arrival"],
        "high_frequency_attender": float(at["high_frequency_attender"]), "renal_impairment": float(pt["renal_impairment"]),
        "complaint_abdominal": float(at["complaint"] == "abdominal"), "complaint_fever": float(at["complaint"] == "fever"),
        "complaint_other": float(at["complaint"] not in ("pain", "abdominal", "fever")),
        "pain_arrival": at["pain_score_arrival"], "spo2_gap_arrival": pt["baseline_spo2"] - tri["spo2"],
        "temp_arrival": tri["temp"], "rr_arrival": tri["rr"], "hr_arrival": tri["hr"],
        "hb_drop_arrival": pt["steady_state_hb"] - arrival_labs["hb"], "wbc_arrival": arrival_labs["wbc"],
        "plt_arrival": arrival_labs["plt"], "retic_arrival": arrival_labs["retic"], "ldh_arrival": arrival_labs["ldh"],
        "crp_arrival": arrival_labs["crp"],
    }
    cur = ward[-1]
    hours = cur["hour"]
    lag = next((v for v in ward if v["hour"] == hours - 8), tri)
    allv = [tri] + ward
    f.update({
        "hours": hours, "spo2": cur["spo2"], "spo2_gap": pt["baseline_spo2"] - cur["spo2"],
        "spo2_change_8h": cur["spo2"] - lag["spo2"], "spo2_min": min(v["spo2"] for v in allv), "rr": cur["rr"],
        "rr_change_8h": cur["rr"] - lag["rr"], "hr": cur["hr"], "hr_change_8h": cur["hr"] - lag["hr"],
        "temp": cur["temp"], "temp_max": max(v["temp"] for v in allv), "pain": cur["pain"],
        "pain_change_8h": cur["pain"] - lag["pain"], "opioid_load": cur["opioid_load"],
        "opioid_8h": cur["opioid_load"] - (lag["opioid_load"] if lag.get("source") == "ward" else 0.0),
        "spirometry_frac": float(np.mean([v.get("spirometry_done", False) for v in ward])),
    })
    adm = d["admitted_min"]
    later = [l for l in snap["labs"]["series"][1:] if l["minute"] <= adm + hours * 60]
    if later:
        l = later[-1]
        f.update({"lab_available": 1.0, "lab_hb_change": l["hb"] - arrival_labs["hb"], "lab_plt_ratio": l["plt"] / arrival_labs["plt"],
                  "lab_wbc_change": l["wbc"] - arrival_labs["wbc"], "lab_crp_change": l["crp"] - arrival_labs["crp"],
                  "lab_ldh_ratio": l["ldh"] / arrival_labs["ldh"]})
    else:
        f.update({"lab_available": 0.0, "lab_hb_change": 0.0, "lab_plt_ratio": 1.0, "lab_wbc_change": 0.0,
                  "lab_crp_change": 0.0, "lab_ldh_ratio": 1.0})
    return f
