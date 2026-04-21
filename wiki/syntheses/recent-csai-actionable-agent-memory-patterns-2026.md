# Recent cs.AI Actionable Agent Memory Patterns (2026)

## Goal

Capture implementation-relevant patterns from a recent `cs.AI` batch, with emphasis on memory architecture, controller design, delegation, and context efficiency.

## Most actionable papers from this pass

### 1. WorldDB

**Theme:** vector + graph memory with ontology-aware write-time reconciliation.

**Packet takeaway:**

- durable memory should not be append-only text by default
- writes should attempt reconciliation against existing objects
- structured memory beats long transcript replay

**Adaptation in this repo:**

- active skills now carry typed memory-object fields
- `canonical_keys` were added as lightweight write-time reconciliation handles
- merge/update behavior is now easier to drive explicitly instead of only relying on similarity

### 2. A Control Architecture for Training-Free Memory Use

**Theme:** explicit controller decides when to read/write memory; LLM remains mostly stateless.

**Packet takeaway:**

- prefer explicit memory operations over dumping all memory into prompts
- keep prompts lean and targeted
- use the controller/harness to decide when retrieval is necessary

**Adaptation in this repo:**

- packet guidance now emphasizes explicit READ / WRITE / UPDATE choices
- reducer packets and targeted retrieval are the default path for long work

### 3. Architectural Design Decisions in AI Agent Harnesses

**Theme:** harness-level decisions matter as much as model quality.

**Packet takeaway:**

- externalize state where possible
- be deliberate about memory topology and planning style
- capability-aware routing matters

**Adaptation in this repo:**

- wrapper skills now describe lighter capability-aware routing
- the packet contract makes memory layers clearer and more modular

### 4. LiteResearcher

**Theme:** research agents benefit from action-space discipline and cache reuse.

**Packet takeaway:**

- reuse compact summaries instead of re-reading long sources
- preserve intermediate state in artifacts, not only in prompt history

**Adaptation in this repo:**

- packet guidance now leans harder on stable summaries, briefs, packets, and artifact refs

### 5. CADMAS-CTX

**Theme:** contextual capability calibration for delegation.

**Packet takeaway:**

- use the smallest sufficient workflow/model for the subtask
- reserve expensive review passes for higher-risk decisions

**Adaptation in this repo:**

- packet-owned wrapper skills now emphasize minimal-sufficient routing plus stronger verification for risky steps

### 6. Stability Implies Redundancy / selective halting

**Theme:** long-context handling should exploit stable context instead of recomputing everything.

**Packet takeaway:**

- even when token count is not reduced, stable summaries and cached state reduce effective repeated context cost

**Adaptation in this repo:**

- updated guidance now explicitly prefers reusing stable summaries over replaying raw long histories

## Resulting design pattern for this repo

A simple memory-native harness pattern:

1. observe current task
2. controller decides whether the step needs retrieval, memory write, memory update, or no memory operation
3. read the smallest useful context slice
4. act
5. store only durable facts and provenance
6. reconcile with existing procedural memory via canonical keys when overlap exists

## Why this matters

Most practical token savings here come from:

- structured memory
- write-time reconciliation
- targeted retrieval
- summary reuse
- capability-aware routing

not from trying to compress every prompt after the fact.
