"""Figure for the README: how far each code's Pearson r sits from the number printed in the VADER paper's Table 4.
Draws a light and a dark SVG (GitHub picks one with <picture>). r is computed here from the committed score files and
the paper's ground truth, so the figure cannot drift from the results.

  uv run --no-project --with numpy --with matplotlib python -I scripts/make_figure.py <extracted hutto_ICWSM_2014 dir>
"""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
HUTTO = Path(sys.argv[1])
CFG = json.loads((ROOT / "configs/paper_vader.json").read_text(encoding="utf-8"))
ORDER = ["tweets", "nytEditorialSnippets", "movieReviewSnippets", "amazonReviewSnippets"]
LABEL = {"tweets": "Tweets", "nytEditorialSnippets": "NYT editorials",
         "movieReviewSnippets": "Movie reviews", "amazonReviewSnippets": "Amazon reviews"}
CHECKED = {"tweets", "nytEditorialSnippets"}  # the other two: the paper's VADER row itself is in doubt
THEMES = {
    "light": dict(bg="#fcfcfb", ink="#0b0b0b", ink2="#52514e", muted="#898781", grid="#e1e0d9", axis="#c3c2b7",
                  band="#ecebe6", old="#2a78d6", now="#eb6834"),
    "dark": dict(bg="#1a1a19", ink="#f0efec", ink2="#c3c2b7", muted="#898781", grid="#2c2c2a", axis="#383835",
                 band="#2a2a28", old="#3987e5", now="#d95926"),
}


def r_values():
    paper = {row["corpus"]: row["paper_r"] for row in CFG["rows"]}
    load = lambda f: json.loads((ROOT / "results/vader" / f).read_text(encoding="utf-8"))["scores"]
    old, now, tool = load("scores_code_2014.json"), load("scores_head_44fc044.json"), load("scores_paper2agent.json")
    out = {}
    for c in ORDER:
        rows = [l.split("\t") for l in (HUTTO / f"{c}_GroundTruth.txt").read_text(encoding="latin-1").splitlines()
                if l.strip()]
        gt = np.array([float(r[1]) for r in rows])
        assert len(gt) == len(old[c]) == len(now[c]) == len(tool[c]), c
        assert np.allclose(now[c], tool[c], atol=1e-9), f"{c}: tool differs from the repo run"
        r = lambda s: float(np.corrcoef(gt, np.asarray(s, dtype=float))[0, 1])
        out[c] = dict(paper=paper[c], old=r(old[c]), now=r(now[c]), n=len(gt))
    return out


def draw(vals, theme, path):
    t = THEMES[theme]
    plt.rcParams.update({"font.family": ["Segoe UI", "DejaVu Sans"], "svg.fonttype": "path"})
    fig, ax = plt.subplots(figsize=(8.2, 4.1), dpi=100)
    fig.patch.set_facecolor(t["bg"]); ax.set_facecolor(t["bg"])
    tol = CFG["tolerance"]
    xmin, xmax = -0.042, 0.034
    ax.set_xlim(xmin, xmax); ax.set_ylim(4.35, -0.75)
    # the paper's value and the band that still rounds to it
    ax.axvspan(-tol, tol, color=t["band"], zorder=0, lw=0)
    ax.axvline(0, color=t["ink2"], lw=1, zorder=1)
    ax.text(0, -0.5, "paper's printed r", ha="center", va="bottom", fontsize=9, color=t["ink2"], bbox=dict(fc=t["bg"], ec="none", pad=2), zorder=4)
    for x in np.arange(-0.04, 0.031, 0.01):
        if abs(x) > 1e-9:
            ax.axvline(x, color=t["grid"], lw=0.6, zorder=0)
    ys = {c: i + (0.35 if c not in CHECKED else 0) for i, c in enumerate(ORDER)}
    ax.axhline(1.85, color=t["axis"], lw=0.8, ls=(0, (2, 3)))
    for c, y in ys.items():
        v = vals[c]
        d_old, d_now = v["old"] - v["paper"], v["now"] - v["paper"]
        dim = c not in CHECKED
        alpha = 0.45 if dim else 1
        ax.plot([d_old, d_now], [y, y], color=t["axis"], lw=2, zorder=2, alpha=alpha, solid_capstyle="round")
        ax.scatter([d_old], [y], s=70, color=t["old"], zorder=3, alpha=alpha, edgecolors=t["bg"], linewidths=1.5)
        ax.scatter([d_now], [y], s=70, marker="D", color=t["now"], zorder=3, alpha=alpha, edgecolors=t["bg"],
                   linewidths=1.5)
        ax.text(xmin - 0.001, y, LABEL[c], ha="right", va="center", fontsize=11,
                color=t["muted"] if dim else t["ink"], fontweight="normal" if dim else "semibold")
        ax.text(xmin - 0.001, y + 0.3, f"n = {v['n']:,}", ha="right", va="center", fontsize=8.5, color=t["muted"])
        if not dim:
            side = 1 if d_now > 0 else -1
            ax.text(d_now + side * 0.0016, y, f"{d_now:+.3f}".replace("-", "\u2212"), ha="left" if side > 0 else "right", va="center",
                    fontsize=10, color=t["now"], fontweight="semibold")
    ax.text(xmin + 0.0005, 2.02, "Not counted: the 2014 code misses the paper here too, and matches the paper's row for another method",
            ha="left", va="center", fontsize=8.5, color=t["muted"], bbox=dict(fc=t["bg"], ec="none", pad=1.5), zorder=4)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_yticks([])
    ax.tick_params(axis="x", colors=t["muted"], labelsize=9, length=0, pad=6)
    ax.set_xticks([-0.04, -0.02, 0, 0.02])
    ax.set_xticklabels(["−0.04", "−0.02", "0", "+0.02"])
    ax.set_xlabel("Pearson r minus the paper's value", color=t["ink2"], fontsize=9.5, labelpad=8)
    fig.text(0.015, 0.965, "The 2014 code reproduces the paper. Today's code, and the tool built from it, do not.",
             fontsize=12.5, fontweight="semibold", color=t["ink"], ha="left", va="top")
    # legend as one line of text with the two marks, under the title
    fig.text(0.015, 0.895, "●", color=t["old"], fontsize=11, ha="left", va="top")
    fig.text(0.04, 0.89, "2014 code shipped with the paper", color=t["ink2"], fontsize=9.5, ha="left", va="top")
    fig.text(0.36, 0.895, "◆", color=t["now"], fontsize=11, ha="left", va="top")
    fig.text(0.385, 0.89, "repo today (44fc044) = Paper2Agent tool, identical on all 23,703 sentences",
             color=t["ink2"], fontsize=9.5, ha="left", va="top")
    fig.subplots_adjust(left=0.2, right=0.975, top=0.8, bottom=0.14)
    fig.savefig(path, facecolor=t["bg"])
    plt.close(fig)


def main():
    vals = r_values()
    out = ROOT / "results/figures"
    out.mkdir(parents=True, exist_ok=True)
    for theme in THEMES:
        draw(vals, theme, out / f"vader_paper_gap_{theme}.svg")
    print(json.dumps({c: {k: round(v, 4) if isinstance(v, float) else v for k, v in d.items()} for c, d in vals.items()}))


if __name__ == "__main__":
    main()
