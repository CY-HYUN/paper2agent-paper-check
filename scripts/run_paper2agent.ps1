# Run Paper2Agent unattended on one repository, as its README tells a user to (the skill installed for the project
# only, one prompt), with the model pinned. Launcher for this machine: Windows, Claude Code signed in with a
# subscription, run directory outside the workspace so no workspace CLAUDE.md is picked up.
#
#   pwsh scripts/run_paper2agent.ps1 -RunDir <new folder outside the workspace>\001_bm25s
#
# --setting-sources project skips the user settings (and so the personal hooks and stop gates); the user CLAUDE.md
# is still read by Claude Code, so the appended system prompt says it does not apply. That is a known difference
# from a clean machine and goes into the README with the run's results.
param(
    [Parameter(Mandatory = $true)][string]$RunDir,
    [string]$Model = "claude-opus-5-5",
    [string]$SkillSrc = (Join-Path $PSScriptRoot "..\_local\Paper2Agent\skills\paper2agent"),
    [string]$Repo = "https://github.com/xhluca/bm25s",
    [string]$Commit = "b335013d0172e8c2aabd1399d60146cc51768458",
    [string]$Focus = "the BEIR evaluation workflow in examples/evaluate_on_beir.py (index a BEIR dataset with a chosen BM25 variant, k1, b, stopwords and stemmer, retrieve, and report NDCG@10), plus indexing and retrieval on a user corpus",
    [string]$AgentName = "bm25s_Agent"
)
$ErrorActionPreference = "Stop"
if (Test-Path $RunDir) { throw "$RunDir exists; use a new run directory" }
New-Item -ItemType Directory -Force (Join-Path $RunDir ".claude\skills") | Out-Null
Copy-Item -Recurse $SkillSrc (Join-Path $RunDir ".claude\skills\paper2agent")
$prompt = @"
Use the paper2agent skill to convert the research code repository $Repo (check out commit $Commit) into tested MCP tools in $RunDir\$AgentName.
Focus on $Focus.
Resources: CPU only, no GPU, about 12 GB of RAM free. No API keys are needed. Do not ask questions; every required input is above. Follow the skill instructions for the workflow, verification, and final delivery.
"@
$append = "This is an unattended Paper2Agent run for a reproducibility study. Follow the paper2agent skill exactly. Instructions from the user-level CLAUDE.md (language, audit files, memory, commits, reports) do not apply to this run; write in English."
Set-Content -Path (Join-Path $RunDir "prompt.txt") -Value $prompt -Encoding utf8
$meta = [ordered]@{ started = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ"); model = $Model; repo = $Repo
    commit = $Commit; claude = (claude --version); skill_commit = (git -C (Join-Path $SkillSrc "..\..") rev-parse HEAD) }
$meta | ConvertTo-Json | Set-Content -Path (Join-Path $RunDir "run_meta.json") -Encoding utf8
Push-Location $RunDir
try {
    claude -p $prompt --model $Model --setting-sources project --permission-mode acceptEdits `
        --allowedTools "Bash" "PowerShell" "Agent" "Task" "Read" "Write" "Edit" "Glob" "Grep" "WebFetch" "Skill" `
        --append-system-prompt $append --output-format stream-json --verbose --no-chrome `
        *> (Join-Path $RunDir "transcript.jsonl")
    "exit $LASTEXITCODE" | Set-Content -Path (Join-Path $RunDir "exit.txt")
} finally { Pop-Location }
