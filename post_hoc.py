"""Post hoc analysis of the stored blind predictions.

This reads reports/blind_predictions.parquet and does not score the blind set
again. It characterises which acute chest syndrome episodes the alert missed
and which admissions without acute chest syndrome it alerted on.
"""
from __future__ import annotations

import json

import pandas as pd

from .. import config as C


def run() -> dict:
    p = pd.read_parquet(C.REPORTS / "blind_predictions.parquet")
    thr = json.loads((C.MODELS / "acs_model.json").read_text())["threshold"]
    pp = pd.read_parquet(C.MODELS / "person_periods.parquet",
                         columns=["attendance_id", "hours", "opioid_load", "prior_acs_capped", "split"])
    pp = pp[pp.split != "dev"]
    d = p.merge(pp[["attendance_id", "hours", "opioid_load", "prior_acs_capped"]], on=["attendance_id", "hours"])
    d["alert"] = d.hgb >= thr
    e = d.groupby("attendance_id").agg(acs=("acs_72h", "max"), alerted=("alert", "max"), severe=("severe_genotype", "max"),
                                       hydroxyurea=("hydroxyurea", "max"), opioid=("opioid_load", "max"),
                                       prior=("prior_acs_capped", "max"), first_risk=("hgb", "first"), diag=("acs_diagnosis_h", "max"))
    pos, neg = e[e.acs == 1], e[e.acs == 0]
    missed, caught = pos[~pos.alerted], pos[pos.alerted]
    fa, quiet = neg[neg.alerted], neg[~neg.alerted]
    r = lambda x, n=3: round(float(x), n)
    out = {
        "threshold": thr,
        "missed": {"episodes": int(len(missed)), "severe_genotype": r(missed.severe.mean()), "on_hydroxyurea": r(missed.hydroxyurea.mean()),
                   "mean_previous_acs": r(missed.prior.mean(), 2), "median_risk_at_first_obs": r(missed.first_risk.median(), 4),
                   "median_diagnosis_h": r(missed.diag.median(), 1)},
        "caught": {"episodes": int(len(caught)), "severe_genotype": r(caught.severe.mean()), "on_hydroxyurea": r(caught.hydroxyurea.mean()),
                   "mean_previous_acs": r(caught.prior.mean(), 2), "median_risk_at_first_obs": r(caught.first_risk.median(), 4),
                   "median_diagnosis_h": r(caught.diag.median(), 1)},
        "false_alerts": {"admissions": int(len(fa)), "severe_genotype": r(fa.severe.mean()), "median_peak_opioid_load": r(fa.opioid.median(), 2),
                         "mean_previous_acs": r(fa.prior.mean(), 2)},
        "quiet_without_acs": {"admissions": int(len(quiet)), "severe_genotype": r(quiet.severe.mean()), "median_peak_opioid_load": r(quiet.opioid.median(), 2),
                              "mean_previous_acs": r(quiet.prior.mean(), 2)},
    }
    (C.REPORTS / "post_hoc_failures.json").write_text(json.dumps(out, indent=2))
    return out


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
