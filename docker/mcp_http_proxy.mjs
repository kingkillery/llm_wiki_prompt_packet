import http from "node:http";

const listenPort = Number(process.argv[2] || "8181");
const upstreamPort = Number(process.argv[3] || "18181");

const server = http.createServer((req, res) => {
  const upstream = http.request(
    {
      hostname: "::1",
      family: 6,
      port: upstreamPort,
      path: req.url || "/",
      method: req.method,
      headers: {
        ...req.headers,
        host: `[::1]:${upstreamPort}`,
      },
    },
    (upstreamRes) => {
      res.writeHead(upstreamRes.statusCode || 502, upstreamRes.headers);
      upstreamRes.pipe(res);
    }
  );

  upstream.on("error", (error) => {
    const message = error instanceof Error ? error.message : String(error);
    console.error(`MCP upstream error: ${message}`);
    res.writeHead(502, { "content-type": "text/plain; charset=utf-8" });
    res.end(`MCP upstream error: ${message}\n`);
  });

  req.pipe(upstream);
});

for (const signal of ["SIGINT", "SIGTERM"]) {
  process.on(signal, () => {
    server.close(() => process.exit(0));
  });
}

server.listen(listenPort, "0.0.0.0");
