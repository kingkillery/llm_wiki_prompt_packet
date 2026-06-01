# pi-context-layer

`pi-context-layer` adds a context-worker layer to Pi. It watches prompts before the agent starts, detects large or external context references, summarizes them with cheap worker models, caches summaries by SHA-256 hash, and injects the result back into the turn.

Pi docs currently use these extension hooks:

- `before_agent_start` for the concept's `onBeforeRequest`
- `after_provider_response` for `onAfterResponse`
- `session_shutdown` for `onStop`

Project-local auto-discovery is `.pi/extensions/`, while global auto-discovery is `~/.pi/agent/extensions/`.

## Install

Project-local:

```bash
pi install -l ./.pi/extensions/pi-context-layer
```

Or run directly for a test session:

```bash
pi -e ./.pi/extensions/pi-context-layer
```

For npm distribution, publish this folder as `pi-context-layer`, then install it with:

```bash
pi install npm:pi-context-layer
```

## Configuration

Create `.pi/context-layer.json`:

```json
{
  "workerModel": "deepseek-v4-flash",
  "summarizerModel": "deepseek-v4-flash",
  "multimodalModel": "nemotron-3-nano-omni",
  "maxWorkerContext": 500000,
  "cacheEnabled": true,
  "cacheDir": ".pi/context-cache/",
  "vectorEnabled": false,
  "vectorProvider": "vertex-ai",
  "vectorIndexPath": ".pi/context-cache/vector-index.json",
  "vectorTopK": 4,
  "vectorMinSimilarity": 0.72,
  "vertexProjectId": "your-gcp-project-id",
  "vertexLocation": "us-central1",
  "vertexTextEmbeddingModel": "gemini-embedding-001",
  "vertexMultimodalEmbeddingModel": "multimodalembedding@001",
  "vertexEmbeddingDimensionality": 768
}
```

If a model is provider-scoped, use `provider/model-id`, for example `openrouter/deepseek-v4-flash`.

`vectorEnabled` is deliberately off by default. When enabled, the extension uses Vertex AI embeddings through `gcloud auth print-access-token`, stores vectors locally in `vectorIndexPath`, and retrieves related cached summaries before the worker path runs.

Authenticate locally with:

```bash
gcloud auth application-default login
gcloud auth login
gcloud config set project your-gcp-project-id
```

The extension resolves the project from `vertexProjectId`, `GOOGLE_CLOUD_PROJECT`, `GCLOUD_PROJECT`, or `CLOUDSDK_CORE_PROJECT`.

## Commands

- `/context-worker <file-or-directory-path>`: manually summarize a path or URL.
- `/context-refresh`: force re-summarize the last context target.
- `/context-status`: show manifest and cache state.
- `/context-clear`: clear this project's context manifest and cache.

Cache entries are JSON files under `.pi/context-cache/` with `{ hash, timestamp, model, token_count, summary }`. Entries expire after 7 days.

## Retrieval Order

```text
1. Exact references:
   file/path/URL/long output -> hash cache -> context worker if cache miss

2. Optional semantic recall:
   prompt -> Vertex embedding -> local vector index -> top-K cached summaries

3. Thinker injection:
   vector hits + fresh worker summaries -> [Context Layer] system context
```

The vector index stores compressed summaries, not raw repository files. That keeps lookup fast and avoids turning every prompt into a remote embedding/indexing pass.

## Research-Informed Choices

- Long-context training results favor broad downstream task evaluation over needle-only tests, so validate this extension on real coding tasks and long logs, not just synthetic retrieval.
- Context compression work points toward reusable segment summaries; this extension indexes compact summaries and reuses them across turns.
- Attention-guided compression work suggests salience marking before compression; the worker prompt preserves signatures, stack traces, config, and component relationships as the first salience policy.
- Efficient-attention and hybrid Mamba/Transformer model work supports using cheap long-context workers for ingestion while keeping the main thinker context lean.
