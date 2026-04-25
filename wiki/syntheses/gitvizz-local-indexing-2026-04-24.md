# GitVizz Local Indexing Fix (2026-04-24)

## Summary

GitVizz's unauthenticated ZIP generation endpoints are useful for one-shot graph, text, and structure extraction, but they do not create authenticated indexed-repository Mongo records. That leaves `repo_id` blank and prevents normal reuse through GitVizz's indexed repository surfaces.

The durable fix is a local trusted ingest endpoint in the sibling GitVizz checkout:

- Endpoint: `POST /api/local/index-repo`
- Enable flag: `LOCAL_TRUSTED_INGEST=1`
- Optional protection: `LOCAL_TRUSTED_INGEST_TOKEN` matched by `X-Local-Ingest-Token`
- Service user: `local-trusted-ingest`
- Stable repo key format: `local/{repo_name}/{branch}`

## Validation

The packet was indexed through the new persistent path from Docker GitVizz on `2026-04-24`.

- `repo_id`: `69ec012a9f5293551a7d3dd3`
- `repo_name`: `local/llm_wiki_prompt_packet/working-tree-final`
- `branch`: `working-tree-final`
- `text_chars`: `2544167`
- `structure_files`: `330`
- `graph_nodes`: `2230`
- `graph_edges`: `10294`

Mongo verification found the repository document in `gitvizz.repositories` and the service user in `gitvizz.users`.

Storage verification found all expected files under the GitVizz storage mount:

- `repository.zip`
- `content.txt`
- `data.json`
- `documentation/`

## Repeatable Packet Helper

The packet now includes a local helper:

- `scripts/gitvizz_local_ingest.ps1`
- `support/scripts/gitvizz_local_ingest.ps1`

Example:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\gitvizz_local_ingest.ps1 -RepoName llm_wiki_prompt_packet -Branch working-tree-helper
```

The helper writes its ZIP and response to `.tmp/gitvizz-ingest/`, excludes dependency/runtime folders during traversal, and returns the durable `repo_id` plus content/structure/graph counts.

## Notes

- Direct file I/O was used for this wiki update because Obsidian MCP availability was not confirmed during the Docker/GitVizz validation run.
- Raw source material under `raw/` was not modified.
- The GitVizz checkout had a pre-existing unrelated change in `backend/utils/db.py`; it was left untouched.
