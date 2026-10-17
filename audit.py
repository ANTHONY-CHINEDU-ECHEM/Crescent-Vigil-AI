"""Analgesia equity audit.

Measures door to analgesia, reassessment and protocol adherence across groups,
estimates adjusted effects on the time to first analgesia, and checks that the
estimates recover the effects the generator injected (parameter recovery).
Recovery matters: an audit that cannot find a known delay in synthetic data
cannot be trusted to find one in real data.

Groups audited: individual plan visible or not, frequent attendance (five or
more attendances in the previous year), night arrival, sex, age 50 and over,
and site. Ethnicity is not audited because almost every patient in the
cohort shares the same ancestry; the inquiry evidence (S7) concerns how
people with sickle cell disease as a group are treated, which this audit
measures through the factors above.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from .. import config as C
from ..synth.generate import DTA_EFFECTS

COVARIATES = ["crowding", "triage_cat2", "triage_cat1", "plan_visible", "high_frequency_attender", "night", "female", "age_50_plus"]
PAIN_LIKE = ["pain", "chest", "abdominal", "priapism"]
CENSOR_MIN = 95.0


def design(df: pd.DataFrame) -> tuple[np.ndarray, list[str]]:
    X = pd.DataFrame({
        "crowding": df.crowding_index - 0.6, "triage_cat2": (df.triage_category == 2).astype(float),
        "triage_cat1": (df.triage_category == 1).astype(float), "plan_visible": df.plan_visible.astype(float),
        "high_frequency_attender": df.high_frequency_attender.astype(float), "night": df.night.astype(float),
        "female": (df.sex == "F").astype(float), "age_50_plus": (df.age >= 50).astype(float),
    })
    sites = sorted(df.site.unique())
    for s in sites[1:]:
        X[f"site_{s}"] = (df.site == s).astype(float)
    X.insert(0, "intercept", 1.0)
    return X.to_numpy(float), list(X.columns)


def ols_hc1(X, y):
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    r = y - X @ beta
    n, k = X.shape
    XtX_inv = np.linalg.inv(X.T @ X)
    meat = (X * r[:, None] ** 2).T @ X
    cov = XtX_inv @ meat @ XtX_inv * n / (n - k)
    return beta, np.sqrt(np.diag(cov))


def km_curve(minutes: np.ndarray, event: np.ndarray, grid=np.arange(0, 181, 5)) -> list[float]:
    """Kaplan Meier estimate of the proportion who have received analgesia by each minute."""
    order = np.argsort(minutes)
    t, e = minutes[order], event[order]
    n = len(t)
    surv, out, i = 1.0, [], 0
    at_risk = n
    for g in grid:
        while i < n and t[i] <= g:
            j = i
            d = 0
            while j < n and t[j] == t[i]:
                d += e[j]
                j += 1
            if at_risk > 0:
                surv *= 1 - d / at_risk
            at_risk -= j - i
            i = j
        out.append(round(1 - surv, 4))
    return out


def group_table(df: pd.DataFrame, col: str, labels: dict | None = None) -> list[dict]:
    rows = []
    for k, g in df.groupby(col):
        given = g.door_to_analgesia_min.dropna()
        rows.append({
            "group": labels.get(k, str(k)) if labels else str(k), "attendances": int(len(g)),
            "median_min": float(given.median()), "within_30": round(float((g.door_to_analgesia_min <= 30).mean()), 4),
            "within_60": round(float((g.door_to_analgesia_min <= 60).mean()), 4),
            "left_before_analgesia": round(float(g.left_before_analgesia.mean()), 4),
            "reassessed_within_30": round(float(g.reassessed_within_30[g.door_to_analgesia_min.notna()].mean()), 4),
        })
    return rows


def audit(df: pd.DataFrame, label: str) -> dict:
    d = df[df.complaint.isin(PAIN_LIKE)].copy()
    given = d[d.door_to_analgesia_min.notna()]
    X, names = design(given)
    y = np.log(given.door_to_analgesia_min.to_numpy())
    beta, se = ols_hc1(X, y)
    est = {n: {"estimate": round(float(b), 4), "se": round(float(s), 4),
               "ci95": [round(float(b - 1.96 * s), 4), round(float(b + 1.96 * s), 4)],
               "ratio": round(float(np.exp(b)), 3)} for n, b, s in zip(names, beta, se)}
    recovery = []
    for c in COVARIATES:
        true = DTA_EFFECTS[c]
        e = est[c]
        recovery.append({"effect": c, "true": true, "estimate": e["estimate"], "ci95": e["ci95"],
                         "covered": e["ci95"][0] <= true <= e["ci95"][1]})
    minutes = np.where(d.door_to_analgesia_min.notna(), d.door_to_analgesia_min, CENSOR_MIN)
    event = d.door_to_analgesia_min.notna().to_numpy()
    curves = {}
    for name, mask in {"plan visible": d.plan_visible, "no plan visible": ~d.plan_visible,
                       "frequent attender": d.high_frequency_attender, "not frequent": ~d.high_frequency_attender}.items():
        m = mask.to_numpy()
        curves[name] = km_curve(minutes[m], event[m])
    # Counterfactual: every existing plan visible at arrival.
    hidden = (d.has_plan & ~d.plan_visible & d.door_to_analgesia_min.notna()).to_numpy()
    cf = d.door_to_analgesia_min.to_numpy().copy()
    cf[hidden] = cf[hidden] * np.exp(est["plan_visible"]["estimate"])
    pethidine = d[d.first_agent == "pethidine"]
    with_plan = d[d.plan_visible & d.door_to_analgesia_min.notna()]
    return {
        "label": label, "attendances": int(len(d)), "given": int(len(given)),
        "overall": {"median_min": float(given.door_to_analgesia_min.median()),
                    "within_30": round(float((d.door_to_analgesia_min <= 30).mean()), 4),
                    "within_60": round(float((d.door_to_analgesia_min <= 60).mean()), 4),
                    "reassessed_within_30": round(float(given.reassessed_within_30.mean()), 4),
                    "plan_followed_when_visible": round(float(with_plan.plan_followed.mean()), 4),
                    "pethidine_given": int(len(pethidine)),
                    "pethidine_sites": pethidine.site.value_counts().to_dict()},
        "groups": {
            "plan": group_table(d, "plan_visible", {True: "plan visible", False: "no plan visible"}),
            "frequent_attender": group_table(d, "high_frequency_attender", {True: "five or more in past year", False: "fewer than five"}),
            "night": group_table(d, "night", {True: "22:00 to 07:00", False: "daytime"}),
            "sex": group_table(d, "sex", {"F": "female", "M": "male"}),
            "age": group_table(d.assign(age_band=np.where(d.age >= 50, "50 and over", "under 50")), "age_band"),
            "site": group_table(d, "site"),
        },
        "adjusted_log_minutes": est, "recovery": recovery,
        "counterfactual_all_plans_visible": {
            "attendances_with_hidden_plan": int(hidden.sum()),
            "within_30_now": round(float((d.door_to_analgesia_min <= 30).mean()), 4),
            "within_30_if_visible": round(float((pd.Series(cf) <= 30).mean()), 4),
        },
        "km_grid": list(range(0, 181, 5)), "km": curves,
    }


def run(write=True) -> dict:
    att = pd.read_parquet(C.SYNTH / "attendances.parquet")
    out = {"dev": audit(att[att.split == "dev"], "development sites A to F, 2021 to 2024"),
           "blind_site": audit(att[att.split == "blind_site"], "held out sites G and H"),
           "blind_temporal": audit(att[att.split == "blind_temporal"], "sites A to F in 2025")}
    if write:
        (C.REPORTS / "equity_audit.json").write_text(json.dumps(out, indent=2, default=float))
    return out


if __name__ == "__main__":
    r = run()
    for k, v in r.items():
        print(k, v["overall"])
        for rr in v["recovery"]:
            print("   ", rr)
