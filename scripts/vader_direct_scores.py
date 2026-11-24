"""Write compound scores for the four corpora from the installed vaderSentiment, or from the 2014 code in the tarball.

    python scripts/vader_direct_scores.py <hutto_ICWSM_2014 dir> <out.json> [--code-2014]
"""
import json
import sys
import types
from pathlib import Path

CORPORA = ("tweets", "movieReviewSnippets", "amazonReviewSnippets", "nytEditorialSnippets")


def load_2014(d: Path):
    src = (d / "vaderSentiment.py").read_text(encoding="latin-1").split("if __name__ == '__main__':")[0]
    for old, new in [("reload(sys)\n", ""),
                     ("dict(map(lambda (w, m): (w, float(m)), [", "dict(map(lambda wm: (wm[0], float(wm[1])), ["),
                     ("for wmsr in open(f) ]", "for wmsr in open(f, encoding='latin-1') ]"),
                     ("f = 'vader_sentiment_lexicon.txt'", f"f = r'{d / 'vader_sentiment_lexicon.txt'}'")]:
        assert src.count(old) == 1, old
        src = src.replace(old, new)
    m = types.ModuleType("vader2014")
    exec(compile(src, "vader2014", "exec"), m.__dict__)
    return lambda t: m.sentiment(t)["compound"], "vaderSentiment.py of 2014 (tarball), ported to Python 3"


def main() -> None:
    d, out = Path(sys.argv[1]), Path(sys.argv[2])
    if "--code-2014" in sys.argv:
        fn, source = load_2014(d)
    else:
        import importlib.metadata as md
        from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
        an = SentimentIntensityAnalyzer()
        fn, source = (lambda t: an.polarity_scores(t)["compound"]), f"vaderSentiment {md.version('vaderSentiment')} (direct)"
    scores = {}
    for c in CORPORA:
        rows = [l.split("\t") for l in (d / f"{c}_GroundTruth.txt").read_text(encoding="latin-1").splitlines() if l.strip()]
        scores[c] = [fn(r[2]) for r in rows]
    out.write_text(json.dumps({"source": source, "scores": scores}), encoding="utf-8")
    print(source, {c: len(v) for c, v in scores.items()})


if __name__ == "__main__":
    main()
