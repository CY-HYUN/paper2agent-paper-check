# /// script
# requires-python = ">=3.10"
# ///
"""The second check: compare measured NDCG@10 with the numbers printed in the paper, not with another run.

    uv run scripts/paper_check.py results/tables/upstream_bm25s.json [--spec configs/paper_bm25s.json]
    uv run scripts/paper_check.py --selftest

A result file holds rows with method, k1, b, stopwords, stemmer, dataset and ndcg10 (0 to 1). The paper prints
NDCG@10 x 100 to one decimal, so a row is
  match     when 100 * ndcg10 rounds to the printed value,
  near      when it is within 0.15 of it (one rounding step plus float noise), and
  mismatch  otherwise, or when a paper row has no measured row at all (missing).
Exit 1 when any row is a mismatch or missing.
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KEY = ("method", "k1", "b", "stopwords", "stemmer")


def verdict(measured: float | None, paper: float) -> str:
    if measured is None:
        return "missing"
    pct = 100 * measured
    if round(pct, 1) == paper:
        return "match"
    return "near" if abs(pct - paper) <= 0.15 else "mismatch"


def check(result: dict, spec: dict) -> list[dict]:
    got = {tuple(r[k] for k in KEY) + (r["dataset"],): r["ndcg10"] for r in result["rows"]}
    out = []
    for row in spec["rows"]:
        for dataset, paper in row["values"].items():
            measured = got.get(tuple(row[k] for k in KEY) + (dataset,))
            out.append({**{k: row[k] for k in KEY}, "table": row["table"], "dataset": dataset, "paper": paper,
                        "measured": None if measured is None else round(100 * measured, 2),
                        "verdict": verdict(measured, paper)})
    return out


def selftest() -> None:
    assert verdict(0.6863, 68.6) == "match" and verdict(0.68649, 68.6) == "match"
    assert verdict(0.6863, 68.7) == "near" and verdict(0.6818, 68.3) == "near"
    assert verdict(0.6800, 68.3) == "mismatch" and verdict(None, 68.3) == "missing"
    spec = {"rows": [{"table": 2, "method": "lucene", "k1": 1.5, "b": 0.75, "stopwords": "english",
                      "stemmer": "snowball", "values": {"scifact": 68.7, "nfcorpus": 32.1}}]}
    res = {"rows": [{"method": "lucene", "k1": 1.5, "b": 0.75, "stopwords": "english", "stemmer": "snowball",
                     "dataset": "scifact", "ndcg10": 0.687}]}
    assert [r["verdict"] for r in check(res, spec)] == ["match", "missing"]
    print("selftest ok")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("result", nargs="?")
    p.add_argument("--spec", default=str(ROOT / "configs" / "paper_bm25s.json"))
    p.add_argument("--selftest", action="store_true")
    a = p.parse_args()
    if a.selftest:
        selftest()
        return 0
    result = json.loads(Path(a.result).read_text(encoding="utf-8"))
    rows = check(result, json.loads(Path(a.spec).read_text(encoding="utf-8")))
    print(f"producer: {result.get('producer', '?')}")
    for r in rows:
        if r["verdict"] != "match":
            print(f"  {r['verdict']:8} t{r['table']} {r['method']} k1={r['k1']} b={r['b']} stop={r['stopwords']} "
                  f"stem={r['stemmer']} {r['dataset']}: measured {r['measured']}, paper {r['paper']}")
    counts = {v: sum(r["verdict"] == v for r in rows) for v in ("match", "near", "mismatch", "missing")}
    print(f"{len(rows)} paper cells:", ", ".join(f"{k} {v}" for k, v in counts.items()))
    return 1 if counts["mismatch"] or counts["missing"] else 0


if __name__ == "__main__":
    sys.exit(main())
