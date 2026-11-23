# paper2agent-paper-check

Does a tool that Paper2Agent built and verified still reproduce the numbers printed in the paper?

[Paper2Agent](https://github.com/jmiao24/Paper2Agent) (Miao et al., Nature 2026) turns a research repository into
MCP tools. Its verification compares each tool's output with a run of the repository's own code on the same input
(`skills/paper2agent/paper2mcp/SKILL.md`, "Run the bound upstream code ... Preserve native results ... for
comparison"). The skill draws that line on purpose: a delivery "does not claim the whole repository or paper has
been reproduced" (`paper2mcp/references/output-delivery.md`), and paper-to-code work is "outside this conversion
task" (`tool-selection-and-wrapping.md`). So if the repository has drifted from the paper, or a wrapper changes a
default, both sides of the comparison move together and the check still passes. This project measures that declared
gap; it is not a claim that Paper2Agent is wrong.

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

### Step 2, Paper2Agent on bm25s (2026-11-23)

`scripts/run_paper2agent.ps1` ran Paper2Agent (commit 8c2d059) unattended on Windows with Claude Opus 5.5 pinned, the
skill installed for the run directory only, and bm25s pinned at commit b335013. It finished in about 73 minutes
(20:44 to 21:58 UTC) and delivered `bm25s-mcp.zip` with three tools: `bm25s_evaluate_beir_dataset`,
`bm25s_index_corpus` and `bm25s_retrieve_from_index`. Its own report: 119 tests written by agents that did not write
the code, all passing, and the tools' results identical to its reference runs of the upstream examples. The run's
result event reports an API-equivalent cost of USD 17.02 (the run used a subscription, so this is a size, not a bill).
A first start on 2026-11-21 had been stopped after about 90 seconds because the weekly limit was at 84%.

### Step 3, the paper check on the generated tools (2026-11-23)

`scripts/run_paper2agent_tools.py` starts the generated server unchanged, with the Python environment Paper2Agent
prepared, and calls `bm25s_evaluate_beir_dataset` over stdio for all 40 paper cells.

| | match | near | mismatch |
|---|---|---|---|
| bm25s called directly (step 1) | 23 | 17 | 0 |
| the Paper2Agent tool | 23 | 17 | 0 |

The tool's NDCG@10 equals the direct run's in all 40 cells (no difference at full float precision), so it inherits the
repository's agreement with the paper. For this pilot the count this project asks for is **0 tools that pass
Paper2Agent's check and fail the paper's**. The other two tools (index, retrieve) have no number in the paper, so the
paper check does not apply to them.

What the null result does and does not say: here the repository itself still reproduces the paper, and the tool
wraps it without changing a default that matters. The second check can only catch a gap when there is one; one small,
deterministic repository is not evidence that Paper2Agent never drifts from a paper. A repository whose code has moved
away from its paper is the next test.

## Run

```bash
uv run scripts/run_bm25s_upstream.py   # step 1, about 5 minutes on a laptop CPU, datasets cached in data/raw
uv run scripts/paper_check.py results/tables/upstream_bm25s.json
uv run scripts/paper_check.py --selftest
pwsh scripts/run_paper2agent.ps1 -RunDir <new folder>          # step 2, Windows, Claude Code signed in
<bm25s_Agent>/bm25s-env/Scripts/python.exe scripts/run_paper2agent_tools.py <bm25s_Agent>   # step 3
uv run scripts/paper_check.py results/tables/paper2agent_bm25s.json
```

## Folder map

`configs/` the paper's numbers · `scripts/` the runs and the check · `results/tables/` measured rows ·
`docs/` method notes · `_local/` third-party checkouts and run scratch (not committed).
