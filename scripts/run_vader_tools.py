"""Call the VADER MCP server Paper2Agent built, over stdio as a client would, on the four ICWSM-14 corpora.

    <vader_Agent>/vaderSentiment-env/Scripts/python.exe scripts/run_vader_tools.py <vader_Agent> <hutto_ICWSM_2014 dir>
    uv run --no-project --with numpy python scripts/vader_paper_check.py results/vader/scores_paper2agent.json <hutto dir>

Each corpus's text column goes into a UTF-8 file, one text per line, in ground-truth order; one call of
vader_score_text_file_lines per corpus with skip_blank_lines off, so line i of the TSV is ground-truth row i.
Nothing of the generated code is changed.
"""
import asyncio
import csv
import json
import sys
import tempfile
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parent.parent
TOOL = "vader_score_text_file_lines"
CORPORA = ("tweets", "movieReviewSnippets", "amazonReviewSnippets", "nytEditorialSnippets")


async def main(agent: Path, data: Path) -> None:
    params = StdioServerParameters(command=str(agent / "vaderSentiment-env" / "Scripts" / "python.exe"),
                                   args=[str(agent / "src" / "vaderSentiment_mcp.py")], cwd=str(agent))
    out = {"source": f"Paper2Agent-generated MCP server at {agent.name}, tool {TOOL}, called over stdio", "scores": {}}
    tmp = Path(tempfile.mkdtemp(prefix="vader_tool_"))
    async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
        await session.initialize()
        print("tools:", [t.name for t in (await session.list_tools()).tools], flush=True)
        for c in CORPORA:
            texts = [l.split("\t")[2] for l in (data / f"{c}_GroundTruth.txt").read_text(encoding="latin-1").splitlines()
                     if l.strip()]
            src = tmp / f"{c}.txt"
            src.write_text("\n".join(texts) + "\n", encoding="utf-8", newline="")
            res = await session.call_tool(TOOL, {"data_path": str(src), "skip_blank_lines": False,
                                                 "output_dir": str(tmp / "out")})
            if res.is_error:
                raise RuntimeError(f"{c}: {res.content[0].text[:500]}")
            payload = res.structured_content or json.loads(res.content[0].text)
            payload = payload.get("result", payload)
            tsv = Path(payload["artifacts"][0]["path"])
            with tsv.open(encoding="utf-8", newline="") as f:
                rows = list(csv.DictReader(f, delimiter="\t"))
            assert [int(r["line_number"]) for r in rows] == list(range(1, len(texts) + 1)), c
            assert [r["text"] for r in rows] == texts, f"{c}: tool text differs from the input"
            out["scores"][c] = [float(r["compound"]) for r in rows]
            print(f"  {c}: {payload['lines_scored']} of {payload['lines_read']} lines scored", flush=True)
    dest = ROOT / "results" / "vader" / "scores_paper2agent.json"
    if dest.exists():
        sys.exit(f"{dest.relative_to(ROOT)} exists; move it before a new run")
    dest.write_text(json.dumps(out), encoding="utf-8")
    print("wrote", dest.relative_to(ROOT))


if __name__ == "__main__":
    asyncio.run(main(Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()))
