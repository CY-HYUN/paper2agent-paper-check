# paper2agent-paper-check

Does a tool that Paper2Agent built and verified still reproduce the numbers printed in the paper?

[Paper2Agent](https://github.com/jmiao24/Paper2Agent) (Miao et al., Nature 2026) turns a research repository into
MCP tools. Its verification compares each tool's output with a run of the repository's own code on the same input
(`skills/paper2agent/paper2mcp/SKILL.md`, "Run the bound upstream code ... Preserve native results ... for
comparison"). Nothing in that loop looks at the paper. If the repository has drifted from the paper, or a wrapper
changes a default, both sides of the comparison move together and the check still passes.

This project adds a second check whose reference is the paper's table, and counts the tools that pass Paper2Agent's
check but fail the paper's.

## Pilot: BM25S (arXiv 2407.03618)

[bm25s](https://github.com/xhluca/bm25s) is small, CPU-only and deterministic, and its paper prints NDCG@10 for every
BEIR dataset under ten scoring settings (tables 2 and 3). The four smallest datasets (ArguAna, NFCorpus, SCIDOCS,
SciFact) give 40 paper cells, in `configs/paper_bm25s.json`.

### Step 1, the reference: bm25s itself, no agent (2026-11-21)

`scripts/run_bm25s_upstream.py` runs bm25s 0.3.16 on every cell; `scripts/paper_check.py` compares with the paper.

| verdict | rule | cells |
|---|---|---|
| match | 100 x NDCG@10 rounds to the printed value | 23 |
| near | within 0.15 of it | 17 |
| mismatch | further away | 0 |

So the repository, called directly, still reproduces the paper to within 0.15 points in all 40 cells. The near cells
go both ways (ArguAna and SCIDOCS slightly above the paper, SciFact 0.07 to 0.12 below), so one rounding rule does not
explain them; the paper-era release (0.1.7) was not run, because its data loaders differ.

Found on the way: `bm25s.utils.beir` opens the dataset files without an encoding, so on a Windows code page other
than UTF-8 the text would be decoded wrongly and silently. The script stops unless Python's preferred encoding is
UTF-8 (this machine reports cp65001, which is UTF-8).

### Step 2, Paper2Agent on bm25s: not run yet

`scripts/run_paper2agent.ps1` runs Paper2Agent (commit 8c2d059) unattended with the model pinned, the skill installed
for the run directory only, and bm25s pinned at commit b335013. A first start on 2026-11-21 was stopped after about
90 seconds on purpose: the account had used 84% of its weekly limit, and a multi-agent run could take the rest before
the weekly reset.

### Step 3, the paper check on the generated tools: after step 2

The same `paper_check.py` will read the NDCG@10 the generated tools return for the 40 settings.

## Run

```bash
PYTHONUTF8=1 uv run scripts/run_bm25s_upstream.py   # step 1, about 5 minutes on a laptop CPU, datasets cached in data/raw
uv run scripts/paper_check.py results/tables/upstream_bm25s.json
uv run scripts/paper_check.py --selftest
```

## Folder map

`configs/` the paper's numbers · `scripts/` the runs and the check · `results/tables/` measured rows ·
`docs/` method notes · `_local/` third-party checkouts and run scratch (not committed).
