"""Figures for the README and docs, drawn from the stored reports and predictions."""
from __future__ import annotations

import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .. import config as C

INK, MUTED, GRID = "#171a2b", "#5a6078", "#e6e8f0"
C1, C2, C3 = "#4b52b5", "#c0532b", "#0f8a7a"
CRIT = "#b3261e"
plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 10, "axes.edgecolor": MUTED, "axes.labelcolor": INK, "xtick.color": MUTED,
    "ytick.color": MUTED, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8, "axes.spines.top": False,
    "axes.spines.right": False, "figure.dpi": 130, "savefig.bbox": "tight", "axes.titleweight": "bold", "axes.titlesize": 11,
})
F = C.FIGURES


def save(fig, name):
    fig.savefig(F / name, facecolor="white")
    plt.close(fig)


def cohort():
    att = pd.read_parquet(C.SYNTH / "attendances.parquet")
    obs = pd.read_parquet(C.SYNTH / "obs.parquet", columns=["attendance_id"])
    ev = pd.read_parquet(C.SYNTH / "events.parquet", columns=["attendance_id"])
    summary = {"patients": int(att.patient_id.nunique()), "attendances": int(len(att)), "admissions": int(att.admitted.sum()),
               "obs_rows": int(len(obs)), "events": int(len(ev)), "sites": int(att.site.nunique()),
               "acs_after_admission": int(att.acs_72h.sum()), "acs_at_arrival": int(att.acs_at_arrival.sum()),
               "plans": int(pd.read_parquet(C.SYNTH / "care_plans.parquet").shape[0]),
               "by_split": att.split.value_counts().to_dict(), "complaints": att.complaint.value_counts().to_dict()}
    (C.REPORTS / "cohort_summary.json").write_text(json.dumps(summary, indent=2))
    fig, ax = plt.subplots(1, 2, figsize=(11, 3.6), gridspec_kw={"width_ratios": [1.4, 1]})
    t = att.groupby(["site", "split"]).size().unstack(fill_value=0)
    cols = {"dev": C1, "blind_temporal": C3, "blind_site": C2}
    bottom = np.zeros(len(t))
    for k in ("dev", "blind_temporal", "blind_site"):
        if k in t:
            ax[0].bar(t.index, t[k], bottom=bottom, color=cols[k], label=k.replace("_", " "), width=0.7, edgecolor="white", linewidth=1.5)
            bottom += t[k].to_numpy()
    ax[0].set_title("Attendances by site and evaluation split"); ax[0].set_ylabel("attendances"); ax[0].legend(frameon=False)
    cm = att.complaint.value_counts()
    ax[1].barh(cm.index[::-1], cm.values[::-1], color=C1)
    ax[1].set_xscale("log"); ax[1].set_title("Presenting complaint (log scale)")
    save(fig, "cohort.png")


def equity():
    eq = json.loads((C.REPORTS / "equity_audit.json").read_text())
    d = eq["dev"]
    g = d["km_grid"]
    fig, ax = plt.subplots(1, 2, figsize=(11, 3.8), sharey=True)
    for a, pair, title in ((ax[0], ("plan visible", "no plan visible"), "Plan visibility"), (ax[1], ("not frequent", "frequent attender"), "Attendance frequency")):
        for name, col in zip(pair, (C1, C2)):
            a.step(g, d["km"][name], where="post", color=col, lw=2, label=name)
        a.axvline(30, color=CRIT, ls="--", lw=1); a.text(31, 0.05, "30 minute target", color=CRIT, fontsize=8)
        a.set_title(title); a.set_xlabel("minutes since arrival"); a.legend(frameon=False, loc="lower right")
    ax[0].set_ylabel("share given first analgesia")
    save(fig, "door_to_analgesia.png")
    fig, ax = plt.subplots(figsize=(8.5, 4.2))
    names = [r["effect"] for r in d["recovery"]]
    labels = {"crowding": "crowding (per unit)", "triage_cat2": "triage category 2", "triage_cat1": "triage category 1", "plan_visible": "plan visible",
              "high_frequency_attender": "frequent attender", "night": "night arrival", "female": "female", "age_50_plus": "age 50 and over"}
    for j, (k, col) in enumerate((("dev", C1), ("blind_site", C2), ("blind_temporal", C3))):
        rec = eq[k]["recovery"]
        y = np.arange(len(rec)) + (j - 1) * 0.22
        ax.errorbar([r["estimate"] for r in rec], y, xerr=[[r["estimate"] - r["ci95"][0] for r in rec], [r["ci95"][1] - r["estimate"] for r in rec]],
                    fmt="o", color=col, ms=4, lw=1.5, label=eq[k]["label"])
    ax.scatter([r["true"] for r in d["recovery"]], np.arange(len(names)), marker="|", s=400, color=INK, label="injected value", zorder=5)
    ax.set_yticks(range(len(names))); ax.set_yticklabels([labels[n] for n in names]); ax.axvline(0, color=MUTED, lw=1)
    ax.set_xlabel("effect on log minutes to first analgesia"); ax.set_title("Adjusted effects recover the injected values")
    ax.legend(frameon=False, fontsize=8, loc="upper left", bbox_to_anchor=(1.01, 1.0))
    save(fig, "effect_recovery.png")


def model():
    ev = json.loads((C.REPORTS / "evaluation_summary.json").read_text())
    cv = json.loads((C.REPORTS / "model_curves.json").read_text())
    b = ev["blind"]["model"]
    names = {"hgb": "gradient boosted", "logistic": "logistic regression", "rule": "saturation rule"}
    cols = {"hgb": C1, "logistic": C2, "rule": C3}
    fig, ax = plt.subplots(1, 3, figsize=(13, 3.9))
    for k in ("hgb", "logistic", "rule"):
        r = np.array(cv["roc"][k]); p = np.array(cv["pr"][k])
        key = {"hgb": "rolling_hgb", "logistic": "rolling_logistic", "rule": "rolling_rule"}[k]
        ax[0].plot(r[:, 0], r[:, 1], color=cols[k], lw=2, label=f"{names[k]} {b['all'][key]['auroc']:.3f}")
        ax[1].plot(p[:, 0], p[:, 1], color=cols[k], lw=2, label=f"{names[k]} {b['all'][key]['auprc']:.3f}")
    ax[0].plot([0, 1], [0, 1], ls="--", color=MUTED, lw=1); ax[0].set_title("ROC, blind set"); ax[0].set_xlabel("false positive rate"); ax[0].set_ylabel("true positive rate")
    ax[1].set_title("Precision and recall, blind set"); ax[1].set_xlabel("recall"); ax[1].set_ylabel("precision")
    for a in ax[:2]:
        a.legend(frameon=False, fontsize=8)
    cal = cv["calibration"]
    pr, ob = [c["predicted"] for c in cal], [c["observed"] for c in cal]
    m = max(pr + ob) * 1.05
    ax[2].plot([0, m], [0, m], ls="--", color=MUTED, lw=1); ax[2].plot(pr, ob, "o-", color=C1, lw=2, ms=5)
    ax[2].set_title("Calibration by decile, blind set"); ax[2].set_xlabel("predicted risk in 24 h"); ax[2].set_ylabel("observed rate")
    save(fig, "model_discrimination.png")
    fig, ax = plt.subplots(1, 2, figsize=(11, 3.8))
    t = cv["tradeoff"]
    ax[0].plot([x["threshold"] for x in t], [x["sensitivity"] for x in t], color=C1, lw=2, label="admissions with ACS alerted")
    ax[0].plot([x["threshold"] for x in t], [x["false_alert"] for x in t], color=C2, lw=2, label="admissions without ACS alerted")
    ax[0].axvline(cv["threshold"], color=CRIT, ls="--", lw=1); ax[0].text(cv["threshold"] + 0.01, 0.92, "threshold fixed on development data", color=CRIT, fontsize=8)
    ax[0].set_xlabel("alert threshold"); ax[0].set_ylabel("share of admissions"); ax[0].set_title("Alert trade off, blind set"); ax[0].legend(frameon=False, fontsize=8)
    lh = cv["lead_hist"]
    ax[1].bar([x["h"] + 2 for x in lh], [x["n"] for x in lh], width=3.4, color=C1)
    ax[1].set_xlabel("hours from first alert to diagnosis"); ax[1].set_ylabel("episodes"); ax[1].set_title("Warning time, blind set")
    save(fig, "alerts.png")
    tr = json.loads((C.MODELS / "training_report.json").read_text())
    imp = tr["importance"][:14][::-1]
    fig, ax = plt.subplots(figsize=(7.5, 4.4))
    ax.barh([i["feature"] for i in imp], [i["drop_in_auprc"] for i in imp], color=C1)
    ax.set_xlabel("fall in AUPRC when shuffled"); ax.set_title("Permutation importance, development hold out fold")
    save(fig, "importance.png")
    # Example risk trajectories from the blind predictions.
    pred = pd.read_parquet(C.REPORTS / "blind_predictions.parquet")
    rng = np.random.default_rng(3)
    pos = pred[(pred.acs_72h == 1) & (pred.acs_diagnosis_h > 30)].attendance_id.unique()
    neg = pred[(pred.acs_72h == 0)].groupby("attendance_id").hours.max()
    neg = neg[neg >= 68].index.to_numpy()
    fig, ax = plt.subplots(figsize=(9, 3.8))
    for aid, col in zip(list(rng.choice(pos, 3, replace=False)), (C1, C2, C3)):
        s = pred[pred.attendance_id == aid]
        ax.plot(s.hours, s.hgb, color=col, lw=2, label=f"{aid}, diagnosed at {s.acs_diagnosis_h.iat[0]:.0f} h")
        ax.axvline(s.acs_diagnosis_h.iat[0], color=col, ls=":", lw=1.2)
    for aid in rng.choice(neg, 12, replace=False):
        s = pred[pred.attendance_id == aid]
        ax.plot(s.hours, s.hgb, color=MUTED, lw=0.8, alpha=0.5)
    ax.axhline(cv["threshold"], color=CRIT, ls="--", lw=1)
    ax.set_xlabel("hours since admission"); ax.set_ylabel("risk of ACS in next 24 h")
    ax.set_title("Risk trajectories: three blind episodes with ACS against twelve without (grey)"); ax.legend(frameon=False, fontsize=8)
    save(fig, "risk_trajectories.png")


def copilot_figs():
    ev = json.loads((C.REPORTS / "evaluation_summary.json").read_text())
    b = ev["blind"]
    m = b["retrieval"]["methods"]
    order = ["bm25f", "lsa", "learned", "without_phase_match", "without_situation_overlap", "without_entity_hits", "without_title_overlap"]
    lab = {"bm25f": "BM25F", "lsa": "latent semantic", "learned": "learned ranker", "without_phase_match": "without phase",
           "without_situation_overlap": "without situation", "without_entity_hits": "without entities", "without_title_overlap": "without title"}
    fig, ax = plt.subplots(1, 2, figsize=(13, 4.0), gridspec_kw={"wspace": 0.55})
    x = np.arange(len(order))
    ax[0].bar(x - 0.2, [m[k]["hit@1"] for k in order], 0.38, color=C1, label="hit@1")
    ax[0].bar(x + 0.2, [m[k]["ndcg@10"] for k in order], 0.38, color=C3, label="nDCG@10")
    ax[0].set_xticks(x); ax[0].set_xticklabels([lab[k] for k in order], rotation=30, ha="right"); ax[0].set_ylim(0, 1.15)
    ax[0].set_title(f"Retrieval on {b['retrieval']['questions']} blind questions"); ax[0].legend(frameon=False, loc="upper left", ncol=2)
    det = b["perturbation"]["detection"]
    names = {"insert_dose": "dose inserted", "swap_to_forbidden_agent": "avoided agent", "change_number": "number changed",
             "drop_citations": "citations removed", "wrong_card": "wrong card"}
    ax[1].barh([names[k] for k in det], [v["rate"] for v in det.values()], color=C2)
    for i, v in enumerate(det.values()):
        ax[1].text(v["rate"] - 0.01, i, f"{100 * v['rate']:.1f}%", va="center", ha="right", color="white", fontsize=9)
    ax[1].set_xlim(0, 1); ax[1].grid(False); ax[1].set_title("Verifier catches corrupted sentences, blind")
    save(fig, "copilot_quality.png")


def all_figures():
    cohort(); equity()
    if (C.REPORTS / "model_curves.json").exists():
        model(); copilot_figs()


if __name__ == "__main__":
    all_figures()
    print(sorted(p.name for p in F.glob("*.png")))
