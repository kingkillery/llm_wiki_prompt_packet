# QuickScope²: Memory Retrieval Improvements

> **Goal:** Close the two verified retrieval gaps versus SOTA (recency decay + graph traversal) with the minimum surface area and zero breaking changes.
> **Date:** 2026-04-22
> **ETA:** 2–3 hours for Gap 1, 1–2 days for Gap 2.

---

## Gap 1: Recency-Weighted Retrieval

**Problem:** `skill_trigger.py` ranks skills by static similarity. A stale skill from 6 months ago can outrank a freshly-validated one.

**Fastest A→B path:**

### Step 1: Add decay math to `skill_index.py` (10 min)
```python
def _recency_multiplier(updated_at: str, halflife_days: float = 30.0) -> float:
    if not updated_at:
        return 1.0
    try:
        dt = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
        age_days = (datetime.now(timezone.utc) - dt).total_seconds() / 86400.0
        return 0.5 + 0.5 * math.exp(-age_days / halflife_days)
    except Exception:
        return 1.0
```

### Step 2: Apply decay in `SkillIndex.score()` (5 min)
```python
recency = _recency_multiplier(skill.updated_at, halflife_days=30.0)
score = (keyword_weight * keyword_scores.get(skill.id, 0.0) + embed_weight * embedding_scores.get(skill.id, 0.0)) * recency
```

### Step 3: Expose halflife in config (5 min)
Add `"halflife_days": 30.0` to `.llm-wiki/config.json` → `skills.index`.
Read it in `suggest_skills()` with fallback to 30.

### Step 4: Add test (10 min)
`test_skill_trigger.py`: create two skills with identical text but different `updated_at`. Assert the newer one ranks higher.

**Surface touched:** `skill_index.py`, `.llm-wiki/config.json`, `tests/test_skill_trigger.py`
**Breaking changes:** None.

---

## Gap 2: Multi-Hop Skill Graph Traversal

**Problem:** Skills are isolated nodes. The classifier returns flat similarity matches. There is no exploitation of prerequisite / successor / conflict relationships.

**Fastest A→B path:**

### Step 1: Extend skill schema (20 min)
In `skill_index.py` → `Skill` dataclass, add:
```python
related_skills: list[dict] = field(default_factory=list)
```

In `discover_skills()`, parse `related_skills` from frontmatter:
```yaml
---
skill_id: skill-git-rebase
related_skills:
  - id: skill-git-resolve-conflict
    relation: prerequisite
  - id: skill-git-force-push-recovery
    relation: conflict
---
```

### Step 2: Build edge index in `SkillIndex` (20 min)
Add:
```python
edges: dict[str, list[dict]] = field(default_factory=dict)  # skill_id -> [{target_id, relation}]
```
Populate in `build_index()` from `skill.related_skills`.
Serialize/deserialize in `save()` / `load()`.

### Step 3: Add `_graph_neighbors()` (20 min)
```python
def _graph_neighbors(skill_id: str, edges: dict, skills_by_id: dict, max_per_relation: int = 2) -> list[dict]:
    neighbors = []
    for edge in edges.get(skill_id, []):
        target = skills_by_id.get(edge["target_id"])
        if target:
            neighbors.append({"id": target.id, "title": target.title, "relation": edge["relation"]})
    # Deduplicate and cap per relation
    ...
    return neighbors
```

### Step 4: Emit neighborhood in `format_suggestions()` (15 min)
```
Skill suggestions:
  * Git rebase workflow (score 0.91) -- skill-git-rebase
    Fast path: git rebase main
    Neighborhood:
      - prerequisite: Resolve merge conflicts (skill-git-resolve-conflict)
      - conflict: Force-push recovery (skill-git-force-push-recovery)
```

### Step 5: Update `skills-registry.json` writer (10 min)
In `llm_wiki_skill_mcp.py` or wherever skills are promoted, ensure `related_skills` is preserved when writing the registry.

### Step 6: Add test (20 min)
`test_skill_trigger.py`: create three skills with edges. Query a task that matches skill A; assert the suggestion includes skill B (prerequisite) and skill C (conflict).

**Surface touched:** `skill_index.py`, `skill_trigger.py`, `skills-registry.json` writer, tests
**Breaking changes:** None (new optional field).

---

## Execution order (fastest path)

| Order | Task | Time | Unblocks |
|---|---|---|---|
| 1 | Recency decay math + config | 20 min | Immediate retrieval quality gain |
| 2 | Recency decay test + deploy | 10 min | Validation |
| 3 | Skill schema extension (`related_skills`) | 20 min | Schema foundation |
| 4 | Edge index build/load/save | 20 min | Graph persistence |
| 5 | `_graph_neighbors()` + formatter | 35 min | User-facing feature |
| 6 | Graph traversal test + deploy | 20 min | Validation |

**Total hands-on time:** ~2 hours for Gap 1, ~2 hours for Gap 2.

---

## Anti-goals

- Do NOT build a full graph database (Neo4j, etc.). Edges live in the existing JSON index.
- Do NOT require every skill to have edges. Optional field; graceful degradation.
- Do NOT change the MCP tool interface yet. These are internal index improvements.
- Do NOT auto-populate edges with LLM calls. Edges are human-curated or explicitly added during skill authoring.

---

## Acceptance criteria

- [ ] Two skills with identical text but `updated_at` 90 days apart: newer ranks higher.
- [ ] Three skills with prerequisite/conflict edges: querying the parent returns neighbors.
- [ ] Zero changes required to existing skills (both features are opt-in via frontmatter/config).
- [ ] All existing tests pass.
