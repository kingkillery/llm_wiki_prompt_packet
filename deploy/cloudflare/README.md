# Cloudflare edge for the hosted llm-wiki stack

Use Cloudflare as the public edge and keep the GCP VM private by default.

Recommended split:

- `Worker` on `mcp.<your-domain>` is the public API entry for remote MCP or app clients.
- `Tunnel` on `mcp-origin.<your-domain>` points to the VM-local `http://127.0.0.1:8181`.
- `Access` protects the tunnel origin with a service token consumed by the Worker.
- `Access` also protects the human-facing GitVizz hostname, usually `gitvizz.<your-domain>`.

This keeps the packet service private on GCP while still giving you a stable HTTPS edge.

Files in this folder:

- `mcp-edge-worker.js` is a minimal Worker that proxies `/mcp` to the tunnel hostname.
- `wrangler.jsonc.example` is a starting config for deploying the Worker.

Suggested hostnames:

- `mcp.<your-domain>`: Worker custom domain for remote clients
- `mcp-origin.<your-domain>`: Tunnel-backed origin hostname for the packet MCP server
- `gitvizz.<your-domain>`: Tunnel-backed GitVizz frontend behind interactive Access
- `gitvizz-api.<your-domain>`: optional separate GitVizz backend hostname if you expose it independently

Recommended sequence:

1. Deploy the packet VM with `bash ./deploy/gcp/deploy_compute_engine.sh`.
2. Leave `OPEN_PUBLIC_MCP=0` so the script does not create a public firewall rule for port `8181`.
3. Create a Cloudflare Tunnel from the VM to `http://127.0.0.1:8181`.
4. Create a Cloudflare Access self-hosted application for `mcp-origin.<your-domain>`.
5. Create an Access service token for the Worker-to-origin hop.
6. Deploy the Worker from this folder with:

```bash
npx wrangler secret put ACCESS_CLIENT_ID
npx wrangler secret put ACCESS_CLIENT_SECRET
npx wrangler secret put EDGE_API_TOKEN
npx wrangler deploy
```

7. Set `LLM_WIKI_QMD_MCP_URL=https://mcp.<your-domain>/mcp` when you want the packet config to advertise the edge URL instead of the VM-local URL.

Notes:

- `brv` should stay private on the VM or inside your app layer. Do not expose raw BRV provider credentials directly to the edge.
- GitVizz can now run either as its own runtime or as an optional Docker sidecar stack behind the VM. Keep it on its own hostname and gate it with interactive Access rather than routing it through the Worker.
- If you intentionally want direct VM ingress for testing, set `OPEN_PUBLIC_MCP=1` and `PUBLIC_MCP_SOURCE_RANGES=<cidr-list>` when deploying.
