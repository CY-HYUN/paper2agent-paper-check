"""Port the 2014 vaderSentiment.py (Python 2, shipped in hutto_ICWSM_2014.tar.gz) to Python 3 with the fewest edits:
drop reload(sys), unpack the lambda tuple, read the lexicon as latin-1 (Python 2 read bytes), cut the __main__ demo.
Then score the four corpora with it and with the current pip package, against the paper's Table 4 r values."""
import sys
import types
from pathlib import Path

import numpy as np

D = Path(sys.argv[1])
src = (D / "vaderSentiment.py").read_text(encoding="latin-1")
src = src.split("if __name__ == '__main__':")[0]
edits = [("reload(sys)\n", ""),
         ("dict(map(lambda (w, m): (w, float(m)), [", "dict(map(lambda wm: (wm[0], float(wm[1])), ["),
         ("for wmsr in open(f) ]", "for wmsr in open(f, encoding='latin-1') ]"),
         ("f = 'vader_sentiment_lexicon.txt'", f"f = r'{D / 'vader_sentiment_lexicon.txt'}'")]
for old, new in edits:
    assert src.count(old) == 1, old
    src = src.replace(old, new)
old = types.ModuleType("vader2014")
exec(compile(src, "vader2014", "exec"), old.__dict__)

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer  # noqa: E402
new = SentimentIntensityAnalyzer()
PAPER_R = {"tweets": 0.881, "movieReviewSnippets": 0.451, "amazonReviewSnippets": 0.565, "nytEditorialSnippets": 0.492}
print("lexicon entries 2014:", len(old.word_valence_dict), "| current:", len(new.lexicon))
for name, paper in PAPER_R.items():
    rows = [l.split("\t") for l in (D / f"{name}_GroundTruth.txt").read_text(encoding="latin-1").splitlines() if l.strip()]
    gt = np.array([float(r[1]) for r in rows])
    p14 = np.array([old.sentiment(r[2])["compound"] for r in rows])
    pnow = np.array([new.polarity_scores(r[2])["compound"] for r in rows])
    r14, rnow = np.corrcoef(gt, p14)[0, 1], np.corrcoef(gt, pnow)[0, 1]
    changed = int((np.abs(p14 - pnow) > 1e-4).sum())
    print(f"{name}: n={len(rows)} paper r={paper:.3f} | 2014 code r={r14:.3f} | current r={rnow:.3f} | "
          f"items whose score changed {changed}/{len(rows)}")
