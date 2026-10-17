"""Temporal, situation aware retrieval over guidance, plan and history passages.

Scoring has three parts:

1. Lexical: BM25F over the title, entity list and body of each passage.
2. Semantic: cosine similarity in a latent semantic space (TF IDF followed by a
   truncated SVD) fitted on the guidance corpus, which tolerates paraphrase.
3. Context: whether the passage applies to the current phase of the attendance
   (arrival, early, ward, late, discharge), how well its situations overlap the
   situations implied by the question and the live record, and how many of its
   entities the question names.

A logistic ranker learns how to weigh these seven features from the
development questions only. Everything is plain arrays so the browser engine
can reproduce the same scores.
"""
from __future__ import annotations

import json
import math
from collections import Counter
from dataclasses import dataclass

import numpy as np

from .. import config as C
from ..knowledge.cards import PHASES, Passage
from .text import canonical, tokens

FIELD_WEIGHTS = {"title": 2.5, "entities": 2.0, "body": 1.0}
K1, B = 1.2, 0.75
LSA_DIMS = 40

FEATURES = ["bm25_norm", "bm25_recip_rank", "lsa_cosine", "phase_match", "situation_overlap", "entity_hits", "title_overlap"]

# Words in a question or record that imply a clinical situation.
SITUATION_TERMS = {
    "pain": ["pain", "crisis", "analgesia", "opioid", "morphine", "dose", "painkill"],
    "chest": ["chest", "breath", "cough", "oxygen", "saturation", "crackl", "air entry", "infiltrat", "x ray", "acute chest syndrome"],
    "fever": ["fever", "temperature", "38", "sepsis", "infection"],
    "infection": ["infection", "sepsis", "antibiotic", "fever"],
    "sepsis": ["sepsis", "lactate"],
    "neuro": ["weakness", "speech", "seizure", "stroke", "headache", "consciousness", "neurolog"],
    "stroke": ["stroke", "weakness", "speech"],
    "priapism": ["priapism"],
    "abdominal": ["abdominal", "spleen", "upper quadrant", "gallstone", "abdomen"],
    "anaemia": ["haemoglobin", "anaemia", "reticulocyte", "steady state"],
    "hypoventilation": ["sedation", "low respiratory rate", "respiratory rate", "naloxone", "toxicity"],
    "monitoring": ["monitor", "observation", "reassess", "vital", "recheck", "early warning"],
    "plan": ["care plan", "individual care", "plan"],
    "equity": ["trust", "exaggerat", "drug seek", "frequent", "crowd", "stigma", "attend"],
    "transfusion": ["transfus", "exchange", "blood transfusion"],
    "discharge": ["discharge", "home", "go home"],
    "safety": ["pethidine", "dose", "milligram", "safe"],
    "deterioration": ["deteriorat", "worsen", "alert", "escalat", "tiring", "risk"],
    "critical care": ["critical care"],
    "renal": ["renal"],
    "fluids": ["fluid"],
    "prevention": ["prevent", "spiromet", "hydroxyurea"],
    "treatment": ["treat", "management", "antibiotic"],
    "refractory": ["refractory", "not controlling", "not working", "ketamine"],
    "assessment": ["blood tests", "assess", "investigation"],
    "communication": ["involve", "listen", "prefer", "experience"],
    "scope": ["children", "paediatric", "pregnan"],
    "pregnancy": ["pregnan"],
    "crisis": ["self harm", "mental health", "suicid"],
    "admission": ["admission", "admitted", "admit"],
    "oxygen": ["oxygen", "hypoxia"],
    "history": ["previous", "last time", "before", "history"],
}


def phase_from_minute(minute: float | None, admitted_min: float | None = None) -> str | None:
    if minute is None:
        return None
    if admitted_min is not None and minute >= admitted_min:
        return "ward" if (minute - admitted_min) < 24 * 60 else "late"
    if minute <= 30:
        return "arrival"
    if minute <= 120:
        return "early"
    if minute <= 24 * 60:
        return "ward"
    if minute <= 72 * 60:
        return "late"
    return "discharge"


def situations_for(text: str, record_situations: list[str] | None = None) -> set[str]:
    t = canonical(text)
    found = {s for s, terms in SITUATION_TERMS.items() if any(term in t for term in terms)}
    if record_situations:
        found |= set(record_situations)
    return found


@dataclass
class Index:
    passages: list
    vocab: dict
    df: np.ndarray
    avg_len: dict
    tf: list          # per passage: {field: Counter}
    lens: list        # per passage: {field: int}
    lsa_idf: np.ndarray
    lsa_components: np.ndarray
    doc_vecs: np.ndarray
    entity_tokens: list
    title_tokens: list

    @classmethod
    def build(cls, passages: list[Passage]) -> "Index":
        tf, lens = [], []
        for p in passages:
            fields = {"title": tokens(p.title), "entities": tokens(" ".join(p.entities)), "body": tokens(p.body)}
            tf.append({f: Counter(v) for f, v in fields.items()})
            lens.append({f: len(v) for f, v in fields.items()})
        vocab = {}
        for d in tf:
            for c in d.values():
                for w in c:
                    vocab.setdefault(w, len(vocab))
        df = np.zeros(len(vocab))
        for d in tf:
            for w in set().union(*[set(c) for c in d.values()]):
                df[vocab[w]] += 1
        avg = {f: max(1e-9, float(np.mean([l[f] for l in lens]))) for f in FIELD_WEIGHTS}
        # Latent semantic space over all fields, title and entities weighted twice.
        N = len(passages)
        X = np.zeros((N, len(vocab)))
        for i, d in enumerate(tf):
            cnt = Counter()
            for f, c in d.items():
                for w, n in c.items():
                    cnt[w] += n * (2 if f != "body" else 1)
            for w, n in cnt.items():
                X[i, vocab[w]] = 1 + math.log(n)
        idf = np.log((1 + N) / (1 + df)) + 1
        X = X * idf
        X /= np.linalg.norm(X, axis=1, keepdims=True) + 1e-12
        k = min(LSA_DIMS, N - 1)
        U, S, Vt = np.linalg.svd(X, full_matrices=False)
        comps = Vt[:k]
        # Fix SVD sign so Python and TypeScript share one orientation.
        sign = np.sign(comps[np.arange(k), np.abs(comps).argmax(axis=1)])
        comps = comps * sign[:, None]
        docs = X @ comps.T
        docs /= np.linalg.norm(docs, axis=1, keepdims=True) + 1e-12
        # Store at six decimals so the browser engine computes with exactly the same numbers.
        idf, comps, docs = np.round(idf, 6), np.round(comps, 6), np.round(docs, 6)
        ents = [[set(tokens(e)) for e in p.entities] for p in passages]
        titles = [set(tokens(p.title)) for p in passages]
        return cls(passages, vocab, df, avg, tf, lens, idf, comps, docs, ents, titles)

    # ---- scoring -------------------------------------------------------
    def bm25(self, qtoks: list[str]) -> np.ndarray:
        N = len(self.passages)
        out = np.zeros(N)
        for w in sorted(set(qtoks)):
            j = self.vocab.get(w)
            if j is None:
                continue
            n = self.df[j]
            idf = math.log(1 + (N - n + 0.5) / (n + 0.5))
            for i in range(N):
                t = 0.0
                for f, wt in FIELD_WEIGHTS.items():
                    c = self.tf[i][f].get(w, 0)
                    if c:
                        t += wt * c / (1 - B + B * self.lens[i][f] / self.avg_len[f])
                if t:
                    out[i] += idf * t / (K1 + t)
        return out

    def lsa(self, qtoks: list[str]) -> np.ndarray:
        v = np.zeros(len(self.vocab))
        for w, n in Counter(qtoks).items():
            j = self.vocab.get(w)
            if j is not None:
                v[j] = 1 + math.log(n)
        v = v * self.lsa_idf
        nv = np.linalg.norm(v)
        if nv == 0:
            return np.zeros(len(self.passages))
        q = (v / nv) @ self.lsa_components.T
        nq = np.linalg.norm(q)
        return self.doc_vecs @ (q / nq) if nq else np.zeros(len(self.passages))

    def features(self, query: str, minute: float | None = None, admitted_min: float | None = None,
                 record_situations: list[str] | None = None) -> np.ndarray:
        qt = tokens(query)
        qset = set(qt)
        bm = self.bm25(qt)
        mx = bm.max()
        order = np.argsort(-bm, kind="stable")
        rank = np.empty(len(bm))
        rank[order] = np.arange(1, len(bm) + 1)
        recip = np.where(bm > 0, 1.0 / rank, 0.0)
        ls = self.lsa(qt)
        phase = phase_from_minute(minute, admitted_min)
        sits = situations_for(query, record_situations)
        F = np.zeros((len(self.passages), len(FEATURES)))
        for i, p in enumerate(self.passages):
            ph = 0.5 if phase is None else (1.0 if phase in p.phases else 0.0)
            sp = set(p.situations)
            so = len(sits & sp) / len(sp) if sp and sits else 0.0
            ents = self.entity_tokens[i]
            hits = sum(1 for e in ents if e and e <= qset)
            eh = min(1.0, hits / 2.0)
            tt = self.title_tokens[i]
            to = len(tt & qset) / len(tt) if tt else 0.0
            F[i] = [bm[i] / mx if mx > 0 else 0.0, recip[i], max(0.0, ls[i]), ph, so, eh, to]
        return F

    def export(self) -> dict:
        inv = sorted(self.vocab.items(), key=lambda x: x[1])
        return {
            "vocab": [w for w, _ in inv], "df": self.df.tolist(), "avg_len": self.avg_len,
            "tf": [{f: dict(c) for f, c in d.items()} for d in self.tf], "lens": self.lens,
            "lsa_idf": self.lsa_idf.tolist(), "lsa_components": self.lsa_components.tolist(),
            "doc_vecs": self.doc_vecs.tolist(),
            "entity_tokens": [[sorted(e) for e in ents] for ents in self.entity_tokens],
            "title_tokens": [sorted(t) for t in self.title_tokens],
            "passages": [p.to_dict() for p in self.passages],
            "params": {"k1": K1, "b": B, "field_weights": FIELD_WEIGHTS},
        }


class Ranker:
    """Logistic weights over the seven features, fitted on development questions."""

    def __init__(self, weights=None, bias=0.0, mean=None, std=None, mode="learned"):
        self.w = np.asarray(weights if weights is not None else [1, 0.3, 1, 0.2, 0.4, 0.4, 0.3], float)
        self.b = float(bias)
        self.mean = np.zeros(len(FEATURES)) if mean is None else np.asarray(mean, float)
        self.std = np.ones(len(FEATURES)) if std is None else np.asarray(std, float)
        self.mode = mode

    def score(self, F: np.ndarray, mask: list[int] | None = None) -> np.ndarray:
        Z = (F - self.mean) / self.std
        w = self.w.copy()
        if mask:
            w[mask] = 0.0
        return Z @ w + self.b

    def to_dict(self):
        return {"features": FEATURES, "weights": self.w.round(6).tolist(), "bias": round(self.b, 6),
                "mean": self.mean.round(6).tolist(), "std": self.std.round(6).tolist()}

    @classmethod
    def load(cls, path=C.INDEX / "ranker.json"):
        d = json.loads(path.read_text())
        return cls(d["weights"], d["bias"], d["mean"], d["std"])


def train_ranker(index: Index, questions: list[dict]) -> tuple[Ranker, dict]:
    from sklearn.linear_model import LogisticRegression

    ids = [p.pid for p in index.passages]
    X, y, g = [], [], []
    for qi, q in enumerate(questions):
        F = index.features(q["text"], q.get("minute"))
        for i, pid in enumerate(ids):
            X.append(F[i]); y.append(int(pid in q["gold"])); g.append(qi)
    X, y, g = np.array(X), np.array(y), np.array(g)
    mean, std = X.mean(0), X.std(0) + 1e-9
    Z = (X - mean) / std
    # Question grouped cross validation for an honest development estimate.
    folds = 5
    fold_of = np.array([qi % folds for qi in g])
    cv_scores = np.zeros(len(y))
    for k in range(folds):
        tr, te = fold_of != k, fold_of == k
        m = LogisticRegression(C=1.0, class_weight="balanced", max_iter=2000).fit(Z[tr], y[tr])
        cv_scores[te] = m.decision_function(Z[te])
    m = LogisticRegression(C=1.0, class_weight="balanced", max_iter=2000).fit(Z, y)
    rk = Ranker(m.coef_[0], m.intercept_[0], mean, std)
    return rk, {"cv_scores": cv_scores, "groups": g, "labels": y}


def build(write=True):
    from ..knowledge.cards import write_cards_json

    cards = write_cards_json()
    index = Index.build(cards)
    qs = [json.loads(l) for l in open(C.EVAL / "questions_dev.jsonl")]
    ranker, cv = train_ranker(index, qs)
    if write:
        (C.INDEX / "index.json").write_text(json.dumps(index.export()))
        (C.INDEX / "ranker.json").write_text(json.dumps(ranker.to_dict(), indent=2))
    return index, ranker, cv


def load_index() -> Index:
    from ..knowledge.cards import parse_cards
    return Index.build(parse_cards())


if __name__ == "__main__":
    idx, rk, _ = build()
    print(json.dumps(rk.to_dict(), indent=2))
