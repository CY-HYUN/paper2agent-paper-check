# /// script
# requires-python = ">=3.10"
# dependencies = ["bm25s==0.3.16", "PyStemmer==3.1.0", "pytrec-eval-terrier==0.5.11", "numpy<3", "tqdm"]  # tqdm: beir.download_dataset imports it
# ///
"""The paper check's ground truth: run bm25s itself (no agent) on every row of configs/paper_bm25s.json.

    uv run scripts/run_bm25s_upstream.py                # writes results/tables/upstream_bm25s.json    uv run scripts/paper_check.py results/tables/upstream_bm25s.json

Corpus text is title + " " + text and k=1000, as in the repository's examples/evaluate_on_beir.py; NDCG@10 comes
from bm25s.utils.beir.evaluate (BEIR's pytrec_eval code). Datasets are cached in data/raw/beir (not committed).
"""
import json
import platform
import sys
import time
from pathlib import Path

import bm25s
import Stemmer
from bm25s.utils.beir import (
    download_dataset,
    evaluate,
    load_corpus,
    load_qrels,
    load_queries,
)

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "raw" / "beir"


def load(dataset: str):
    download_dataset(dataset, save_dir=str(DATA))
    corpus = load_corpus(dataset, save_dir=str(DATA), show_progress=False)
    queries = load_queries(dataset, save_dir=str(DATA), show_progress=False)
    qrels = load_qrels(dataset, split="test", save_dir=str(DATA), show_progress=False)
    qids = [q for q in queries if q in qrels]  # BEIR evaluates the queries that have judgements
    return corpus, [queries[q]["text"] for q in qids], qids, qrels


def score(row: dict, corpus: dict, query_texts: list, qids: list, qrels: dict) -> float:
    stemmer = Stemmer.Stemmer("english") if row["stemmer"] == "snowball" else None
    doc_ids = list(corpus)
    texts = [(corpus[d]["title"] or "") + " " + corpus[d]["text"] for d in doc_ids]  # load_corpus sets a missing title to None
    c_tok = bm25s.tokenize(texts, stopwords=row["stopwords"], stemmer=stemmer, show_progress=False)
    q_tok = bm25s.tokenize(query_texts, stopwords=row["stopwords"], stemmer=stemmer, show_progress=False)
    model = bm25s.BM25(method=row["method"], k1=row["k1"], b=row["b"])
    model.index(c_tok, show_progress=False)
    hits, scores = model.retrieve(q_tok, corpus=doc_ids, k=min(1000, len(doc_ids)), show_progress=False)
    run = {qid: {d: float(s) for d, s in zip(hits[i], scores[i])} for i, qid in enumerate(qids)}
    ndcg, *_ = evaluate(qrels, run, [10])
    return ndcg["NDCG@10"]


def main() -> None:
    spec =json.loads((ROOT / "configs" / "paper_bm25s.json").read_text(encoding="utf-8"))
    datasets = sorted({d for r in spec["rows"] for d in r["values"]})
    out = {"producer": f"bm25s {bm25s.__version__} called directly", "python": platform.python_version(),
           "started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "rows": []}
    for dataset in datasets:
        corpus, query_texts, qids, qrels = load(dataset)
        print(f"{dataset}: {len(corpus)} documents, {len(qids)} judged queries", flush=True)
        for row in spec["rows"]:
            ndcg = score(row, corpus, query_texts, qids, qrels)
            out["rows"].append({k: row[k] for k in ("table", "method", "k1", "b", "stopwords", "stemmer")}
                               | {"dataset": dataset, "ndcg10": ndcg})
            print(f"  t{row['table']} {row['method']} k1={row['k1']} b={row['b']} stop={row['stopwords']} "
                  f"stem={row['stemmer']}: {100 * ndcg:.2f} (paper {row['values'][dataset]})", flush=True)
    dest = ROOT / "results" / "tables" / (sys.argv[1] if len(sys.argv) > 1 else "upstream_bm25s.json")
    if dest.exists():  # a second run (another bm25s version) must not overwrite the first
        sys.exit(f"{dest.relative_to(ROOT)} exists; pass another file name")
    dest.write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    print("wrote", dest.relative_to(ROOT))


if __name__ == "__main__":
    sys.exit(main())
