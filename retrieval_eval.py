"""Retrieval metrics on held out clinician questions.

Methods compared: BM25F alone, latent semantic similarity alone, the learned
ranker, and the learned ranker with each context feature removed.
"""
from __future__ import annotations

import json
import math

import numpy as np

from .. import config as C
from ..retrieval.index import FEATURES, Index, Ranker


def metrics_for(scores: np.ndarray, ids: list[str], gold: list[str]) -> dict:
    order = np.argsort(-scores, kind="stable")
    ranked = [ids[i] for i in order]
    g = set(gold)
    first = next((r for r, pid in enumerate(ranked, 1) if pid in g), None)
    dcg = sum(1 / math.log2(r + 1) for r, pid in enumerate(ranked[:10], 1) if pid in g)
    idcg = sum(1 / math.log2(r + 1) for r in range(1, min(len(g), 10) + 1))
    return {
        "hit@1": float(ranked[0] in g),
        "recall@3": len(g & set(ranked[:3])) / len(g),
        "recall@5": len(g & set(ranked[:5])) / len(g),
        "any@3": float(bool(g & set(ranked[:3]))),
        "mrr": 1 / first if first else 0.0,
        "ndcg@10": dcg / idcg if idcg else 0.0,
    }


def evaluate(index: Index, ranker: Ranker, questions: list[dict]) -> dict:
    ids = [p.pid for p in index.passages]
    methods = {"bm25f": None, "lsa": None, "learned": [], **{f"without_{f}": [i] for i, f in enumerate(FEATURES) if i >= 3}}
    out = {m: [] for m in methods}
    per_q = []
    for q in questions:
        F = index.features(q["text"], q.get("minute"))
        for m, mask in methods.items():
            if m == "bm25f":
                s = F[:, 0] + 1e-6 * F[:, 2]
            elif m == "lsa":
                s = F[:, 2]
            else:
                s = ranker.score(F, mask)
            r = metrics_for(s, ids, q["gold"])
            out[m].append(r)
            if m == "learned":
                order = np.argsort(-s, kind="stable")[:5]
                per_q.append({"qid": q["qid"], "text": q["text"], "gold": q["gold"], "top5": [ids[i] for i in order], **r})
    summary = {m: {k: round(float(np.mean([r[k] for r in rs])), 4) for k in rs[0]} for m, rs in out.items()}
    return {"n": len(questions), "methods": summary, "per_question": per_q}


def dev_cross_validated(index: Index, questions: list[dict], cv: dict) -> dict:
    ids = [p.pid for p in index.passages]
    n = len(ids)
    rows = []
    for qi, q in enumerate(questions):
        s = cv["cv_scores"][qi * n:(qi + 1) * n]
        rows.append(metrics_for(s, ids, q["gold"]))
    return {k: round(float(np.mean([r[k] for r in rows])), 4) for k in rows[0]}


if __name__ == "__main__":
    from ..retrieval.index import build
    idx, rk, cv = build()
    qs = [json.loads(l) for l in open(C.EVAL / "questions_dev.jsonl")]
    print("dev cross validated learned:", dev_cross_validated(idx, qs, cv))
    res = evaluate(idx, rk, qs)
    print(json.dumps(res["methods"], indent=1))
