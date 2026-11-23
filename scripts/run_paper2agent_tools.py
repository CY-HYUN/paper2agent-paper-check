"""Step 3: call the MCP server Paper2Agent built, over stdio as a client would, for every paper cell.

    # run with the Python environment Paper2Agent prepared, which already holds the MCP SDK the server uses
    # (mcp 2.3.0 on 2026-11-23; a separately pinned mcp 1.21.0 failed to import against pydantic 2.14)
    <bm25s_Agent>/bm25s-env/Scripts/python.exe scripts/run_paper2agent_tools.py <path to bm25s_Agent>
    # writes results/tables/paper2agent_bm25s.json
    uv run scripts/paper_check.py results/tables/paper2agent_bm25s.json

The server is started with the Python environment Paper2Agent prepared (bm25s-env) and its own entry point
(src/bm25s_mcp.py); nothing of the generated code is changed. One call per (row, dataset) to bm25s_evaluate_beir_dataset.
"""
import asyncio
import json
import sys
import time
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parent.parent
TOOL = "bm25s_evaluate_beir_dataset"


def ndcg10(payload: dict) -> float:
    """The tool's NDCG@10, wherever the result dict keeps it (checked on the first call and printed)."""
    for key in ("ndcg", "NDCG"):
        if isinstance(payload.get(key), dict) and "NDCG@10" in payload[key]:
            return float(payload[key]["NDCG@10"])
    metrics = payload.get("metrics") or {}
    for key in ("ndcg", "NDCG"):
        if isinstance(metrics.get(key), dict) and "NDCG@10" in metrics[key]:
            return float(metrics[key]["NDCG@10"])
    raise KeyError(f"no NDCG@10 in the tool result; keys: {sorted(payload)}")


async def main(agent: Path) -> None:
    spec = json.loads((ROOT / "configs" / "paper_bm25s.json").read_text(encoding="utf-8"))
    params = StdioServerParameters(command=str(agent / "bm25s-env" / "Scripts" / "python.exe"),
                                   args=[str(agent / "src" / "bm25s_mcp.py")], cwd=str(agent))
    out = {"producer": f"Paper2Agent-generated MCP server at {agent.name}, tool {TOOL}, called over stdio",
           "started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "rows": []}
    async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
        await session.initialize()
        names = [t.name for t in (await session.list_tools()).tools]
        print("tools:", names, flush=True)
        first = True
        for row in spec["rows"]:
            for dataset in row["values"]:
                args = {"dataset": dataset, "method": row["method"], "k1": row["k1"], "b": row["b"],
                        "stopwords": row["stopwords"] or "none",
                        "stemmer_language": "english" if row["stemmer"] == "snowball" else None,
                        "k_values": [10], "data_dir": str(ROOT / "data" / "raw" / "beir_tool")}
                res = await session.call_tool(TOOL, args)
                if res.is_error:  # mcp 2.x field names (CallToolResult.model_fields, checked 2026-11-23)
                    raise RuntimeError(f"{dataset} {row}: {res.content[0].text[:500]}")
                payload = res.structured_content or json.loads(res.content[0].text)
                payload = payload.get("result", payload) if isinstance(payload, dict) else payload
                if first:
                    print("first result keys:", sorted(payload), flush=True)
                    first = False
                value = ndcg10(payload)
                out["rows"].append({k: row[k] for k in ("table", "method", "k1", "b", "stopwords", "stemmer")}
                                   | {"dataset": dataset, "ndcg10": value})
                print(f"  t{row['table']} {row['method']} k1={row['k1']} b={row['b']} stop={row['stopwords']} "
                      f"stem={row['stemmer']} {dataset}: {100 * value:.2f} (paper {row['values'][dataset]})", flush=True)
    dest = ROOT / "results" / "tables" / "paper2agent_bm25s.json"
    if dest.exists():
        sys.exit(f"{dest.relative_to(ROOT)} exists; move it before a new run")
    dest.write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    print("wrote", dest.relative_to(ROOT))


if __name__ == "__main__":
    asyncio.run(main(Path(sys.argv[1]).resolve()))
