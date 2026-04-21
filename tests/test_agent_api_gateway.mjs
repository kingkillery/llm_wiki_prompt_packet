import test from "node:test";
import assert from "node:assert/strict";
import http from "node:http";
import os from "node:os";
import path from "node:path";
import { mkdtemp, writeFile, rm } from "node:fs/promises";
import { spawn } from "node:child_process";

const repoRoot = path.resolve(import.meta.dirname, "..");
const gatewayScript = path.join(repoRoot, "docker", "mcp_http_proxy.mjs");

function createJsonServer(handler) {
  const requests = [];
  const server = http.createServer(async (req, res) => {
    const chunks = [];
    for await (const chunk of req) {
      chunks.push(chunk);
    }
    const body = Buffer.concat(chunks).toString("utf-8");
    requests.push({ method: req.method, url: req.url, body, headers: req.headers });
    await handler(req, res, body);
  });
  return { server, requests };
}

async function listen(server) {
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  const address = server.address();
  return { host: "127.0.0.1", port: address.port };
}

async function closeServer(server) {
  await new Promise((resolve) => server.close(resolve));
}

async function waitForHealth(port, token = "") {
  for (let attempt = 0; attempt < 40; attempt += 1) {
    try {
      const response = await fetch(`http://127.0.0.1:${port}/healthz`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (response.ok) {
        return;
      }
    } catch {
      // server not ready yet
    }
    await new Promise((resolve) => setTimeout(resolve, 100));
  }
  throw new Error("Gateway did not become healthy in time");
}

async function startGateway(options) {
  const child = spawn(process.execPath, [gatewayScript, String(options.listenPort), String(options.qmdPort), "127.0.0.1"], {
    cwd: repoRoot,
    env: {
      ...process.env,
      LLM_WIKI_GITVIZZ_BACKEND_URL: options.graphUrl || "",
      LLM_WIKI_AGENT_API_TOKEN: options.token || "",
      LLM_WIKI_AGENT_API_BIND_HOST: options.bindHost || "127.0.0.1",
      LLM_WIKI_AGENT_API_UNSAFE_NO_AUTH: options.allowUnsafeNoAuth ? "1" : "",
      LLM_WIKI_BRV_QUERY_SCRIPT: options.queryScript || "",
      LLM_WIKI_BRV_CURATE_SCRIPT: options.curateScript || "",
      LLM_WIKI_BRV_COMMAND: options.brvCommand || "brv",
      LLM_WIKI_VAULT: options.vaultPath || repoRoot,
    },
    stdio: ["ignore", "pipe", "pipe"],
    windowsHide: true,
  });

  let stderr = "";
  child.stderr.on("data", (chunk) => {
    stderr += chunk.toString("utf-8");
  });

  await waitForHealth(options.listenPort, options.token || "");

  return {
    child,
    getStderr: () => stderr,
    async stop() {
      child.kill("SIGTERM");
      await new Promise((resolve) => child.on("close", resolve));
    },
  };
}

async function waitForExit(child, timeoutMs = 5000) {
  return await new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error("Process did not exit in time")), timeoutMs);
    child.on("close", (code) => {
      clearTimeout(timer);
      resolve(code);
    });
  });
}

test("gateway proxies /mcp, /graph, and memory routes without auth in local mode", async (t) => {
  const qmd = createJsonServer(async (_req, res, body) => {
    res.writeHead(200, { "content-type": "application/json" });
    res.end(JSON.stringify({ ok: true, upstream: "qmd", body }));
  });
  const graph = createJsonServer(async (req, res) => {
    res.writeHead(200, { "content-type": "application/json" });
    res.end(JSON.stringify({ ok: true, upstream: "graph", path: req.url }));
  });

  const { port: qmdPort } = await listen(qmd.server);
  const { port: graphPort } = await listen(graph.server);

  const tempDir = await mkdtemp(path.join(os.tmpdir(), "llm-wiki-gateway-"));
  const queryScript = path.join(tempDir, "query.mjs");
  const curateScript = path.join(tempDir, "curate.mjs");
  await writeFile(
    queryScript,
    "console.log(JSON.stringify({success:true,data:{result:'query ok'}}));\n",
    "utf-8"
  );
  await writeFile(
    curateScript,
    "console.log(JSON.stringify({success:true,data:{message:'curate ok'}}));\n",
    "utf-8"
  );

  const probe = http.createServer();
  const { port: gatewayPort } = await listen(probe);
  await closeServer(probe);

  const gateway = await startGateway({
    listenPort: gatewayPort,
    qmdPort,
    graphUrl: `http://127.0.0.1:${graphPort}`,
    queryScript,
    curateScript,
  });

  t.after(async () => {
    await gateway.stop();
    await closeServer(qmd.server);
    await closeServer(graph.server);
    await rm(tempDir, { recursive: true, force: true });
  });

  const mcpResponse = await fetch(`http://127.0.0.1:${gatewayPort}/mcp`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ ping: true }),
  });
  assert.equal(mcpResponse.status, 200);
  assert.equal(qmd.requests[0].url, "/mcp");

  const graphResponse = await fetch(`http://127.0.0.1:${gatewayPort}/graph/openapi.json?x=1`);
  assert.equal(graphResponse.status, 200);
  const graphPayload = await graphResponse.json();
  assert.equal(graphPayload.path, "/openapi.json?x=1");

  const queryResponse = await fetch(`http://127.0.0.1:${gatewayPort}/memory/query`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ query: "what matters?" }),
  });
  assert.equal(queryResponse.status, 200);
  const queryPayload = await queryResponse.json();
  assert.equal(queryPayload.payload.data.result, "query ok");

  const curateResponse = await fetch(`http://127.0.0.1:${gatewayPort}/memory/curate`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ content: "durable note" }),
  });
  assert.equal(curateResponse.status, 200);
  const curatePayload = await curateResponse.json();
  assert.equal(curatePayload.payload.data.message, "curate ok");

  const healthResponse = await fetch(`http://127.0.0.1:${gatewayPort}/healthz`);
  const healthPayload = await healthResponse.json();
  assert.equal(healthPayload.routes.mcp, true);
  assert.equal(healthPayload.routes.graph, true);
});

test("gateway enforces bearer auth when a token is configured", async (t) => {
  const qmd = createJsonServer(async (_req, res) => {
    res.writeHead(200, { "content-type": "application/json" });
    res.end(JSON.stringify({ ok: true }));
  });
  const { port: qmdPort } = await listen(qmd.server);
  const probe = http.createServer();
  const { port: gatewayPort } = await listen(probe);
  await closeServer(probe);

  const gateway = await startGateway({
    listenPort: gatewayPort,
    qmdPort,
    token: "secret-token",
  });

  t.after(async () => {
    await gateway.stop();
    await closeServer(qmd.server);
  });

  const unauthorized = await fetch(`http://127.0.0.1:${gatewayPort}/mcp`, { method: "POST" });
  assert.equal(unauthorized.status, 401, gateway.getStderr());

  const authorized = await fetch(`http://127.0.0.1:${gatewayPort}/mcp`, {
    method: "POST",
    headers: { Authorization: "Bearer secret-token" },
  });
  assert.equal(authorized.status, 200);
});

test("gateway refuses non-loopback binds without auth unless explicitly overridden", async () => {
  const qmd = createJsonServer(async (_req, res) => {
    res.writeHead(200, { "content-type": "application/json" });
    res.end(JSON.stringify({ ok: true }));
  });
  const { port: qmdPort } = await listen(qmd.server);
  const probe = http.createServer();
  const { port: gatewayPort } = await listen(probe);
  await closeServer(probe);

  const child = spawn(process.execPath, [gatewayScript, String(gatewayPort), String(qmdPort), "127.0.0.1"], {
    cwd: repoRoot,
    env: {
      ...process.env,
      LLM_WIKI_AGENT_API_BIND_HOST: "0.0.0.0",
      LLM_WIKI_VAULT: repoRoot,
    },
    stdio: ["ignore", "pipe", "pipe"],
    windowsHide: true,
  });

  let stderr = "";
  child.stderr.on("data", (chunk) => {
    stderr += chunk.toString("utf-8");
  });

  const exitCode = await waitForExit(child);
  await closeServer(qmd.server);

  assert.notEqual(exitCode, 0);
  assert.match(stderr, /Refusing to bind 0\.0\.0\.0/);
});
