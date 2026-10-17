"""Evaluation on the development set, and the single scoring of the blind set.

    python -m crescent_vigil.eval.evaluate            development only
    python -m crescent_vigil.eval.evaluate --blind    score the frozen blind set (appends to blind_runs.json)

The blind run refuses to start if any frozen file has changed since freezing.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, precision_recall_curve, roc_auc_score, roc_curve

from .. import config as C
from ..models.acs import ACSModel, apply_calibrator, episode_alerts, rule_score, summarise
from ..models.features import ADMISSION_FEATURES, FEATURES
from ..retrieval.index import FEATURES as RFEATURES, Index, Ranker
from ..knowledge.cards import parse_cards
from . import copilot_eval as CE
from .retrieval_eval import dev_cross_validated, evaluate as retrieval_evaluate
from .splits import verify

SUMMARY = C.REPORTS / "evaluation_summary.json"


def load_questions(split):
    return [json.loads(l) for l in open(C.EVAL / f"questions_{split}.jsonl")]


def copilot_section(cp, scenarios, with_ablations=True) -> dict:
    out = {"all": CE.score_scenarios(cp, scenarios)}
    for sl in ("blind_site", "blind_temporal"):
        sub = [s for s in scenarios if s["split"] == sl]
        if sub:
            out[sl] = CE.score_scenarios(cp, sub)
    if with_ablations:
        abl = {}
        for name, ab in {"without_phase_feature": {"mask": [3]}, "without_situation_feature": {"mask": [4]},
                         "without_entity_feature": {"mask": [5]}, "without_record_situations": {"no_record_situations": True},
                         "bm25f_only": {"mask": [1, 2, 3, 4, 5, 6]}}.items():
            r = CE.score_scenarios(cp, scenarios, ablate=ab)
            abl[name] = {"citation_correct": r["citation_correct"], "verified_rate": r["verified_rate"], "action_f1": r["actions"]["f1"]}
        out["ablations"] = abl
    return out


def model_predictions(pp: pd.DataFrame, m: ACSModel) -> pd.DataFrame:
    X = pp[FEATURES].to_numpy(float)
    out = pp[["attendance_id", "patient_id", "site", "split", "hours", "acs_72h", "acs_diagnosis_h", "label_24h"]].copy()
    out["hgb"] = apply_calibrator(m.cal, m.rolling.predict_proba(X)[:, 1])
    out["logistic"] = m.logistic.predict_proba(X)[:, 1]
    out["rule"] = rule_score(pp)
    for c in ("spo2_gap", "temp_max", "spo2_min", "severe_genotype", "female", "hydroxyurea", "high_frequency_attender"):
        out[c] = pp[c].to_numpy()
    return out


def calibration_bins(y, p, n=10):
    q = np.quantile(p, np.linspace(0, 1, n + 1))
    q[-1] += 1e-9
    rows = []
    for a, b in zip(q[:-1], q[1:]):
        m = (p >= a) & (p < b)
        if m.sum():
            rows.append({"predicted": round(float(p[m].mean()), 4), "observed": round(float(y[m].mean()), 4), "n": int(m.sum())})
    return rows


def thin(x, y, k=160):
    idx = np.unique(np.linspace(0, len(x) - 1, min(k, len(x))).astype(int))
    return [[round(float(x[i]), 4), round(float(y[i]), 4)] for i in idx]


def model_section(pred: pd.DataFrame, m: ACSModel, pp: pd.DataFrame) -> tuple[dict, dict]:
    res, curves = {}, {}
    y = pred.label_24h.to_numpy()
    for name, sub in {"all": pred, "blind_site": pred[pred.split == "blind_site"], "blind_temporal": pred[pred.split == "blind_temporal"]}.items():
        ys = sub.label_24h.to_numpy()
        res[name] = {"rolling_hgb": summarise(ys, sub.hgb.to_numpy()), "rolling_logistic": summarise(ys, sub.logistic.to_numpy()),
                     "rolling_rule": {k: v for k, v in summarise(ys, sub.rule.to_numpy()).items() if k != "brier"}}
    thr = float(m.threshold)
    res["alerts"] = {"hgb_at_frozen_threshold": episode_alerts(pred, pred.hgb.to_numpy(), thr),
                     "rule": episode_alerts(pred, pred.rule.to_numpy(), 0.0)}
    dev_oof = pd.read_parquet(C.MODELS / "dev_oof.parquet")
    from ..models.acs import threshold_for_sensitivity
    pp_dev = pd.read_parquet(C.MODELS / "person_periods.parquet", columns=["attendance_id", "hours", "acs_72h", "acs_diagnosis_h", "split"])
    pp_dev = pp_dev[pp_dev.split == "dev"].reset_index(drop=True)
    lr_thr = threshold_for_sensitivity(pp_dev, dev_oof.oof_logistic.to_numpy(), 0.80)
    res["alerts"]["logistic_at_dev_threshold"] = episode_alerts(pred, pred.logistic.to_numpy(), lr_thr)
    # Admission model.
    first = pp[pp.hours == 0]
    pa = apply_calibrator(m.adm_cal, m.admission.predict_proba(first[ADMISSION_FEATURES].to_numpy(float))[:, 1])
    res["admission_hgb"] = summarise(first.acs_72h.to_numpy(), pa)
    # Subgroups.
    subs = []
    for col, lab in (("severe_genotype", {1: "HbSS, HbS beta zero or HbSD", 0: "HbSC or HbS beta plus"}), ("female", {1: "female", 0: "male"}),
                     ("hydroxyurea", {1: "on hydroxyurea", 0: "not on hydroxyurea"}), ("high_frequency_attender", {1: "frequent attender", 0: "not frequent"})):
        for v, name in lab.items():
            s = pred[pred[col] == v]
            if s.label_24h.sum() > 10:
                subs.append({"group": name, "rows": int(len(s)), "auroc": round(float(roc_auc_score(s.label_24h, s.hgb)), 4),
                             "auprc": round(float(average_precision_score(s.label_24h, s.hgb)), 4),
                             "alert_sensitivity": episode_alerts(s, s.hgb.to_numpy(), thr)["episode_sensitivity"]})
    for site in sorted(pred.site.unique()):
        s = pred[pred.site == site]
        subs.append({"group": f"site {site}", "rows": int(len(s)), "auroc": round(float(roc_auc_score(s.label_24h, s.hgb)), 4),
                     "auprc": round(float(average_precision_score(s.label_24h, s.hgb)), 4),
                     "alert_sensitivity": episode_alerts(s, s.hgb.to_numpy(), thr)["episode_sensitivity"]})
    res["subgroups"] = subs
    # Failure analysis.
    d = pred.copy()
    d["alert"] = d.hgb >= thr
    ep = d.groupby("attendance_id").agg(acs=("acs_72h", "max"), diag=("acs_diagnosis_h", "max"), alerted=("alert", "max"),
                                        temp_max=("temp_max", "max"), gap_max=("spo2_gap", "max"))
    pos, neg = ep[ep.acs == 1], ep[ep.acs == 0]
    missed, caught = pos[~pos.alerted], pos[pos.alerted]
    fa, quiet = neg[neg.alerted], neg[~neg.alerted]
    res["failures"] = {
        "missed_episodes": int(len(missed)), "missed_median_diagnosis_h": round(float(missed.diag.median()), 1),
        "caught_median_diagnosis_h": round(float(caught.diag.median()), 1),
        "missed_diagnosed_within_12h": round(float((missed.diag <= 12).mean()), 4),
        "caught_diagnosed_within_12h": round(float((caught.diag <= 12).mean()), 4),
        "false_alert_admissions": int(len(fa)),
        "false_alerts_with_fever": round(float((fa.temp_max >= 38).mean()), 4), "quiet_with_fever": round(float((quiet.temp_max >= 38).mean()), 4),
        "false_alerts_with_desaturation": round(float((fa.gap_max >= 3).mean()), 4), "quiet_with_desaturation": round(float((quiet.gap_max >= 3).mean()), 4),
    }
    res["calibration"] = calibration_bins(y, pred.hgb.to_numpy())
    for name in ("hgb", "logistic", "rule"):
        fpr, tpr, _ = roc_curve(y, pred[name])
        pr, rc, _ = precision_recall_curve(y, pred[name])
        curves.setdefault("roc", {})[name] = thin(fpr, tpr)
        curves.setdefault("pr", {})[name] = thin(rc[::-1], pr[::-1])
    curves["calibration"] = res["calibration"]
    trade = []
    for t in np.round(np.linspace(0.04, 0.6, 29), 3):
        e = episode_alerts(pred, pred.hgb.to_numpy(), float(t))
        trade.append({"threshold": float(t), "sensitivity": e["episode_sensitivity"], "false_alert": e["false_alert_admissions"],
                      "lead": e["median_lead_time_h"], "per100": e["alerts_per_100_patient_days"]})
    curves["tradeoff"] = trade
    first_alert = d[d.alert].groupby("attendance_id").hours.min()
    lead = (pos.diag - first_alert.reindex(pos.index)).dropna()
    hist = np.histogram(lead, bins=np.arange(0, 76, 4))
    curves["lead_hist"] = [{"h": int(h), "n": int(n)} for h, n in zip(hist[1][:-1], hist[0])]
    curves["threshold"] = thr
    return res, curves


def dev_section(cp, index, ranker) -> dict:
    qs = load_questions("dev")
    from ..retrieval.index import train_ranker
    _, cv = train_ranker(index, qs)
    dev_sc = CE.load("dev")
    return {
        "retrieval": {"cross_validated_learned": dev_cross_validated(index, qs, cv), "fitted": retrieval_evaluate(index, ranker, qs)["methods"]},
        "copilot": copilot_section(cp, dev_sc),
        "probes": {k: v for k, v in CE.run_probes(cp, dev_sc).items() if k != "results"},
        "perturbation": CE.perturbation_test(cp, dev_sc, n=200),
        "model": json.loads((C.MODELS / "training_report.json").read_text()),
    }


def blind_section(cp, index, ranker) -> tuple[dict, dict]:
    if not verify():
        raise SystemExit("Frozen evaluation files have changed; the blind set cannot be scored.")
    qs = load_questions("blind")
    ret = retrieval_evaluate(index, ranker, qs)
    misses = [q for q in ret["per_question"] if q["hit@1"] == 0]
    sc = CE.load("blind")
    probes = CE.run_probes(cp, sc, seed=1)
    pp = pd.read_parquet(C.MODELS / "person_periods.parquet")
    pp = pp[pp.split != "dev"].reset_index(drop=True)
    pred = model_predictions(pp, cp.model)
    pred.to_parquet(C.REPORTS / "blind_predictions.parquet", index=False)
    model, curves = model_section(pred, cp.model, pp)
    eq = json.loads((C.REPORTS / "equity_audit.json").read_text())
    out = {
        "retrieval": {"questions": ret["n"], "methods": ret["methods"], "misses": misses},
        "copilot": copilot_section(cp, sc),
        "probes": probes,
        "perturbation": CE.perturbation_test(cp, sc, n=300, seed=1),
        "model": model,
        "equity_recovery": {k: {"covered": sum(r["covered"] for r in v["recovery"]), "effects": len(v["recovery"])} for k, v in eq.items()},
    }
    return out, curves


def main(blind: bool) -> dict:
    from ..agent.copilot import Copilot
    index = Index.build(parse_cards())
    ranker = Ranker.load()
    cp = Copilot(index=index, ranker=ranker, log=False)
    summary = json.loads(SUMMARY.read_text()) if SUMMARY.exists() else {}
    summary["frozen"] = json.loads((C.EVAL / "FROZEN.json").read_text())
    summary["dev"] = dev_section(cp, index, ranker)
    if blind:
        ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
        res, curves = blind_section(cp, index, ranker)
        res["scored_at"] = ts
        summary["blind"] = res
        (C.REPORTS / "model_curves.json").write_text(json.dumps(curves))
        runs = json.loads((C.EVAL / "blind_runs.json").read_text())
        runs["runs"].append({"scored_at": ts, "combined_sha256": summary["frozen"]["combined_sha256"]})
        (C.EVAL / "blind_runs.json").write_text(json.dumps(runs, indent=2))
    SUMMARY.write_text(json.dumps(summary, indent=2, default=float))
    return summary


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--blind", action="store_true")
    a = ap.parse_args()
    s = main(a.blind)
    print(json.dumps({k: v for k, v in s.items() if k != "frozen"}, indent=1, default=float)[:6000])
