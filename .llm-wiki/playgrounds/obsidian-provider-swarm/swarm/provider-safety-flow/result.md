# Provider Safety Flow Result

## Commands

- Wrote workspace-local `.llm-wiki/config.json` with `wiki_layer.vault_path = "."`.
- Ran `llm_wiki_provider.py write wiki/syntheses/Safety.md --content "Provider writes inside vault."`.
- Ran `llm_wiki_provider.py search "inside vault" --limit 3`.
- Ran attempted traversal write: `llm_wiki_provider.py write ..\outside.md --content "should fail"`.

## Observations

- Inside-vault write succeeded with `direct-file` and created `wiki/syntheses/Safety.md`.
- Search found `wiki/syntheses/Safety.md`.
- Path traversal was rejected with `WikiProviderError: Wiki path escapes vault: ..\outside.md`.

## Result

PASS. The direct-file provider allows normal user-like wiki writes and blocks writes outside the configured vault.
