# Testing Patterns

**Analysis Date:** 2026-04-12

## Test Framework

**Runner:**

- Python `unittest` - Used by `tests/test_install_obsidian_agent_memory.py`, `tests/test_install_g_kade_workspace.py`, and `tests/test_llm_wiki_skill_mcp.py`
- Node built-in `node:test` - Used by `tests/test_agent_api_gateway.mjs`

**Assertion Library:**

- `unittest.TestCase` assertions and `unittest.mock` in the Python tests
- `node:assert/strict` in the Node gateway test

**Run Commands:**

```bash
python -m unittest discover -s tests -p "test_*.py"   # Run Python tests
python tests/test_install_g_kade_workspace.py          # Run one Python module directly
node --test tests/test_agent_api_gateway.mjs           # Run the Node gateway test
```

## Test File Organization

**Location:**

- Separate `tests/` tree for all tracked tests
- No co-located tests in the implementation directories

**Naming:**

- Python: `test_*.py`
- Node: `test_*.mjs`

**Structure:**

```text
tests/
  test_install_obsidian_agent_memory.py
  test_install_g_kade_workspace.py
  test_llm_wiki_skill_mcp.py
  test_agent_api_gateway.mjs
```

## Test Structure

**Suite Organization:**

```python
class InstallerHomeSkillTests(unittest.TestCase):
    def setUp(self) -> None:
        ...

    def tearDown(self) -> None:
        ...

    def test_install_home_skills_copies_packet_owned_skill_payloads(self) -> None:
        ...
```

```javascript
test("gateway proxies /mcp, /graph, and memory routes without auth in local mode", async (t) => {
  ...
});
```

**Patterns:**

- Python tests use temporary directories and real filesystem effects instead of heavy mocking
- Node tests spin up real local HTTP servers and child processes to exercise the gateway end to end
- Focus is behavioral: verify outputs, generated files, and route behavior rather than internal implementation details

## Mocking

**Framework:**

- Python uses `unittest.mock` selectively, for example around environment flags or missing HUMAN profile sources
- Node test code avoids full mocks and instead creates in-process HTTP servers and temporary scripts

**Patterns:**

```python
with mock.patch.dict(os.environ, {}, clear=False):
    ...
```

```javascript
const gateway = await startGateway({
  listenPort: gatewayPort,
  qmdPort,
  token: "secret-token",
});
```

**What to Mock:**

- Environment variables and edge-case dependencies
- Temporary filesystems and subprocess inputs

**What NOT to Mock:**

- File writes produced by installers
- HTTP proxy behavior in the gateway path

## Fixtures and Factories

**Test Data:**

- Python tests use helper loaders and temporary workspaces, for example `load_module()` and `tempfile.TemporaryDirectory()`
- `tests/test_llm_wiki_skill_mcp.py` uses a reusable `base_payload()` factory for skill-pipeline scenarios

**Location:**

- Inline helper functions inside each test module
- No shared `tests/fixtures/` directory is tracked

## Coverage

**Requirements:**

- No explicit line or branch coverage target is tracked
- No coverage configuration files are present

**Configuration:**

- No `coverage.py`, `pytest-cov`, `nyc`, or similar config is tracked
- The only GitHub Actions workflow in `.github/workflows/release-installers.yml` validates release assets but does not run the full test suite

## Test Types

**Unit / behavior tests:**

- Installer safety and ownership checks in `tests/test_install_obsidian_agent_memory.py`
- Workspace-root detection and KADE overlay scaffolding in `tests/test_install_g_kade_workspace.py`
- Skill-pipeline reducer/router logic in `tests/test_llm_wiki_skill_mcp.py`

**Integration tests:**

- Gateway proxying and auth behavior in `tests/test_agent_api_gateway.mjs`

**E2E Tests:**

- Not detected for hosted deploy flows, plugin packaging, or shell/PowerShell wrappers

## Common Patterns

**Async Testing:**

```javascript
const response = await fetch(`http://127.0.0.1:${gatewayPort}/mcp`, {
  method: "POST",
});
assert.equal(response.status, 200);
```

**Error Testing:**

```python
with self.assertRaises(SystemExit):
    self.module.ensure_safe_install_root(self.home_root, self.home_root, allow_home_root=False)
```

**Snapshot Testing:**

- Not used in the tracked test suite

---

_Testing analysis: 2026-04-12_
_Update when test runners, commands, or CI coverage change_
