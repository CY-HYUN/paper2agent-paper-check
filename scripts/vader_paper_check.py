"""Check VADER compound scores, from any source (the Paper2Agent tool, or a direct run), against the paper's Table 4 r.

    python scripts/vader_paper_check.py <scores.json> <hutto_ICWSM_2014 dir> [configs/paper_vader.json]
    python scripts/vader_paper_check.py --selftest

scores.json: {"source": "...", "scores": {"tweets": [compound per line of tweets_GroundTruth.txt, in order], ...}}.
Verdict per corpus: match (|r - paper| <= tolerance), mismatch, or missing. A mismatch where the 2014 code also misses
the paper is marked 'paper_row_suspect': that gap is not drift since the paper, so it is reported apart.
Exit 1 when any corpus is missing.
"""
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent


def ground_truth(d: Path, corpus: str) -> np.ndarray:
    rows = [l.split("\t") for l in (d / f"{corpus}_GroundTruth.txt").read_text(encoding="latin-1").splitlines() if l.strip()]
    return np.array([float(r[1]) for r in rows])


def verdict(r, row: dict, tol: float) -> str:
    if r is None:
        return "missing"
    if abs(r - row["paper_r"]) <= tol:
        return "match"
    return "mismatch, paper_row_suspect" if abs(row["code_2014_r"] - row["paper_r"]) > tol else "mismatch"


def check(scores: dict, gts: dict, cfg: dict) -> list:
    out = []
    for row in cfg["rows"]:
        s = scores.get(row["corpus"])
        gt = gts[row["corpus"]]
        r = None
        if s is not None:
            assert len(s) == len(gt) == row["n"], (row["corpus"], len(s), len(gt), row["n"])
            r = float(np.corrcoef(gt, np.asarray(s, dtype=float))[0, 1])
        out.append({**row, "measured_r": None if r is None else round(r, 4),
                    "verdict": verdict(r, row, cfg["tolerance"])})
    return out


def selftest() -> None:
    cfg = {"tolerance": 0.0005, "rows": [{"corpus": "a", "n": 4, "paper_r": 1.0, "code_2014_r": 1.0},
                                         {"corpus": "b", "n": 4, "paper_r": 1.0, "code_2014_r": 1.0},
                                         {"corpus": "c", "n": 4, "paper_r": 0.5, "code_2014_r": 0.9},
                                         {"corpus": "d", "n": 4, "paper_r": 1.0, "code_2014_r": 1.0}]}
    gt = np.array([1.0, 2.0, 3.0, 4.0])
    res = check({"a": [1, 2, 3, 4], "b": [1, 2, 4, 3], "c": [1, 2, 4, 3]}, {k: gt for k in "abcd"}, cfg)
    v = [x["verdict"] for x in res]
    assert v == ["match", "mismatch", "mismatch, paper_row_suspect", "missing"], v
    print("selftest ok")


def main() -> int:
    if sys.argv[1:] == ["--selftest"]:
        selftest()
        return 0
    data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    d = Path(sys.argv[2])
    cfg = json.loads(Path(sys.argv[3] if len(sys.argv) > 3 else ROOT / "configs/paper_vader.json").read_text(encoding="utf-8"))
    res = check(data["scores"], {r["corpus"]: ground_truth(d, r["corpus"]) for r in cfg["rows"]}, cfg)
    print("source:", data.get("source"))
    for x in res:
        print(f"  {x['verdict']:28} {x['corpus']}: measured {x['measured_r']}, paper {x['paper_r']}, 2014 code {x['code_2014_r']}")
    return 1 if any(x["verdict"] == "missing" for x in res) else 0


if __name__ == "__main__":
    sys.exit(main())
