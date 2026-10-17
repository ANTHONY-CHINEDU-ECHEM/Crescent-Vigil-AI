"""Acute chest syndrome deterioration models.

Two models share the same learner, a histogram gradient boosted tree ensemble:

* rolling: at every four hourly observation set after admission, the chance
  that acute chest syndrome is diagnosed within the next 24 hours (a discrete
  time hazard model over person periods);
* admission: at the first ward observation, the chance of acute chest syndrome
  within 72 hours.

Baselines: logistic regression on the same features, and a saturation rule
(saturation below 94 percent or at least three points below the patient's own
baseline). Only development attendances are used. Hyperparameters are chosen
by patient grouped cross validation; probabilities are calibrated with an
isotonic map fitted to out of fold predictions; the alert threshold is fixed
on development data before the blind set is opened.
"""
from __future__ import annotations

import json
import time

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from .. import config as C
from .features import ADMISSION_FEATURES, FEATURES, person_period_table

GRID = [
    {"learning_rate": 0.06, "max_leaf_nodes": 15, "l2_regularization": 1.0, "max_iter": 300},
    {"learning_rate": 0.06, "max_leaf_nodes": 31, "l2_regularization": 1.0, "max_iter": 300},
    {"learning_rate": 0.03, "max_leaf_nodes": 31, "l2_regularization": 3.0, "max_iter": 600},
]
SEED = C.MASTER_SEED


def hgb(params):
    return HistGradientBoostingClassifier(random_state=SEED, early_stopping=False, min_samples_leaf=80, **params)


def rule_score(df: pd.DataFrame) -> np.ndarray:
    """Saturation rule as a score: positive when saturation is low or below baseline."""
    return np.maximum(C.PROTOCOL.spo2_flag - df.spo2, df.spo2_gap - C.PROTOCOL.spo2_drop_flag + 0.5).to_numpy()


def build_tables():
    att = pd.read_parquet(C.SYNTH / "attendances.parquet")
    obs = pd.read_parquet(C.SYNTH / "obs.parquet")
    labs = pd.read_parquet(C.SYNTH / "labs.parquet")
    pp = person_period_table(att, obs, labs)
    pp.to_parquet(C.MODELS / "person_periods.parquet", index=False)
    return pp


def cv_predict(model_fn, X, y, groups, folds=5):
    oof = np.zeros(len(y))
    for tr, te in GroupKFold(n_splits=folds).split(X, y, groups):
        m = model_fn().fit(X[tr], y[tr])
        oof[te] = m.predict_proba(X[te])[:, 1]
    return oof


def summarise(y, p) -> dict:
    return {"n": int(len(y)), "positives": int(y.sum()), "auroc": round(float(roc_auc_score(y, p)), 4),
            "auprc": round(float(average_precision_score(y, p)), 4),
            "brier": round(float(brier_score_loss(y, np.clip(p, 0, 1))), 5) if p.max() <= 1 and p.min() >= 0 else None}


def episode_alerts(df: pd.DataFrame, score: np.ndarray, threshold: float) -> dict:
    """Alert policy: the first observation set whose score reaches the threshold raises an alert."""
    d = df[["attendance_id", "hours", "acs_72h", "acs_diagnosis_h"]].copy()
    d["alert"] = score >= threshold
    first = d[d.alert].groupby("attendance_id").hours.min()
    ep = d.groupby("attendance_id").agg(acs=("acs_72h", "max"), diag=("acs_diagnosis_h", "max"), last=("hours", "max"))
    ep["first_alert"] = first
    pos = ep[ep.acs == 1]
    neg = ep[ep.acs == 0]
    caught = pos.first_alert.notna()
    lead = (pos.diag - pos.first_alert)[caught]
    alerts = d.alert.sum()
    patient_days = (ep["last"] + C.OBS_STEP_H).sum() / 24
    return {
        "threshold": round(float(threshold), 4),
        "episodes_with_acs": int(len(pos)), "episode_sensitivity": round(float(caught.mean()), 4),
        "median_lead_time_h": round(float(lead.median()), 1) if len(lead) else None,
        "lead_time_iqr_h": [round(float(lead.quantile(0.25)), 1), round(float(lead.quantile(0.75)), 1)] if len(lead) else None,
        "admissions_without_acs": int(len(neg)), "false_alert_admissions": round(float(neg.first_alert.notna().mean()), 4),
        "alerting_admissions_ppv": round(float(caught.sum() / max(1, ep.first_alert.notna().sum())), 4),
        "alerts_per_100_patient_days": round(float(100 * alerts / patient_days), 2),
    }


def threshold_for_sensitivity(df, score, target=0.80) -> float:
    lo, hi = float(np.min(score)), float(np.max(score))
    for _ in range(40):
        mid = (lo + hi) / 2
        if episode_alerts(df, score, mid)["episode_sensitivity"] >= target:
            lo = mid
        else:
            hi = mid
    return lo


def export_trees(model: HistGradientBoostingClassifier) -> dict:
    trees = []
    for it in model._predictors:
        nodes = it[0].nodes
        trees.append({
            "f": nodes["feature_idx"].astype(int).tolist(), "t": nodes["num_threshold"].astype(float).tolist(),
            "l": nodes["left"].astype(int).tolist(), "r": nodes["right"].astype(int).tolist(),
            "leaf": nodes["is_leaf"].astype(int).tolist(), "v": nodes["value"].astype(float).tolist(),
            "m": nodes["missing_go_to_left"].astype(int).tolist(),
        })
    return {"baseline": float(model._baseline_prediction.ravel()[0]), "trees": trees}


def raw_tree_predict(exp: dict, X: np.ndarray) -> np.ndarray:
    """Reference implementation of the exported ensemble (mirrored in TypeScript)."""
    out = np.full(len(X), exp["baseline"])
    for t in exp["trees"]:
        for i, x in enumerate(X):
            n = 0
            while not t["leaf"][n]:
                v = x[t["f"][n]]
                if np.isnan(v):
                    n = t["l"][n] if t["m"][n] else t["r"][n]
                else:
                    n = t["l"][n] if v <= t["t"][n] else t["r"][n]
            out[i] += t["v"][n]
    return 1 / (1 + np.exp(-out))


def calibrator(y, p) -> dict:
    iso = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0).fit(p, y)
    return {"x": iso.X_thresholds_.astype(float).tolist(), "y": iso.y_thresholds_.astype(float).tolist()}


def apply_calibrator(cal: dict, p: np.ndarray) -> np.ndarray:
    return np.interp(p, cal["x"], cal["y"])


def explain(model, cal, x: np.ndarray, medians: np.ndarray, names: list[str], top: list[int], k=4) -> list[dict]:
    """Occlusion explanation: how much the calibrated risk falls when one feature is set to the development median."""
    base = apply_calibrator(cal, model.predict_proba(x[None])[:, 1])[0]
    X = np.repeat(x[None], len(top), axis=0)
    for r, j in enumerate(top):
        X[r, j] = medians[j]
    alt = apply_calibrator(cal, model.predict_proba(X)[:, 1])
    d = [{"feature": names[j], "value": float(x[j]), "typical": float(medians[j]), "effect": float(base - a)}
         for j, a in zip(top, alt)]
    return sorted(d, key=lambda z: -abs(z["effect"]))[:k]


def train(write=True) -> dict:
    t0 = time.time()
    pp = build_tables()
    dev = pp[pp.split == "dev"].reset_index(drop=True)
    X = dev[FEATURES].to_numpy(float)
    y = dev.label_24h.to_numpy()
    groups = dev.patient_id.to_numpy()
    report = {"rows_dev": int(len(dev)), "admissions_dev": int(dev.attendance_id.nunique()),
              "acs_admissions_dev": int(dev.groupby("attendance_id").acs_72h.max().sum()), "grid": []}

    best, best_ap, best_oof = None, -1, None
    for params in GRID:
        oof = cv_predict(lambda: hgb(params), X, y, groups)
        ap = average_precision_score(y, oof)
        report["grid"].append({**params, "cv_auprc": round(float(ap), 4), "cv_auroc": round(float(roc_auc_score(y, oof)), 4)})
        if ap > best_ap:
            best, best_ap, best_oof = params, ap, oof
    report["chosen"] = best
    lr_oof = cv_predict(lambda: make_pipeline(StandardScaler(), LogisticRegression(max_iter=3000, C=0.5)), X, y, groups)
    cal = calibrator(y, best_oof)
    oof_cal = apply_calibrator(cal, best_oof)
    report["dev_cv"] = {"rolling_hgb": summarise(y, oof_cal), "rolling_logistic": summarise(y, lr_oof),
                        "rolling_rule": {k: v for k, v in summarise(y, rule_score(dev)).items() if k != "brier"}}
    thr = threshold_for_sensitivity(dev, oof_cal, 0.80)
    rule_thr = 0.0
    report["dev_alerts"] = {"hgb": episode_alerts(dev, oof_cal, thr),
                            "logistic_at_same_sensitivity": episode_alerts(dev, lr_oof, threshold_for_sensitivity(dev, lr_oof, 0.80)),
                            "rule": episode_alerts(dev, rule_score(dev), rule_thr)}
    # Admission model at the first ward observation.
    first = dev[dev.hours == 0].reset_index(drop=True)
    Xa, ya, ga = first[ADMISSION_FEATURES].to_numpy(float), first.acs_72h.to_numpy(), first.patient_id.to_numpy()
    adm_params = {"learning_rate": 0.05, "max_leaf_nodes": 15, "l2_regularization": 1.0, "max_iter": 250}
    a_oof = cv_predict(lambda: hgb(adm_params), Xa, ya, ga)
    a_lr = cv_predict(lambda: make_pipeline(StandardScaler(), LogisticRegression(max_iter=3000, C=0.5)), Xa, ya, ga)
    a_cal = calibrator(ya, a_oof)
    report["dev_cv"]["admission_hgb"] = summarise(ya, apply_calibrator(a_cal, a_oof))
    report["dev_cv"]["admission_logistic"] = summarise(ya, a_lr)

    # Final fits on all development rows.
    model = hgb(best).fit(X, y)
    adm_model = hgb(adm_params).fit(Xa, ya)
    lr = make_pipeline(StandardScaler(), LogisticRegression(max_iter=3000, C=0.5)).fit(X, y)
    medians = np.nanmedian(X, axis=0)
    # Global importance: permutation on a patient grouped hold out fold.
    from sklearn.inspection import permutation_importance
    tr, te = next(GroupKFold(n_splits=5).split(X, y, groups))
    m_tr = hgb(best).fit(X[tr], y[tr])
    sub = np.random.default_rng(SEED).choice(te, size=min(40000, len(te)), replace=False)
    pi = permutation_importance(m_tr, X[sub], y[sub], scoring="average_precision", n_repeats=3, random_state=SEED)
    imp = sorted(zip(FEATURES, pi.importances_mean), key=lambda z: -z[1])
    report["importance"] = [{"feature": f, "drop_in_auprc": round(float(v), 4)} for f, v in imp]
    top = [FEATURES.index(f) for f, _ in imp[:12]]
    report["alert_threshold"] = round(float(thr), 4)
    report["seconds"] = round(time.time() - t0, 1)

    if write:
        import joblib
        joblib.dump({"rolling": model, "admission": adm_model, "logistic": lr, "cal": cal, "adm_cal": a_cal,
                     "medians": medians, "top": top, "threshold": thr}, C.MODELS / "acs_models.joblib")
        exp = {"features": FEATURES, "admission_features": ADMISSION_FEATURES,
               "rolling": export_trees(model), "admission": export_trees(adm_model),
               "calibration": cal, "admission_calibration": a_cal, "medians": medians.astype(float).tolist(),
               "explain_features": top, "threshold": float(thr)}
        (C.MODELS / "acs_model.json").write_text(json.dumps(exp))
        pd.DataFrame({"attendance_id": dev.attendance_id, "hours": dev.hours, "label_24h": y,
                      "oof_hgb": oof_cal, "oof_logistic": lr_oof, "rule": rule_score(dev)}).to_parquet(C.MODELS / "dev_oof.parquet", index=False)
        (C.MODELS / "training_report.json").write_text(json.dumps(report, indent=2))
    return report


class ACSModel:
    """Runtime wrapper used by the copilot and API."""

    def __init__(self, path=C.MODELS / "acs_models.joblib"):
        import joblib
        b = joblib.load(path)
        self.__dict__.update(b)

    def predict(self, feats: dict) -> dict:
        x = np.array([feats[f] for f in FEATURES], float)
        p = float(apply_calibrator(self.cal, self.rolling.predict_proba(x[None])[:, 1])[0])
        return {"risk_24h": p, "alert": p >= self.threshold, "threshold": float(self.threshold),
                "drivers": explain(self.rolling, self.cal, x, self.medians, FEATURES, self.top)}


if __name__ == "__main__":
    print(json.dumps(train(), indent=2))


def write_export() -> None:
    """Rewrite acs_model.json from the saved models at full precision (used by the browser engine)."""
    import joblib
    b = joblib.load(C.MODELS / "acs_models.joblib")
    exp = {"features": FEATURES, "admission_features": ADMISSION_FEATURES,
           "rolling": export_trees(b["rolling"]), "admission": export_trees(b["admission"]),
           "calibration": b["cal"], "admission_calibration": b["adm_cal"], "medians": [float(x) for x in b["medians"]],
           "explain_features": [int(x) for x in b["top"]], "threshold": float(b["threshold"])}
    (C.MODELS / "acs_model.json").write_text(json.dumps(exp))
