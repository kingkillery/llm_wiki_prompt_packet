import http from "node:http";
import path from "node:path";
import { spawn } from "node:child_process";

const listenPort = Number(process.argv[2] || "8181");
const upstreamPort = Number(process.argv[3] || "18181");
const upstreamHost = process.argv[4] || "127.0.0.1";
const bindHost = process.env.LLM_WIKI_AGENT_API_BIND_HOST || "0.0.0.0";
const bodyLimitBytes = Number(process.env.LLM_WIKI_AGENT_API_BODY_LIMIT_BYTES || "1048576");
const authToken = process.env.LLM_WIKI_AGENT_API_TOKEN || "";
const vaultPath = process.env.LLM_WIKI_VAULT || "/workspace";
const brvCommand = process.env.LLM_WIKI_BRV_COMMAND || "brv";
const brvQueryScript = process.env.LLM_WIKI_BRV_QUERY_SCRIPT || path.join(vaultPath, "scripts", "brv_query.sh");
const brvCurateScript = process.env.LLM_WIKI_BRV_CURATE_SCRIPT || path.join(vaultPath, "scripts", "brv_curate.sh");
const graphBackendUrl = process.env.LLM_WIKI_GITVIZZ_BACKEND_URL || "";

function json(res, statusCode, payload) {
  res.writeHead(statusCode, { "content-type": "application/json; charset=utf-8" });
  res.end(JSON.stringify(payload));
}

function text(res, statusCode, message) {
  res.writeHead(statusCode, { "content-type": "text/plain; charset=utf-8" });
  res.end(`${message}\n`);
}

function isAuthorized(req) {
  if (!authToken) {
    return true;
  }
  return req.headers.authorization === `Bearer ${authToken}`;
}

function stripHopByHopHeaders(headers) {
  const next = { ...headers };
  for (const key of ["connection", "content-length", "host", "keep-alive", "proxy-connection", "transfer-encoding", "upgrade"]) {
    delete next[key];
  }
  return next;
}

function proxyRequest(req, res, options) {
  const upstream = http.request(
    {
      hostname: options.hostname,
      port: options.port,
      path: options.path,
      method: req.method,
      headers: {
        ...stripHopByHopHeaders(req.headers),
        host: `${options.hostname}:${options.port}`,
      },
    },
    (upstreamRes) => {
      res.writeHead(upstreamRes.statusCode || 502, upstreamRes.headers);
      upstreamRes.pipe(res);
    }
  );

  upstream.on("error", (error) => {
    const message = error instanceof Error ? error.message : String(error);
    console.error(`Gateway upstream error: ${message}`);
    text(res, 502, `Gateway upstream error: ${message}`);
  });

  req.pipe(upstream);
}

function collectBody(req) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    let total = 0;

    req.on("data", (chunk) => {
      total += chunk.length;
      if (total > bodyLimitBytes) {
        reject(new Error(`request body exceeds ${bodyLimitBytes} bytes`));
        req.destroy();
        return;
      }
      chunks.push(chunk);
    });
    req.on("end", () => resolve(Buffer.concat(chunks)));
    req.on("error", reject);
  });
}

function parseJsonBody(buffer) {
  if (!buffer.length) {
    return {};
  }
  return JSON.parse(buffer.toString("utf-8"));
}

function parseLastJsonLine(stdout) {
  const lines = stdout
    .split(/\r?\n/u)
    .map((line) => line.trim())
    .filter(Boolean);

  for (let index = lines.length - 1; index >= 0; index -= 1) {
    try {
      return JSON.parse(lines[index]);
    } catch {
      // keep scanning older lines
    }
  }
  return null;
}

function resolveScriptCommand(scriptPath) {
  const extension = path.extname(scriptPath).toLowerCase();
  if (extension === ".sh") {
    return ["bash", [scriptPath]];
  }
  if (extension === ".ps1") {
    return [process.platform === "win32" ? "powershell" : "pwsh", ["-NoProfile", "-ExecutionPolicy", "Bypass", "-File", scriptPath]];
  }
  if (extension === ".py") {
    return [process.env.PYTHON_BIN || "python3", [scriptPath]];
  }
  if (extension === ".js" || extension === ".mjs" || extension === ".cjs") {
    return [process.execPath, [scriptPath]];
  }
  if (extension === ".cmd" || extension === ".bat") {
    return [process.env.ComSpec || "cmd.exe", ["/d", "/s", "/c", scriptPath]];
  }
  return [scriptPath, []];
}

function runProcess(command, args, options = {}) {
  return new Promise((resolve, reject) => {
    const child = spawn(command, args, {
      cwd: options.cwd,
      env: options.env,
      stdio: ["pipe", "pipe", "pipe"],
      windowsHide: true,
    });

    let stdout = "";
    let stderr = "";
    const timeoutMs = options.timeoutMs || 15000;
    let timedOut = false;
    const timer = setTimeout(() => {
      timedOut = true;
      child.kill("SIGTERM");
    }, timeoutMs);

    child.stdout.on("data", (chunk) => {
      stdout += chunk.toString("utf-8");
    });
    child.stderr.on("data", (chunk) => {
      stderr += chunk.toString("utf-8");
    });
    child.on("error", (error) => {
      clearTimeout(timer);
      reject(error);
    });
    child.on("close", (code) => {
      clearTimeout(timer);
      if (timedOut) {
        reject(new Error(`command timed out after ${timeoutMs}ms`));
        return;
      }
      resolve({ code: code ?? 1, stdout, stderr });
    });

    if (options.stdin) {
      child.stdin.write(options.stdin);
    }
    child.stdin.end();
  });
}

async function runScript(scriptPath, args) {
  const [command, prefixArgs] = resolveScriptCommand(scriptPath);
  return runProcess(command, [...prefixArgs, ...args], {
    cwd: vaultPath,
    env: process.env,
  });
}

async function runBrvStatus() {
  return runProcess(brvCommand, ["status", "--format", "json"], {
    cwd: vaultPath,
    env: process.env,
  });
}

async function handleMemoryStatus(res) {
  try {
    const result = await runBrvStatus();
    const payload = parseLastJsonLine(result.stdout);
    if (result.code !== 0) {
      json(res, 503, {
        ok: false,
        error: result.stderr.trim() || "brv status failed",
        exit_code: result.code,
      });
      return;
    }
    json(res, 200, {
      ok: true,
      payload,
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    json(res, 503, { ok: false, error: message });
  }
}

async function handleMemoryCommand(req, res, mode) {
  if (req.method !== "POST") {
    text(res, 405, "Method not allowed");
    return;
  }

  let payload;
  try {
    payload = parseJsonBody(await collectBody(req));
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    json(res, 400, { ok: false, error: message });
    return;
  }

  const scriptPath = mode === "query" ? brvQueryScript : brvCurateScript;
  const args = [];
  if (mode === "query") {
    if (!payload.query || typeof payload.query !== "string") {
      json(res, 400, { ok: false, error: "query is required" });
      return;
    }
    args.push("--query", payload.query);
    if (payload.useQueryExperiment) {
      args.push("--use-query-experiment");
    }
  } else {
    if (!payload.content || typeof payload.content !== "string") {
      json(res, 400, { ok: false, error: "content is required" });
      return;
    }
    args.push("--content", payload.content);
  }

  if (payload.provider && typeof payload.provider === "string") {
    args.push("--provider", payload.provider);
  }
  if (payload.model && typeof payload.model === "string") {
    args.push("--model", payload.model);
  }

  try {
    const result = await runScript(scriptPath, args);
    const parsed = parseLastJsonLine(result.stdout);
    if (result.code !== 0) {
      json(res, 502, {
        ok: false,
        error: result.stderr.trim() || `${mode} failed`,
        exit_code: result.code,
      });
      return;
    }
    json(res, 200, {
      ok: true,
      payload: parsed ?? result.stdout.trim(),
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    json(res, 502, { ok: false, error: message });
  }
}

function healthPayload() {
  return {
    ok: true,
    auth_enabled: Boolean(authToken),
    routes: {
      mcp: true,
      graph: Boolean(graphBackendUrl),
      memory_status: true,
      memory_query: true,
      memory_curate: true,
    },
    memory: {
      command: brvCommand,
      query_script: brvQueryScript,
      curate_script: brvCurateScript,
    },
    qmd: {
      upstream_host: upstreamHost,
      upstream_port: upstreamPort,
    },
  };
}

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url || "/", `http://${req.headers.host || "localhost"}`);
  const pathname = url.pathname;

  if (pathname === "/healthz") {
    json(res, 200, healthPayload());
    return;
  }

  if (!isAuthorized(req)) {
    json(res, 401, { ok: false, error: "Unauthorized" });
    return;
  }

  if (pathname === "/mcp" || pathname.startsWith("/mcp/")) {
    proxyRequest(req, res, {
      hostname: upstreamHost,
      port: upstreamPort,
      path: `${pathname}${url.search}`,
    });
    return;
  }

  if (pathname === "/graph" || pathname.startsWith("/graph/")) {
    if (!graphBackendUrl) {
      json(res, 503, { ok: false, error: "GitVizz backend is not configured" });
      return;
    }
    const backendUrl = new URL(graphBackendUrl);
    const strippedPath = pathname === "/graph" ? "/" : pathname.slice("/graph".length);
    proxyRequest(req, res, {
      hostname: backendUrl.hostname,
      port: Number(backendUrl.port || (backendUrl.protocol === "https:" ? "443" : "80")),
      path: `${backendUrl.pathname.replace(/\/$/, "")}${strippedPath}${url.search}`,
    });
    return;
  }

  if (pathname === "/memory/status") {
    await handleMemoryStatus(res);
    return;
  }

  if (pathname === "/memory/query") {
    await handleMemoryCommand(req, res, "query");
    return;
  }

  if (pathname === "/memory/curate") {
    await handleMemoryCommand(req, res, "curate");
    return;
  }

  json(res, 404, { ok: false, error: "Not found" });
});

for (const signal of ["SIGINT", "SIGTERM"]) {
  process.on(signal, () => {
    server.close(() => process.exit(0));
  });
}

server.listen(listenPort, bindHost, () => {
  const authMode = authToken ? "bearer-auth enabled" : "loopback/trusted network mode";
  console.error(`Agent gateway listening on ${bindHost}:${listenPort} (${authMode})`);
});
