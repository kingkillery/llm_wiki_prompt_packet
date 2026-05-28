# Pro GPT QA Prompt

Use Desktop Commander to QA this repository:

`C:\dev\Desktop-Projects\llm_wiki_prompt_packet\llm_wiki_prompt_packet`

You are a pro GPT code reviewer. Perform a practical QA pass over the repo, focusing on bugs, broken workflows, test failures, risky regressions, stale docs, and mismatches between source and deployed copies.

Requirements:

- Use Desktop Commander for filesystem inspection, command execution, and local file analysis.
- When referencing files, always provide full absolute paths.
- Do not rely on partial paths such as `scripts/dashboard_server.py`; use full paths like `C:\dev\Desktop-Projects\llm_wiki_prompt_packet\llm_wiki_prompt_packet\scripts\dashboard_server.py`.
- Start by checking `git status --short --branch` so existing dirty files are visible.
- Do not revert, delete, or overwrite user changes.
- Run the most relevant test suite for the areas you inspect.
- If tests cannot be run, explain the blocker and the exact command that failed.
- Prioritize findings by severity and include concrete reproduction steps where possible.
- For every finding, include the full file path, line number when available, expected behavior, actual behavior, and suggested fix.
- If no issues are found, say that clearly and list any remaining QA gaps.

Suggested starting commands:

```powershell
git status --short --branch
python -m unittest discover -s tests
python -m py_compile scripts\dashboard_server.py support\scripts\dashboard_server.py
```

Deliver a concise QA report with:

1. Findings, ordered by severity.
2. Test results.
3. Risk areas not fully covered.
4. Recommended next fixes.
