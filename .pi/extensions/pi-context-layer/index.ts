import { createHash } from "node:crypto";
import { execFile } from "node:child_process";
import * as fs from "node:fs/promises";
import * as path from "node:path";
import { promisify } from "node:util";
import {
  createAgentSession,
  DefaultResourceLoader,
  SessionManager,
  type ExtensionAPI,
  type ExtensionContext,
} from "@earendil-works/pi-coding-agent";

export interface ContextLayerConfig {
  workerModel: string;
  summarizerModel: string;
  multimodalModel: string;
  maxWorkerContext: number;
  cacheEnabled: boolean;
  cacheDir: string;
  vectorEnabled: boolean;
  vectorProvider: "vertex-ai";
  vectorIndexPath: string;
  vectorTopK: number;
  vectorMinSimilarity: number;
  vertexProjectId?: string;
  vertexLocation: string;
  vertexTextEmbeddingModel: string;
  vertexMultimodalEmbeddingModel: string;
  vertexEmbeddingDimensionality?: number;
}

type ContextKind = "file" | "directory" | "inline" | "url" | "multimodal";

interface ContextItem {
  kind: ContextKind;
  label: string;
  content: string;
  model: string;
  tokenCount: number;
  mediaPath?: string;
  mediaType?: string;
}

interface CacheEntry {
  hash: string;
  timestamp: string;
  model: string;
  token_count: number;
  summary: string;
}

interface ContextManifest {
  files_summarized: string[];
  tokens_saved: number;
  workers_spawned: number;
  cache_hits: number;
  cache_misses: number;
  vector_queries: number;
  vector_hits: number;
  vector_updates: number;
  last_target?: string;
}

interface VectorEntry {
  id: string;
  hash: string;
  label: string;
  kind: ContextKind;
  model: string;
  timestamp: string;
  embeddingModel: string;
  embedding: number[];
  summary: string;
  token_count: number;
}

interface VectorIndex {
  version: 1;
  provider: "vertex-ai";
  entries: VectorEntry[];
}

const DEFAULT_CONFIG: ContextLayerConfig = {
  workerModel: "deepseek-v4-flash",
  summarizerModel: "deepseek-v4-flash",
  multimodalModel: "nemotron-3-nano-omni",
  maxWorkerContext: 500000,
  cacheEnabled: true,
  cacheDir: ".pi/context-cache/",
  vectorEnabled: false,
  vectorProvider: "vertex-ai",
  vectorIndexPath: ".pi/context-cache/vector-index.json",
  vectorTopK: 4,
  vectorMinSimilarity: 0.72,
  vertexLocation: "us-central1",
  vertexTextEmbeddingModel: "gemini-embedding-001",
  vertexMultimodalEmbeddingModel: "multimodalembedding@001",
};

const CACHE_TTL_MS = 7 * 24 * 60 * 60 * 1000;
const LONG_PROMPT_TOKEN_THRESHOLD = 8000;
const WORKER_CONCURRENCY = 3;
const TEXT_EXTENSIONS = new Set([
  ".c",
  ".cc",
  ".conf",
  ".cpp",
  ".cs",
  ".css",
  ".csv",
  ".go",
  ".h",
  ".html",
  ".java",
  ".js",
  ".json",
  ".jsonc",
  ".jsx",
  ".log",
  ".md",
  ".mjs",
  ".py",
  ".rs",
  ".sh",
  ".sql",
  ".toml",
  ".ts",
  ".tsx",
  ".txt",
  ".xml",
  ".yaml",
  ".yml",
]);
const MULTIMODAL_EXTENSIONS = new Set([
  ".gif",
  ".jpeg",
  ".jpg",
  ".m4a",
  ".mp3",
  ".mp4",
  ".png",
  ".wav",
  ".webm",
]);
const SKIP_DIRS = new Set([
  ".git",
  ".hg",
  ".pi/context-cache",
  "dist",
  "node_modules",
  "target",
  "__pycache__",
]);

let workerDepth = 0;

function estimateTokens(text: string): number {
  return Math.ceil(text.length / 4);
}

function hashContent(content: string): string {
  return createHash("sha256").update(content).digest("hex");
}

function defaultManifest(): ContextManifest {
  return {
    files_summarized: [],
    tokens_saved: 0,
    workers_spawned: 0,
    cache_hits: 0,
    cache_misses: 0,
    vector_queries: 0,
    vector_hits: 0,
    vector_updates: 0,
  };
}

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" ? (value as Record<string, unknown>) : {};
}

async function exists(target: string): Promise<boolean> {
  try {
    await fs.access(target);
    return true;
  } catch {
    return false;
  }
}

async function readJson<T>(target: string, fallback: T): Promise<T> {
  try {
    return JSON.parse(await fs.readFile(target, "utf8")) as T;
  } catch {
    return fallback;
  }
}

async function writeJson(target: string, value: unknown): Promise<void> {
  await fs.mkdir(path.dirname(target), { recursive: true });
  await fs.writeFile(target, `${JSON.stringify(value, null, 2)}\n`, "utf8");
}

async function loadConfig(cwd: string): Promise<ContextLayerConfig> {
  const configPath = path.join(cwd, ".pi", "context-layer.json");
  const raw = await readJson<Record<string, unknown>>(configPath, {});
  const vertexProjectId =
    typeof raw.vertexProjectId === "string" && raw.vertexProjectId.trim()
      ? raw.vertexProjectId
      : process.env.GOOGLE_CLOUD_PROJECT ||
        process.env.GCLOUD_PROJECT ||
        process.env.CLOUDSDK_CORE_PROJECT ||
        undefined;
  return {
    workerModel:
      typeof raw.workerModel === "string" && raw.workerModel.trim()
        ? raw.workerModel
        : DEFAULT_CONFIG.workerModel,
    summarizerModel:
      typeof raw.summarizerModel === "string" && raw.summarizerModel.trim()
        ? raw.summarizerModel
        : DEFAULT_CONFIG.summarizerModel,
    multimodalModel:
      typeof raw.multimodalModel === "string" && raw.multimodalModel.trim()
        ? raw.multimodalModel
        : DEFAULT_CONFIG.multimodalModel,
    maxWorkerContext:
      typeof raw.maxWorkerContext === "number" && Number.isFinite(raw.maxWorkerContext)
        ? raw.maxWorkerContext
        : DEFAULT_CONFIG.maxWorkerContext,
    cacheEnabled: typeof raw.cacheEnabled === "boolean" ? raw.cacheEnabled : DEFAULT_CONFIG.cacheEnabled,
    cacheDir:
      typeof raw.cacheDir === "string" && raw.cacheDir.trim()
        ? raw.cacheDir
        : DEFAULT_CONFIG.cacheDir,
    vectorEnabled:
      typeof raw.vectorEnabled === "boolean" ? raw.vectorEnabled : DEFAULT_CONFIG.vectorEnabled,
    vectorProvider: "vertex-ai",
    vectorIndexPath:
      typeof raw.vectorIndexPath === "string" && raw.vectorIndexPath.trim()
        ? raw.vectorIndexPath
        : DEFAULT_CONFIG.vectorIndexPath,
    vectorTopK:
      typeof raw.vectorTopK === "number" && Number.isFinite(raw.vectorTopK)
        ? Math.max(1, Math.floor(raw.vectorTopK))
        : DEFAULT_CONFIG.vectorTopK,
    vectorMinSimilarity:
      typeof raw.vectorMinSimilarity === "number" && Number.isFinite(raw.vectorMinSimilarity)
        ? raw.vectorMinSimilarity
        : DEFAULT_CONFIG.vectorMinSimilarity,
    vertexProjectId,
    vertexLocation:
      typeof raw.vertexLocation === "string" && raw.vertexLocation.trim()
        ? raw.vertexLocation
        : DEFAULT_CONFIG.vertexLocation,
    vertexTextEmbeddingModel:
      typeof raw.vertexTextEmbeddingModel === "string" && raw.vertexTextEmbeddingModel.trim()
        ? raw.vertexTextEmbeddingModel
        : DEFAULT_CONFIG.vertexTextEmbeddingModel,
    vertexMultimodalEmbeddingModel:
      typeof raw.vertexMultimodalEmbeddingModel === "string" && raw.vertexMultimodalEmbeddingModel.trim()
        ? raw.vertexMultimodalEmbeddingModel
        : DEFAULT_CONFIG.vertexMultimodalEmbeddingModel,
    vertexEmbeddingDimensionality:
      typeof raw.vertexEmbeddingDimensionality === "number" &&
      Number.isFinite(raw.vertexEmbeddingDimensionality)
        ? Math.floor(raw.vertexEmbeddingDimensionality)
        : undefined,
  };
}

function resolvePath(cwd: string, target: string): string {
  const clean = target.replace(/[),.;:]+$/u, "");
  return path.isAbsolute(clean) ? clean : path.resolve(cwd, clean);
}

function isLikelyTextFile(filePath: string): boolean {
  return TEXT_EXTENSIONS.has(path.extname(filePath).toLowerCase());
}

function isMultimodalPath(filePath: string): boolean {
  return MULTIMODAL_EXTENSIONS.has(path.extname(filePath).toLowerCase());
}

function mediaTypeFor(filePath: string): string | undefined {
  switch (path.extname(filePath).toLowerCase()) {
    case ".gif":
      return "image/gif";
    case ".jpeg":
    case ".jpg":
      return "image/jpeg";
    case ".png":
      return "image/png";
    case ".webp":
      return "image/webp";
    default:
      return undefined;
  }
}

function normalizeSkipPath(filePath: string): string {
  return filePath.replace(/\\/g, "/");
}

function shouldSkipDir(dirPath: string): boolean {
  const normalized = normalizeSkipPath(dirPath);
  return Array.from(SKIP_DIRS).some((skip) => normalized.endsWith(`/${skip}`) || normalized === skip);
}

async function readTextFile(filePath: string, label: string): Promise<string> {
  const buffer = await fs.readFile(filePath);
  if (buffer.includes(0)) {
    return `[Binary file omitted: ${label}]`;
  }
  return buffer.toString("utf8");
}

async function collectDirectoryContent(dirPath: string, maxChars: number): Promise<string> {
  const parts: string[] = [];
  let remaining = maxChars;

  async function walk(current: string): Promise<void> {
    if (remaining <= 0 || shouldSkipDir(current)) {
      return;
    }
    let entries: Array<{ name: string; isDirectory(): boolean; isFile(): boolean }>;
    try {
      entries = (await fs.readdir(current, { withFileTypes: true })) as Array<{
        name: string;
        isDirectory(): boolean;
        isFile(): boolean;
      }>;
    } catch {
      return;
    }

    for (const entry of entries.sort((a, b) => a.name.localeCompare(b.name))) {
      if (remaining <= 0) {
        return;
      }
      const full = path.join(current, entry.name);
      if (entry.isDirectory()) {
        await walk(full);
        continue;
      }
      if (!entry.isFile() || !isLikelyTextFile(full)) {
        continue;
      }
      const rel = path.relative(dirPath, full);
      const text = await readTextFile(full, rel);
      const block = `\n\n--- FILE: ${rel} ---\n${text}`;
      parts.push(block.slice(0, remaining));
      remaining -= block.length;
    }
  }

  await walk(dirPath);
  if (remaining <= 0) {
    parts.push("\n\n[Directory content truncated to worker context budget.]");
  }
  return parts.join("");
}

function extractReferences(prompt: string): string[] {
  const refs = new Set<string>();
  const pathPattern =
    /(?:^|[\s(["'`])((?:\.{1,2}[\\/][^\s)"'`]+)|(?:[A-Za-z]:[\\/][^\s)"'`]+)|(?:\/[^\s)"'`]+))/g;
  const urlPattern = /\bhttps?:\/\/[^\s)"'`]+/g;
  for (const match of prompt.matchAll(pathPattern)) {
    refs.add(match[1]);
  }
  for (const match of prompt.matchAll(urlPattern)) {
    refs.add(match[0].replace(/[),.;]+$/u, ""));
  }
  return Array.from(refs);
}

async function fetchUrlContent(url: string): Promise<string> {
  const response = await fetch(url);
  const contentType = response.headers.get("content-type") ?? "";
  const body = await response.text();
  return `URL: ${url}\nStatus: ${response.status} ${response.statusText}\nContent-Type: ${contentType}\n\n${body}`;
}

async function detectContextItems(
  prompt: string,
  ctx: ExtensionContext,
  config: ContextLayerConfig,
): Promise<ContextItem[]> {
  const items: ContextItem[] = [];
  const maxChars = Math.max(4000, config.maxWorkerContext * 4);
  const refs = extractReferences(prompt);

  for (const ref of refs) {
    if (/^https?:\/\//i.test(ref)) {
      try {
        const content = await fetchUrlContent(ref);
        items.push({
          kind: "url",
          label: ref,
          content,
          model: config.summarizerModel,
          tokenCount: estimateTokens(content),
        });
      } catch (error) {
        items.push({
          kind: "url",
          label: ref,
          content: `URL reference only; fetch failed: ${String(error)}`,
          model: config.summarizerModel,
          tokenCount: estimateTokens(ref),
        });
      }
      continue;
    }

    const fullPath = resolvePath(ctx.cwd, ref);
    if (!(await exists(fullPath))) {
      continue;
    }
    const stats = await fs.stat(fullPath);
    if (stats.isDirectory()) {
      const content = await collectDirectoryContent(fullPath, maxChars);
      items.push({
        kind: "directory",
        label: fullPath,
        content,
        model: config.workerModel,
        tokenCount: estimateTokens(content),
      });
      continue;
    }
    if (stats.isFile() && isMultimodalPath(fullPath)) {
      items.push({
        kind: "multimodal",
        label: fullPath,
        content: `Multimodal file reference: ${fullPath}\nSize: ${stats.size} bytes\nDo not inline binary content.`,
        model: config.multimodalModel,
        tokenCount: 256,
        mediaPath: fullPath,
        mediaType: mediaTypeFor(fullPath),
      });
      continue;
    }
    if (stats.isFile() && isLikelyTextFile(fullPath)) {
      const content = await readTextFile(fullPath, fullPath);
      items.push({
        kind: "file",
        label: fullPath,
        content,
        model: config.workerModel,
        tokenCount: estimateTokens(content),
      });
    }
  }

  if (estimateTokens(prompt) > LONG_PROMPT_TOKEN_THRESHOLD) {
    items.push({
      kind: "inline",
      label: "inline prompt content",
      content: prompt,
      model: config.summarizerModel,
      tokenCount: estimateTokens(prompt),
    });
  }

  return items;
}

function systemPromptFor(kind: ContextKind): string {
  if (kind === "multimodal") {
    return [
      "You are a perception compression agent.",
      "Your job is to inspect the provided image, video, audio, or OCR-adjacent reference and return a dense structured summary.",
      "Preserve visible text, UI state, entities, errors, timestamps, and relationships. Never invent unseen content.",
    ].join(" ");
  }
  if (kind === "inline") {
    return [
      "You are a log and terminal-output compression agent.",
      "Preserve error patterns, stack traces, command state, recent status, warnings, and exact configuration values.",
      "Output concise markdown.",
    ].join(" ");
  }
  return [
    "You are a context compression agent.",
    "Your only job is to read the provided content and return a dense, structured summary that preserves:",
    "(a) all function/class signatures and key implementation details,",
    "(b) all error messages and their stack traces,",
    "(c) all configuration values,",
    "(d) relationships between components.",
    "Output in markdown with headers. Be as concise as possible while being lossless for a coding agent.",
  ].join(" ");
}

function splitIntoChunks(item: ContextItem, config: ContextLayerConfig): ContextItem[] {
  const maxChars = Math.max(4000, config.maxWorkerContext * 4);
  if (item.content.length <= maxChars) {
    return [item];
  }
  const chunks: ContextItem[] = [];
  for (let offset = 0; offset < item.content.length; offset += maxChars) {
    const index = chunks.length + 1;
    const content = item.content.slice(offset, offset + maxChars);
    chunks.push({
      ...item,
      label: `${item.label} chunk ${index}`,
      content,
      tokenCount: estimateTokens(content),
    });
  }
  return chunks;
}

async function resolveModel(ctx: ExtensionContext, modelSpec: string): Promise<unknown | undefined> {
  const registry = asRecord(ctx).modelRegistry as
    | { find?: (provider: string, model: string) => unknown; getAvailable?: () => Promise<unknown[]> }
    | undefined;
  if (!registry) {
    return undefined;
  }
  if (modelSpec.includes("/")) {
    const [provider, ...rest] = modelSpec.split("/");
    const model = rest.join("/");
    const found = registry.find?.(provider, model);
    if (found) {
      return found;
    }
  }
  const available = await registry.getAvailable?.();
  const normalizedSpec = modelSpec.toLowerCase();
  return available?.find((candidate) => {
    const record = asRecord(candidate);
    const id = typeof record.id === "string" ? record.id : "";
    const provider = typeof record.provider === "string" ? record.provider : "";
    const full = `${provider}/${id}`;
    const normalizedId = id.toLowerCase();
    const normalizedFull = full.toLowerCase();
    return (
      normalizedId === normalizedSpec ||
      normalizedFull === normalizedSpec ||
      normalizedId.endsWith(`/${normalizedSpec}`) ||
      normalizedFull.endsWith(`/${normalizedSpec}`) ||
      normalizedId.includes(normalizedSpec)
    );
  });
}

async function promptOptionsFor(item: ContextItem): Promise<Record<string, unknown> | undefined> {
  if (!item.mediaPath || !item.mediaType?.startsWith("image/")) {
    return undefined;
  }
  const data = await fs.readFile(item.mediaPath, "base64");
  return {
    images: [
      {
        type: "image",
        source: {
          type: "base64",
          mediaType: item.mediaType,
          data,
        },
      },
    ],
  };
}

async function runWorkerSession(
  item: ContextItem,
  ctx: ExtensionContext,
  config: ContextLayerConfig,
): Promise<string> {
  const model = await resolveModel(ctx, item.model);
  if (!model) {
    throw new Error(`Worker model not available: ${item.model}`);
  }
  const loader = new DefaultResourceLoader({
    cwd: ctx.cwd,
    systemPromptOverride: () => systemPromptFor(item.kind),
    agentsFilesOverride: () => ({ agentsFiles: [] }),
    skillsOverride: () => ({ skills: [], diagnostics: [] }),
    promptsOverride: () => ({ prompts: [], diagnostics: [] }),
  });
  await loader.reload();

  workerDepth += 1;
  try {
    const result = await createAgentSession({
      cwd: ctx.cwd,
      model: model as never,
      modelRegistry: asRecord(ctx).modelRegistry as never,
      resourceLoader: loader,
      sessionManager: SessionManager.inMemory(),
      noTools: "all",
    } as never);
    const session = result.session;
    await session.prompt(
      [
        `Context item: ${item.label}`,
        `Kind: ${item.kind}`,
        `Estimated tokens: ${item.tokenCount}`,
        "",
        "```text",
        item.content,
        "```",
      ].join("\n"),
      (await promptOptionsFor(item)) as never,
    );
    const messages = (session as unknown as { messages?: Array<Record<string, unknown>> }).messages ?? [];
    const assistant = [...messages].reverse().find((message) => message.role === "assistant");
    const content = Array.isArray(assistant?.content) ? assistant.content : [];
    const text = content
      .map((part) => {
        const record = asRecord(part);
        return record.type === "text" && typeof record.text === "string" ? record.text : "";
      })
      .filter(Boolean)
      .join("\n");
    session.dispose();
    return text.trim() || "(context worker returned no text)";
  } finally {
    workerDepth -= 1;
  }
}

async function readCache(cacheDir: string, hash: string): Promise<CacheEntry | undefined> {
  const target = path.join(cacheDir, `${hash}.json`);
  const entry = await readJson<CacheEntry | undefined>(target, undefined);
  if (!entry) {
    return undefined;
  }
  const age = Date.now() - Date.parse(entry.timestamp);
  if (!Number.isFinite(age) || age > CACHE_TTL_MS) {
    await fs.rm(target, { force: true });
    return undefined;
  }
  return entry;
}

async function writeCache(cacheDir: string, entry: CacheEntry): Promise<void> {
  await writeJson(path.join(cacheDir, `${entry.hash}.json`), entry);
}

class WorkerQueue {
  private running = 0;
  private readonly pending: Array<() => void> = [];

  async run<T>(task: () => Promise<T>): Promise<T> {
    if (this.running >= WORKER_CONCURRENCY) {
      await new Promise<void>((resolve) => this.pending.push(resolve));
    }
    this.running += 1;
    try {
      return await task();
    } finally {
      this.running -= 1;
      this.pending.shift()?.();
    }
  }
}

const queue = new WorkerQueue();
const execFileAsync = promisify(execFile);

function getSessionDir(ctx: ExtensionContext): string {
  const manager = asRecord(ctx).sessionManager as
    | { getPath?: () => string | undefined; getSessionFile?: () => string | undefined }
    | undefined;
  const sessionFile = manager?.getPath?.() ?? manager?.getSessionFile?.();
  return sessionFile ? path.dirname(sessionFile) : path.join(ctx.cwd, ".pi");
}

function manifestPath(ctx: ExtensionContext): string {
  return path.join(getSessionDir(ctx), "context-manifest.json");
}

async function loadManifest(ctx: ExtensionContext): Promise<ContextManifest> {
  return { ...defaultManifest(), ...(await readJson<Partial<ContextManifest>>(manifestPath(ctx), {})) };
}

async function saveManifest(ctx: ExtensionContext, manifest: ContextManifest): Promise<void> {
  await writeJson(manifestPath(ctx), manifest);
}

async function summarizeItem(
  item: ContextItem,
  ctx: ExtensionContext,
  config: ContextLayerConfig,
  manifest: ContextManifest,
  forceRefresh = false,
): Promise<string> {
  const cacheDir = path.resolve(ctx.cwd, config.cacheDir);
  const hash = hashContent(`${item.model}\n${item.kind}\n${item.label}\n${item.content}`);

  if (config.cacheEnabled && !forceRefresh) {
    const cached = await readCache(cacheDir, hash);
    if (cached) {
      manifest.cache_hits += 1;
      return cached.summary;
    }
  }

  manifest.cache_misses += 1;
  manifest.workers_spawned += 1;
  const summary = await queue.run(() => runWorkerSession(item, ctx, config));
  await addVectorEntry(item, summary, hash, ctx, config, manifest);
  if (config.cacheEnabled) {
    await writeCache(cacheDir, {
      hash,
      timestamp: new Date().toISOString(),
      model: item.model,
      token_count: item.tokenCount,
      summary,
    });
  }
  return summary;
}

async function summarizeItems(
  items: ContextItem[],
  ctx: ExtensionContext,
  config: ContextLayerConfig,
  forceRefresh = false,
  manifest: ContextManifest | undefined = undefined,
): Promise<{ summary: string; manifest: ContextManifest }> {
  manifest ??= await loadManifest(ctx);
  const expanded = items.flatMap((item) => splitIntoChunks(item, config));
  const summaries = await Promise.all(
    expanded.map(async (item) => {
      try {
        const summary = await summarizeItem(item, ctx, config, manifest, forceRefresh);
        manifest.tokens_saved += Math.max(0, item.tokenCount - estimateTokens(summary));
        manifest.last_target = item.label;
        if ((item.kind === "file" || item.kind === "directory") && !manifest.files_summarized.includes(item.label)) {
          manifest.files_summarized.push(item.label);
        }
        return `## ${item.label}\n\n${summary}`;
      } catch (error) {
        return [
          `## ${item.label}`,
          "",
          `Context worker failed: ${String(error)}`,
          "Falling back to raw text excerpt for the thinker.",
          "",
          "```text",
          item.content.slice(0, 12000),
          "```",
        ].join("\n");
      }
    }),
  );
  await saveManifest(ctx, manifest);
  return {
    summary: `[Context Layer]\n\n${summaries.join("\n\n---\n\n")}`,
    manifest,
  };
}

async function cacheState(cwd: string, config: ContextLayerConfig): Promise<{ dir: string; entries: number }> {
  const dir = path.resolve(cwd, config.cacheDir);
  try {
    const entries = await fs.readdir(dir);
    return { dir, entries: entries.filter((entry) => entry.endsWith(".json")).length };
  } catch {
    return { dir, entries: 0 };
  }
}

function vectorIndexPath(cwd: string, config: ContextLayerConfig): string {
  return path.resolve(cwd, config.vectorIndexPath);
}

function emptyVectorIndex(): VectorIndex {
  return { version: 1, provider: "vertex-ai", entries: [] };
}

async function loadVectorIndex(cwd: string, config: ContextLayerConfig): Promise<VectorIndex> {
  return readJson<VectorIndex>(vectorIndexPath(cwd, config), emptyVectorIndex());
}

async function saveVectorIndex(cwd: string, config: ContextLayerConfig, index: VectorIndex): Promise<void> {
  await writeJson(vectorIndexPath(cwd, config), index);
}

async function getGcloudAccessToken(): Promise<string> {
  if (process.env.GOOGLE_OAUTH_ACCESS_TOKEN) {
    return process.env.GOOGLE_OAUTH_ACCESS_TOKEN;
  }
  const result = await execFileAsync("gcloud", ["auth", "print-access-token"], {
    windowsHide: true,
    timeout: 15000,
  });
  const token = result.stdout.trim();
  if (!token) {
    throw new Error("gcloud did not return an access token");
  }
  return token;
}

function cosineSimilarity(a: number[], b: number[]): number {
  const length = Math.min(a.length, b.length);
  if (length === 0) {
    return 0;
  }
  let dot = 0;
  let normA = 0;
  let normB = 0;
  for (let i = 0; i < length; i += 1) {
    dot += a[i] * b[i];
    normA += a[i] * a[i];
    normB += b[i] * b[i];
  }
  if (normA === 0 || normB === 0) {
    return 0;
  }
  return dot / (Math.sqrt(normA) * Math.sqrt(normB));
}

function parseEmbeddingResponse(response: unknown, preferredKey = "embeddings"): number[] {
  const predictions = asRecord(response).predictions;
  if (!Array.isArray(predictions) || predictions.length === 0) {
    throw new Error("Vertex embedding response did not include predictions");
  }
  const first = asRecord(predictions[0]);
  const direct = asRecord(first[preferredKey]).values;
  if (Array.isArray(direct)) {
    return direct.filter((value): value is number => typeof value === "number");
  }
  const textEmbedding = first.textEmbedding;
  if (Array.isArray(textEmbedding)) {
    return textEmbedding.filter((value): value is number => typeof value === "number");
  }
  const imageEmbedding = first.imageEmbedding;
  if (Array.isArray(imageEmbedding)) {
    return imageEmbedding.filter((value): value is number => typeof value === "number");
  }
  throw new Error("Vertex embedding response did not include an embedding vector");
}

async function callVertexPredict(
  config: ContextLayerConfig,
  model: string,
  body: Record<string, unknown>,
): Promise<unknown> {
  if (!config.vertexProjectId) {
    throw new Error(
      "Vertex vector retrieval requires vertexProjectId or GOOGLE_CLOUD_PROJECT/GCLOUD_PROJECT/CLOUDSDK_CORE_PROJECT",
    );
  }
  const token = await getGcloudAccessToken();
  const location = config.vertexLocation;
  const url =
    `https://${location}-aiplatform.googleapis.com/v1/projects/` +
    `${encodeURIComponent(config.vertexProjectId)}/locations/${encodeURIComponent(location)}` +
    `/publishers/google/models/${encodeURIComponent(model)}:predict`;
  const response = await fetch(url, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json; charset=utf-8",
    },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    throw new Error(`Vertex predict failed (${response.status} ${response.statusText}): ${await response.text()}`);
  }
  return response.json();
}

async function embedText(
  text: string,
  config: ContextLayerConfig,
  taskType: "RETRIEVAL_QUERY" | "RETRIEVAL_DOCUMENT" | "CODE_RETRIEVAL_QUERY",
): Promise<number[]> {
  const response = await callVertexPredict(config, config.vertexTextEmbeddingModel, {
    instances: [
      {
        content: text.slice(0, 8000),
        task_type: taskType,
      },
    ],
    parameters: {
      autoTruncate: true,
      ...(config.vertexEmbeddingDimensionality
        ? { outputDimensionality: config.vertexEmbeddingDimensionality }
        : {}),
    },
  });
  return parseEmbeddingResponse(response);
}

async function embedContextItem(item: ContextItem, config: ContextLayerConfig): Promise<number[]> {
  if (item.mediaPath && item.mediaType?.startsWith("image/")) {
    const response = await callVertexPredict(config, config.vertexMultimodalEmbeddingModel, {
      instances: [
        {
          text: item.label,
          image: {
            bytesBase64Encoded: await fs.readFile(item.mediaPath, "base64"),
          },
        },
      ],
    });
    return parseEmbeddingResponse(response, "imageEmbedding");
  }
  return embedText(
    `${item.label}\n\n${item.content.slice(0, 8000)}`,
    config,
    item.kind === "file" || item.kind === "directory" ? "CODE_RETRIEVAL_QUERY" : "RETRIEVAL_DOCUMENT",
  );
}

async function addVectorEntry(
  item: ContextItem,
  summary: string,
  hash: string,
  ctx: ExtensionContext,
  config: ContextLayerConfig,
  manifest: ContextManifest,
): Promise<void> {
  if (!config.vectorEnabled) {
    return;
  }
  try {
    const embedding = await embedContextItem({ ...item, content: summary }, config);
    const index = await loadVectorIndex(ctx.cwd, config);
    const entry: VectorEntry = {
      id: hash,
      hash,
      label: item.label,
      kind: item.kind,
      model: item.model,
      timestamp: new Date().toISOString(),
      embeddingModel: item.mediaPath
        ? config.vertexMultimodalEmbeddingModel
        : config.vertexTextEmbeddingModel,
      embedding,
      summary,
      token_count: item.tokenCount,
    };
    index.entries = [entry, ...index.entries.filter((existing) => existing.hash !== hash)].slice(0, 1000);
    await saveVectorIndex(ctx.cwd, config, index);
    manifest.vector_updates += 1;
  } catch (error) {
    console.warn(`Context Layer vector index update skipped: ${String(error)}`);
  }
}

async function retrieveVectorSummaries(
  prompt: string,
  ctx: ExtensionContext,
  config: ContextLayerConfig,
  manifest: ContextManifest,
): Promise<string> {
  if (!config.vectorEnabled) {
    return "";
  }
  const index = await loadVectorIndex(ctx.cwd, config);
  if (index.entries.length === 0) {
    return "";
  }
  manifest.vector_queries += 1;
  try {
    const queryEmbedding = await embedText(prompt, config, "RETRIEVAL_QUERY");
    const hits = index.entries
      .map((entry) => ({ entry, score: cosineSimilarity(queryEmbedding, entry.embedding) }))
      .filter((hit) => hit.score >= config.vectorMinSimilarity)
      .sort((a, b) => b.score - a.score)
      .slice(0, config.vectorTopK);
    manifest.vector_hits += hits.length;
    if (hits.length === 0) {
      return "";
    }
    return [
      "[Context Layer: Vector Retrieval]",
      ...hits.map(
        ({ entry, score }) =>
          `## ${entry.label}\n\nSimilarity: ${score.toFixed(3)}\nCached: ${entry.timestamp}\n\n${entry.summary}`,
      ),
    ].join("\n\n---\n\n");
  } catch (error) {
    console.warn(`Context Layer vector retrieval skipped: ${String(error)}`);
    return "";
  }
}

async function summarizePathArg(
  args: string,
  ctx: ExtensionContext,
  config: ContextLayerConfig,
  forceRefresh: boolean,
): Promise<string> {
  const prompt = args.trim();
  if (!prompt) {
    return "Usage: /context-worker <file-or-directory-path>";
  }
  const items = await detectContextItems(prompt, ctx, config);
  if (items.length === 0) {
    return `No readable context target found for: ${prompt}`;
  }
  return (await summarizeItems(items, ctx, config, forceRefresh)).summary;
}

export default function piContextLayer(pi: ExtensionAPI): void {
  pi.on("before_agent_start", async (event, ctx) => {
    if (workerDepth > 0) {
      return undefined;
    }
    const prompt = typeof event.prompt === "string" ? event.prompt : "";
    const config = await loadConfig(ctx.cwd);
    const manifest = await loadManifest(ctx);
    const items = await detectContextItems(prompt, ctx, config);
    const vectorSummary = await retrieveVectorSummaries(prompt, ctx, config, manifest);
    if (items.length === 0 && !vectorSummary) {
      await saveManifest(ctx, manifest);
      return undefined;
    }

    ctx.ui?.setStatus?.("context-layer", `Context Layer: ${items.length} item(s)`);
    const directSummary =
      items.length > 0 ? (await summarizeItems(items, ctx, config, false, manifest)).summary : "";
    if (items.length === 0) {
      await saveManifest(ctx, manifest);
    }
    const summary = [vectorSummary, directSummary].filter(Boolean).join("\n\n---\n\n");
    return {
      message: {
        customType: "context-layer",
        content: summary,
        display: true,
      },
      systemPrompt: `${event.systemPrompt}\n\n${summary}`,
    };
  });

  pi.on("after_provider_response", async (_event, ctx) => {
    const manifest = await loadManifest(ctx);
    if (manifest.workers_spawned > 0 || manifest.cache_hits > 0) {
      ctx.ui?.setStatus?.(
        "context-layer",
        `Context Layer: ${manifest.files_summarized.length} cached, ${manifest.tokens_saved} tokens saved, ${manifest.workers_spawned} workers, ${manifest.vector_hits} vector hits`,
      );
    }
  });

  pi.on("session_shutdown", async (_event, ctx) => {
    const manifest = await loadManifest(ctx);
    const footer = `Context Layer: ${manifest.files_summarized.length} files cached, ${manifest.tokens_saved} tokens saved, ${manifest.workers_spawned} workers used, ${manifest.vector_hits} vector hits.`;
    ctx.ui?.setStatus?.("context-layer", footer);
    console.log(footer);
  });

  pi.registerCommand("context-status", {
    description: "Show the context layer manifest and cache state",
    handler: async (_args, ctx) => {
      const config = await loadConfig(ctx.cwd);
      const manifest = await loadManifest(ctx);
      const cache = await cacheState(ctx.cwd, config);
      const vector = await loadVectorIndex(ctx.cwd, config);
      const message = [
        "Context Layer Status",
        `Files summarized: ${manifest.files_summarized.length}`,
        `Tokens saved: ${manifest.tokens_saved}`,
        `Workers spawned: ${manifest.workers_spawned}`,
        `Cache hits: ${manifest.cache_hits}`,
        `Cache misses: ${manifest.cache_misses}`,
        `Vector enabled: ${config.vectorEnabled}`,
        `Vector entries: ${vector.entries.length}`,
        `Vector queries: ${manifest.vector_queries}`,
        `Vector hits: ${manifest.vector_hits}`,
        `Vector updates: ${manifest.vector_updates}`,
        `Cache entries: ${cache.entries}`,
        `Cache dir: ${cache.dir}`,
        `Vector index: ${vectorIndexPath(ctx.cwd, config)}`,
      ].join("\n");
      ctx.ui?.notify?.(message, "info");
      console.log(message);
    },
  });

  pi.registerCommand("context-clear", {
    description: "Clear the context layer manifest and project cache",
    handler: async (_args, ctx) => {
      const config = await loadConfig(ctx.cwd);
      const cache = path.resolve(ctx.cwd, config.cacheDir);
      await fs.rm(cache, { recursive: true, force: true });
      await fs.rm(vectorIndexPath(ctx.cwd, config), { force: true });
      await fs.rm(manifestPath(ctx), { force: true });
      ctx.ui?.notify?.("Context Layer cache and manifest cleared.", "info");
    },
  });

  pi.registerCommand("context-worker", {
    description: "Dispatch a context worker to a specific path or URL",
    handler: async (args, ctx) => {
      const config = await loadConfig(ctx.cwd);
      const summary = await summarizePathArg(args, ctx, config, false);
      pi.sendMessage({ customType: "context-layer", content: summary, display: true });
      ctx.ui?.notify?.("Context worker summary added to the session.", "info");
    },
  });

  pi.registerCommand("context-refresh", {
    description: "Force re-summarize the last context target with a new worker",
    handler: async (_args, ctx) => {
      const config = await loadConfig(ctx.cwd);
      const manifest = await loadManifest(ctx);
      if (!manifest.last_target) {
        ctx.ui?.notify?.("No previous context target to refresh.", "warning");
        return;
      }
      const summary = await summarizePathArg(manifest.last_target, ctx, config, true);
      pi.sendMessage({ customType: "context-layer", content: summary, display: true });
      ctx.ui?.notify?.("Context target refreshed.", "info");
    },
  });
}
