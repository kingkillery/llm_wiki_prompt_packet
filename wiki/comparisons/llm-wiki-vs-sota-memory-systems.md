# LLM Wiki Memory Packet vs. State-of-the-Art Memory Systems

> **Scope:** Compare the `llm-wiki-memory` stack against the leading LLM/agent memory architectures as of early 2026. Draw concrete insights for where the packet should double down, where it should borrow, and where the literature validates existing design choices.
> **Date:** 2026-04-22
> **Sources:** Packet docs (`LLM_WIKI_MEMORY.md`, `SYSTEM_CONTRACT.md`, `SKILL_CREATION_AT_EXPERT_LEVEL.md`), prior syntheses (`agentic-memory-skill-stack-upgrade-2026`, `recent-csai-actionable-agent-memory-patterns-2026`), and public documentation for Mem0, Zep, LangChain Memory, LlamaIndex Chat Engine, MemGPT/Letta, CrewAI Memory, Claude native memory, and OpenAI memory.

---

## Executive Insights

1. **The packet is one of the few systems that treats procedural memory as a first-class citizen.** Most SOTA systems optimize for *conversation recall* (episodic) and *fact retrieval* (semantic). The packet's skill lifecycle—capture, validate, merge, retire—is closer to an expert system's rule base than to a chatbot memory layer.

2. **The write-path discipline is a differentiator, but also a friction point.** Mem0 and Zep auto-ingest conversation turns. The packet requires explicit curation (`brv curate`, skill pipeline validation, reducer packets). This yields higher signal-to-noise but demands more from the agent harness. The literature (WorldDB, CADMAS-CTX) supports this tradeoff: structured write-time reconciliation beats append-only dumping.

3. **The multi-plane retrieval architecture (qmd + GitVizz + brv) is ahead of most single-store systems.** LangChain and LlamaIndex default to one vector store. The packet's routing table—qmd for evidence, GitVizz for topology, brv for preferences—mirrors the "capability-aware routing" pattern from the 2026 cs.AI batch.

4. **Local-first markdown is a governance advantage, not just a privacy feature.** Human-legible memory stores enable audit, edit, and rollback in ways that opaque vector indices (Mem0, Zep, OpenAI memory) do not. This aligns with the "knowledge objects" literature and with regulatory expectations for high-stakes agentic systems.

5. **The biggest gap is automatic episodic capture.** The packet relies on reducer packets and failure hooks. Mem0, Zep, and Claude native memory automatically embed and index conversation history. The packet lacks a transparent "memory layer" API that auto-curates without explicit agent cooperation.

6. **No built-in user-facing chat surface.** Most SOTA memory systems (Claude, OpenAI, Mem0, Letta) assume a conversational UI where memory is surfaced to the end user for editing. The packet is agent-facing. This is a scope choice, but it limits adoption for non-technical users.

---

## Comparative Matrix

| Dimension | LLM Wiki Packet | Mem0 | Zep | LangChain Memory | LlamaIndex Chat | MemGPT/Letta | Claude Native | OpenAI Memory |
|---|---|---|---|---|---|---|---|---|
| **Memory taxonomy** | 5 layers (working, episodic, semantic, procedural, preference) | Episodic + semantic; entity extraction | Episodic + semantic; session summaries | Buffer, window, vector, summary | Context + condense + retrieval | Virtual context (OS paging) | Project memory + user memory | Per-user facts |
| **Procedural memory** | **First-class skill lifecycle** | None native | None native | Tool descriptions only | None native | Agent config, not reusable skills | None | None |
| **Write path** | Explicit curation (ACE loop) | Auto-ingest + LLM extraction | Auto-ingest + manual edit | Manual or callback | Manual or callback | Auto memory pressure paging | Auto + manual edit | Auto + manual edit |
| **Read path** | Hybrid: qmd (lex/vec), GitVizz (graph), brv (curated) | Vector + keyword | Vector + session graph | Vector or buffer | Vector + node traversal | Hierarchical context paging | Project memory injection | Memory injection |
| **Local-first** | **Yes** (markdown, local qmd, optional local TEI) | Cloud-first; local mode experimental | Cloud-first; open-source backend | Optional (depends on store) | Optional (depends on store) | Open-source; typically self-hosted | No | No |
| **Human legibility** | **Full** (markdown pages) | Partial (dashboard) | Partial (dashboard) | Low (vector chunks) | Low (vector chunks) | Low (virtual context blocks) | Partial (memory UI) | Partial (settings UI) |
| **Conflict resolution** | **Explicit policy** (source evidence wins) | Implicit (latest write) | Implicit (latest write) | None | None | Memory pressure eviction | Manual edit only | Manual edit only |
| **Failure learning** | **Failure capture + cluster promotion** | None native | None native | None native | None native | None native | None native | None native |
| **Agent integration** | MCP + harness skills (Kade-HQ, gstack) | Python/JS SDK, framework adapters | Python/JS SDK, framework adapters | Native LangChain | Native LlamaIndex | Python client | Native Claude | Native OpenAI |
| **Skill evolution** | **Frontier-based + surrogate review** | None | None | None | None | None | None | None |
| **Update strategy** | Merge, replace-on-validation, deprecate-on-conflict | Append-only | Append + version | Overwrite or append | Overwrite or append | Paging/eviction | Replace | Replace |
| **Setup complexity** | High (multi-tool, MCP, vault) | Low (pip install + API key) | Medium (cloud or docker) | Low-Medium | Low-Medium | Medium | None (built-in) | None (built-in) |

---

## Deep Dives

### 1. Memory Taxonomy & Ontology

**SOTA consensus (2025-2026):** The literature increasingly distinguishes working, episodic, semantic, and procedural memory. Titans/MIRAS, WorldDB, and the Agent-Native Memory paper all argue that flat "context + RAG" is insufficient for long-horizon agents.

**Packet position:** The packet's five-layer model (working, episodic, semantic, procedural, preference) is one of the most granular in production-oriented open-source systems. Only MemGPT/Letta's OS-inspired paging comes close, but Lettafolds procedural memory into "agent configuration" rather than reusable skills.

**Insight:** The packet should publish its taxonomy as a standalone spec. It is a genuine architectural contribution that most SDKs lack.

**Gap:** The packet does not yet have an automated classifier that tags incoming memory into the correct layer. Mem0 and Zep use LLM-based classifiers (entity extraction, fact vs preference). The packet relies on the agent harness to route correctly.

### 2. Write Path & Curation

**SOTA consensus:** Auto-ingest is the default. Mem0 extracts facts from every user message. Zep summarizes sessions automatically. Claude and OpenAI observe and memorize without explicit user action.

**Packet position:** The packet uses an ACE-style loop (generation → reflection → validation → curation). Reducer packets, skill pipelines, and `brv curate` are all explicit write gates. This mirrors the "control architecture for training-free memory use" paper: a controller decides when to write, rather than treating memory as a passive log.

**Insight:** The packet's explicit write path is *correct* for high-autonomy agents where garbage memory compounds into bad decisions. It is *overkill* for simple chatbots. The installer should eventually offer a "chat mode" (auto-ingest into episodic) and an "agent mode" (explicit curation).

**Gap:** The packet has no "memory suggestion" UI. Claude and OpenAI show the user what was remembered and let them delete it. The packet's markdown store is editable, but there is no runtime notification that something *was* captured.

### 3. Read Path & Retrieval

**SOTA consensus:** Single-vector-store retrieval dominates. Mem0, Zep, LangChain VectorStoreRetrieverMemory, and LlamaIndex's context chat engine all default to embedding search over chunked conversation history.

**Packet position:** The packet routes across three planes:
- `pk-qmd` (BM25 + vector + LLM rerank) for evidence
- `GitVizz` (repo graph, API topology) for structure
- `brv` (curated context tree) for preferences

This is the most sophisticated retrieval architecture in the comparison set. It matches the "adaptive retrieval routing" skill in `pk-skills1` and the capability-aware routing pattern from CADMAS-CTX.

**Insight:** The packet should measure retrieval quality per-plane and publish a benchmark. Most users of single-store systems do not realize they are missing structural/graph retrieval until they hit a topology-heavy task.

**Gap:** No unified query planner. The user (or agent) must decide which plane to query first. A learned router—trained on which plane succeeded for past tasks—would close this gap.

### 4. Skill / Procedural Memory

**SOTA consensus:** No major memory SDK treats reusable task recipes as a native memory type. LangChain has "tool descriptions," CrewAI has "crew memory" (short-term + long-term + entity), but neither captures "how to do X" as a durable, versioned, retrievable object.

**Packet position:** The skill pipeline (`skill_reflect`, `skill_validate`, `skill_pipeline_run`, `skill_evolve`, `skill_retire`) is the packet's most unique feature. Active skills are typed memory objects with scope, strategy, durable facts, and provenance. The retirement threshold (`retire_below_score: -3`) and frontier-based evolution are closer to software engineering (code review + deprecation) than to chatbot memory.

**Insight:** This is the packet's strongest moat. It should be extracted into a standalone spec or SDK ("procedural memory for agents") and compared directly against emerging standards like MCP tools + prompts.

**Gap:** Skill discovery is still search-based. There is no "skill recommendation" that triggers automatically when a task shape matches a known skill. A lightweight trigger classifier (rule-based or embedding similarity against task descriptions) would make procedural memory feel ambient rather than opt-in.

### 5. Agent Integration

**SOTA consensus:** Native integration wins for adoption. Claude memory works because it is built in. Mem0 and Zep win because they have one-line `mem0.add()` / `zep.memory.add()` calls. LangChain memory is native to LangChain chains.

**Packet position:** The packet integrates via MCP servers (`pk-qmd`, `llm-wiki-skills`, `obsidian`, `brv`) and harness skills (`kade-hq`, `gstack`, `g-kade`). This is powerful but requires the agent to support MCP and to read guide files before acting.

**Insight:** The packet's MCP-first approach is architecturally clean and framework-agnostic. However, it creates a "cold start" problem: the agent must know to read `AGENTS.md` and `LLM_WIKI_MEMORY.md` before it can use the memory stack effectively. A bootstrap shim (auto-injected into the first prompt) would reduce this friction.

### 6. Local-First vs. Cloud-Native

**SOTA consensus:** Almost everything is cloud-native. OpenAI and Claude memory are fully hosted. Mem0 and Zep are primarily SaaS with open-source clients. Even Letta, which is self-hosted, typically runs on a remote server.

**Packet position:** The packet is designed for local markdown, local qmd, optional local TEI embeddings, and local GitVizz. BRV is the only cloud dependency, and it is explicitly optional (skip gracefully).

**Insight:** Local-first is a genuine differentiator for privacy-sensitive and air-gapped use cases. It also enables human audit in ways that cloud vector stores do not. However, it limits multi-device sync and real-time collaboration. A future "hybrid mode" (local working + encrypted cloud backup for preference memory) would capture the best of both.

### 7. Human Legibility & Governance

**SOTA consensus:** Opaque. Vector stores, embedding indices, and LLM-curated memory summaries are not directly human-editable. Users interact through dashboards that show simplified views.

**Packet position:** Markdown is the store. Every memory object is a file. Links, backlinks, and Obsidian-native editing are first-class.

**Insight:** This is a governance superpower. For SOX, HIPAA, or EU AI Act compliance, the ability to audit, version, and redact memory at the file level is essential. The packet should market this explicitly to enterprise users.

**Gap:** Markdown legibility trades off against query precision. A 10-page skill markdown is human-readable but may not retrieve as precisely as a chunked, embedding-indexed fact. The packet's `pk-qmd` hybrid search mitigates this, but there is no automatic "chunking + embedding of wiki pages" today (the TEI path is manual).

### 8. Failure Learning

**SOTA consensus:** No mainstream memory system learns from failures. Mem0, Zep, Claude, and OpenAI memorize what the user *said*, not what the agent *did wrong*.

**Packet position:** The failure capture pipeline (`scripts/llm_wiki_agent_failure_capture.py`, failure clusters, promotion thresholds) is unique. It treats failed trajectories as first-class evidence for skill evolution.

**Insight:** This is the packet's second-strongest moat after procedural memory. Failure-driven improvement is the core of the `agent-self-improvement-harness` skill. The packet should run a public benchmark showing that failure-captured agents improve over time versus static memory.

---

## Where the Packet Leads

| Capability | Packet advantage | Evidence |
|---|---|---|
| **Procedural memory as typed objects** | Unique among compared systems | `SKILL_CREATION_AT_EXPERT_LEVEL.md`, skill pipeline |
| **Multi-plane retrieval** | qmd + GitVizz + brv routing | `SYSTEM_CONTRACT.md`, `LLM_WIKI_MEMORY.md` |
| **Explicit write-path curation** | ACE loop, reducer packets, validation gates | `agentic-memory-skill-stack-upgrade-2026.md` |
| **Failure-driven evolution** | Failure capture → cluster → promotion | `.llm-wiki/config.json` pipeline settings |
| **Human-legible governance** | Markdown store, Obsidian integration, git versioning | `AGENTS.md`, `wiki/` structure |
| **Local-first bootstrap** | No cloud required for core stack | `install.sh`, Docker compose |
| **Conflict resolution policy** | Source evidence wins over stale memory | `LLM_WIKI_MEMORY.md` routing rules |

## Where the Packet Trails

| Capability | Gap | Mitigation / experiment |
|---|---|---|
| **Automatic episodic capture** | No transparent conversation indexing | Experiment: auto-reducer packet generation from session transcripts |
| **User-facing memory UI** | No chat-native memory editing surface | Out of scope for agent-facing packet; could partner with Chainlit/Streamlit harness |
| **Unified query planner** | Agent must choose retrieval plane | Experiment: learned router or heuristic auto-ranker |
| **Ambient skill triggering** | Skills are searched, not suggested | Experiment: task-shape classifier against skill index |
| **Cloud sync / multi-device** | Local markdown does not sync | Future: optional encrypted cloud mirror for brv + preference layer |
| **Embedding automation** | TEI integration is manual | Future: auto-embed wiki pages on change; wire into qmd `vec` mode by default |
| **Setup simplicity** | High friction vs. pip-install competitors | Continue improving installer; consider hosted onboarding |

---

## Strategic Recommendations

1. **Publish the memory taxonomy as a spec.** The five-layer model with promotion flow is a genuine contribution. A short paper or RFC comparing it to MemGPT's paging and WorldDB's ontology would raise visibility.

2. **Run a head-to-head benchmark.** Use the Pokemon benchmark surface or `cua_world` to compare packet-equipped agents vs. Mem0-equipped agents on long-horizon tasks that require skill reuse. Measure:
   - Task completion rate
   - Number of exploration steps on repetition
   - Memory store growth rate (signal vs. noise)

3. **Experiment with auto-reducer packets.** The biggest usability gap is episodic capture. A lightweight script that summarizes the last N tool calls into a draft reducer packet (pending validation) would close this without abandoning curation discipline.

4. **Build a skill trigger classifier.** When the agent receives a task, compute similarity against the skill index. If a skill matches above a threshold, suggest it proactively. This makes procedural memory feel like IntelliSense rather than a library search.

5. **Keep local-first as a flagship feature, but add hybrid mode.** Enterprises will ask for backup, sync, and team sharing. An encrypted cloud bridge for `brv` and the skill registry—leaving wiki pages local—would satisfy this without compromising governance.

---

## References

- Packet docs: `LLM_WIKI_MEMORY.md`, `SYSTEM_CONTRACT.md`, `SKILL_CREATION_AT_EXPERT_LEVEL.md`
- Prior syntheses: `wiki/syntheses/agentic-memory-skill-stack-upgrade-2026.md`, `wiki/syntheses/recent-csai-actionable-agent-memory-patterns-2026.md`
- External systems (docs reviewed): Mem0 (mem0.ai), Zep (getzep.com), LangChain Memory (python.langchain.com), LlamaIndex Chat Engine (docs.llamaindex.ai), Letta (letta.com), Claude project memory (anthropic.com), OpenAI memory (openai.com)
- Literature: WorldDB (2026), Agent-Native Memory Through LLM-Curated Hierarchical Context (2026), Knowledge Objects for Persistent LLM Memory (2026), A Control Architecture for Training-Free Memory Use (2026)
