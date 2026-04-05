# temp-git-deployment

Paste this into Claude Code, Codex, Droid, Antigravity, or another terminal-capable coding agent when the packet is ready to publish.

```md
You are a release engineer and repository hardening operator.

Your job is to deploy this prompt packet to a clean git repository, verify there are no secrets or sensitive artifacts, and create a hosted auto-installer package that supports:

- macOS and Linux:
  - `curl -fsSL https://URL/install.sh | sh`
- Windows PowerShell:
  - `irm https://URL/install.ps1 | iex`

Assume this is an implementation task.
Do the work.
Only stop for authentication, irreversible publish steps, missing hosting credentials, DNS/CDN setup, or explicit human approval before making a public repo or release.

## Inputs

Use these variables and ask for them only if missing:
- `PACKET_PATH`: local path to the packet directory
- `REPO_NAME`: target git repository name
- `GIT_REMOTE_URL`: remote URL if already created
- `DEFAULT_BRANCH`: default `main`
- `HOST_BASE_URL`: final public base URL for hosted installers and release artifacts
- `PUBLISH_VISIBILITY`: `private` or `public`, default `private` until approved
- `FORCE_OVERWRITE`: default `false`

Infer safe defaults where possible.

## Primary goals

1. Review the packet for internal consistency.
2. Remove or block secrets, tokens, personal paths, or machine-specific debris.
3. Make the repository publishable.
4. Create a safe installer story:
   - `install.sh`
   - `install.ps1`
   - a downloadable release archive / zip
   - checksum file(s)
5. Make the published install commands stable and copy-pasteable.
6. Keep top-level agent guidance concise.

## Internal consistency review

Before publishing, verify that:
- `README.md` matches the actual file layout
- root prompts and installer paths agree
- script names match the documented commands
- the Obsidian bootstrap prompt matches the packet's actual installed file structure
- cross-agent names are consistent:
  - `AGENTS.md`
  - `CLAUDE.md`
  - `.claude/commands/...`
  - `.agents/skills/...`
  - `.agent/workflows/...`
- there are no references to files that do not exist
- there are no broken relative links inside markdown docs

If something is inconsistent, fix it before publishing and record the change.

## Security / privacy review

Scan the packet before git init or before pushing any new commit.

Look for:
- API keys
- bearer tokens
- SSH private keys
- `.env` files
- auth cookies
- machine-specific usernames or absolute home-directory paths
- internal-only hostnames or IPs
- accidental logs, caches, temporary files, editor swap files, `.DS_Store`, `Thumbs.db`
- secrets embedded in scripts, docs, examples, or shell history fragments

Use multiple checks, such as:
- filename-based scans
- regex-based scans
- gitignore review
- optional secret scanners if available

At minimum:
- add a strong `.gitignore`
- add a simple local secret scan script if useful
- refuse to publish until obvious sensitive material is removed or explicitly approved

## Repository structure to produce

Ensure the published repo has a coherent structure similar to:

- `README.md`
- `LICENSE` if missing and user approves
- `.gitignore`
- `prompts/`
- `installers/`
- `obsidian_universal_bootstrap_prompt.md`
- `temp-git-deployment.md`
- `install.sh`
- `install.ps1`
- optional `checksums.txt`
- optional `scripts/secret_scan.py`

Do not add unnecessary framework noise.

## Installer packaging requirements

Create a publishable wrapper installer pair:

### `install.sh`
It should:
- run on macOS and Linux
- download or access the packet archive from `HOST_BASE_URL`
- unpack to a temporary directory
- invoke the packet's Python installer or shell wrapper
- pass through user arguments such as:
  - `--vault`
  - `--targets`
  - `--force`
- fail fast with clear error messages
- clean up temp files
- avoid unsafe shell tricks beyond the intended pipe-to-sh entrypoint

### `install.ps1`
It should:
- support Windows PowerShell
- download the same release artifact from `HOST_BASE_URL`
- unpack to a temporary directory
- invoke the installer in a Windows-safe way
- pass through equivalent arguments
- emit clear status and error messages

### Release artifact
Publish a versioned archive such as:
- `llm_wiki_prompt_packet-vX.Y.Z.zip`

Prefer stable versioned URLs rather than mutable ad-hoc paths.

## Hosting requirements

Use one of these hosting patterns, whichever is available and safest:

1. GitHub release assets
2. Raw GitHub content from a version tag
3. S3 / R2 / similar object storage with a stable HTTPS URL
4. Another static host with versioned artifacts

Prefer URLs that can support commands like:

- macOS/Linux:
  - `curl -fsSL https://HOST_BASE_URL/install.sh | sh -s -- --vault "/path/to/Vault"`
- Windows PowerShell:
  - `irm https://HOST_BASE_URL/install.ps1 | iex`

If `HOST_BASE_URL` is not yet available:
- prepare the repo
- generate the scripts with placeholders
- document exactly what URL must be substituted before release

## Git / release workflow

Do this in order:

1. Review and fix the packet
2. Add `.gitignore`
3. Run secret / sensitivity scan
4. Initialize git repo if needed
5. Stage only safe files
6. Create a clean initial commit
7. Add or verify remote
8. Push to the requested visibility only after approval if needed
9. Create a version tag
10. Build release archive
11. Upload release assets or otherwise publish them
12. Verify the hosted installer URLs
13. Test install commands in dry-run mode where possible

## `.gitignore` minimum expectations

Include common exclusions for:
- `.env*`
- OS junk
- editor temp files
- Python caches
- Node modules
- local virtualenvs
- logs
- release staging temp dirs
- personal notes not meant for publishing, if applicable

## Validation steps

Before declaring success:
1. verify no obvious secrets remain
2. verify every documented file exists
3. verify `install.sh` and `install.ps1` reference the correct versioned artifact URL
4. verify the packet archive contains the expected files
5. verify the local installer still works:
   - dry-run
   - sample target subset
6. verify README install commands match the published URLs exactly

## Required final report format

Return exactly these sections:

### Packet review
- issues found
- fixes made
- remaining caveats

### Security review
- scans run
- findings
- actions taken

### Repository status
- local repo status
- remote status
- release/tag status

### Published install commands
- macOS/Linux command
- Windows PowerShell command

### Files added or changed
- one bullet per file

### Manual actions still required
- one bullet per action

### Notes
- brief caveats only

## Safety rules

- Do not publish secrets.
- Do not make a public release until sensitive-content review is clean and visibility is approved.
- Prefer versioned release URLs over mutable branch URLs.
- Keep `AGENTS.md` and `CLAUDE.md` concise.
- Do not silently delete user-authored material outside the packet.

Begin now.
```
