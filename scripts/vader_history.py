"""Score the paper's four corpora with every vaderSentiment commit that changed the package, to find which change
moved Table 4's r. Each commit's vaderSentiment/ folder is read with `git show` (no checkout), the module is exec'd
with the fewest Python 3 edits (as in vader_2014_vs_now.py), and the lexicon is read as UTF-8 or else latin-1.

  python -I scripts/vader_history.py <vaderSentiment clone> <extracted hutto_ICWSM_2014 dir> results/vader/history.json
"""
import io
import json
import re
import subprocess
import sys
import tempfile
import time
import types
from pathlib import Path

import numpy as np

REPO, HUTTO, OUT = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
PAPER_R = {"tweets": 0.881, "movieReviewSnippets": 0.451, "amazonReviewSnippets": 0.565, "nytEditorialSnippets": 0.492}
git = lambda *a: subprocess.run(["git", "-C", str(REPO), *a], capture_output=True, check=True).stdout


def corpora():
    out = {}
    for name in PAPER_R:
        rows = [l.split("\t") for l in (HUTTO / f"{name}_GroundTruth.txt").read_text(encoding="latin-1").splitlines()
                if l.strip()]
        out[name] = (np.array([float(r[1]) for r in rows]), [r[2] for r in rows])
    return out


def lenient_open(path, mode="r", *args, **kwargs):
    # the 2014 lexicon is latin-1, later ones UTF-8; Python 2 read bytes either way
    if "b" in mode or "w" in mode or "a" in mode:
        return open(path, mode, *args, **kwargs)
    raw = Path(path).read_bytes()
    try:
        return io.StringIO(raw.decode("utf-8"))
    except UnicodeDecodeError:
        return io.StringIO(raw.decode("latin-1"))


def py3(src):
    src = src.split("if __name__ == '__main__':")[0].split('if __name__ == "__main__":')[0]
    src = src.replace("reload(sys)\n", "")
    return re.sub(r"^\s*sys\.setdefaultencoding\(.*\)\s*$", "", src, flags=re.M)


def load(sha, workdir):
    names = git("ls-tree", "--name-only", sha, "vaderSentiment/").decode().split()
    for n in names:
        (workdir / Path(n).name).write_bytes(git("show", f"{sha}:{n}"))
    path = workdir / "vaderSentiment.py"
    src = path.read_bytes().decode("utf-8", "replace")
    mod = types.ModuleType(f"vader_{sha}")
    mod.__dict__.update(__file__=str(path), open=lenient_open, unicode=str)  # 2014-12 code calls unicode()
    try:
        code = compile(src.split("if __name__ == '__main__':")[0], str(path), "exec")
    except SyntaxError:
        src2 = src.replace("dict(map(lambda (w, m): (w, float(m)), [",
                           "dict(map(lambda wm: (wm[0], float(wm[1])), [")
        code = compile(py3(src2), str(path), "exec")
    import os
    cwd = os.getcwd()
    os.chdir(workdir)  # some versions open the lexicon by bare file name
    try:
        exec(code, mod.__dict__)
        if hasattr(mod, "SentimentIntensityAnalyzer"):
            sia = mod.SentimentIntensityAnalyzer()
            return lambda t: sia.polarity_scores(t)["compound"]
        neg = getattr(mod, "negated", None)
        if neg is not None and neg.__defaults__ and isinstance(neg.__defaults__[0], list):
            # 2014-12 code: negated(list, nWords=[]) extends its mutable default with NEGATE on every call, so each call
            # gets slower (1,716 tweets in 120 s). The list only ever holds NEGATE again, so resetting it per call
            # leaves every score unchanged and only removes the slowdown.
            fresh = neg.__defaults__[1:]
            def score(t):
                neg.__defaults__ = ([],) + fresh
                return mod.sentiment(t)["compound"]
            sample = [t for _, texts in corpora().values() for t in texts[:150]]
            plain = [mod.sentiment(t)["compound"] for t in sample]  # the unpatched behaviour, defaults still growing
            assert plain == [score(t) for t in sample], f"{sha}: resetting negated() changed a score"
            return score
        return lambda t: mod.sentiment(t)["compound"]
    finally:
        os.chdir(cwd)


def main():
    data = corpora()
    log = git("log", "--reverse", "--format=%h%x09%ad%x09%s", "--date=short", "--", "vaderSentiment/").decode()
    rows, prev, seen = [], None, {}
    for line in log.splitlines():
        sha, date, subject = line.split("\t", 2)
        rec = {"commit": sha, "date": date, "subject": subject[:90]}
        # commits that leave the module and its lexicons byte-identical score the same: reuse, do not rerun
        state = git("ls-tree", sha, "vaderSentiment/vaderSentiment.py", "vaderSentiment/vader_sentiment_lexicon.txt",
                    "vaderSentiment/vader_lexicon.txt", "vaderSentiment/emoji_utf8_lexicon.txt")
        if state in seen:
            rec.update({k: v for k, v in seen[state].items() if k in ("r", "error")}, same_as=seen[state]["commit"])
            rows.append(rec)
            print(sha, date, "same package files as", rec["same_as"], flush=True)
            continue
        seen[state] = rec
        t0 = time.time()
        try:
            with tempfile.TemporaryDirectory() as td:
                score = load(sha, Path(td))
                scores = {n: np.array([score(t) for t in texts]) for n, (gt, texts) in data.items()}
            rec["r"] = {n: round(float(np.corrcoef(data[n][0], s)[0, 1]), 4) for n, s in scores.items()}
            if prev is not None:
                rec["changed_vs_prev"] = {n: int((np.abs(scores[n] - prev[n]) > 1e-4).sum()) for n in scores}
            prev = scores
        except Exception as e:  # recorded per commit, never silently dropped
            rec["error"] = f"{type(e).__name__}: {str(e)[:160]}"
        rec["seconds"] = round(time.time() - t0, 1)
        rows.append(rec)
        print(sha, date, rec.get("r", {}).get("tweets"), rec.get("r", {}).get("nytEditorialSnippets"),
              rec.get("error", ""), f"{rec['seconds']}s", flush=True)
    OUT.write_text(json.dumps({"what": "Table 4 r per vaderSentiment commit that touched vaderSentiment/",
                               "paper_r": PAPER_R, "rows": rows}, indent=1), encoding="utf-8")
    scored = [r for r in rows if "r" in r]
    print(f"scored {len(scored)} of {len(rows)} commits")
    # calibration: the first public commit should score like the 2014 code shipped with the paper (0.881 on tweets)
    assert scored and abs(scored[0]["r"]["tweets"] - 0.881) < 0.0005, scored[:1]


if __name__ == "__main__":
    main()
