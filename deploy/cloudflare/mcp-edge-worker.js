const JSON_HEADERS = {
  "content-type": "application/json; charset=utf-8",
  "cache-control": "no-store",
};

function json(data, init = {}) {
  return new Response(JSON.stringify(data, null, 2), {
    ...init,
    headers: {
      ...JSON_HEADERS,
      ...(init.headers || {}),
    },
  });
}

function stripTrailingSlash(value) {
  return value.replace(/\/+$/, "");
}

function buildUpstreamUrl(baseUrl, pathname, search) {
  const url = new URL(baseUrl);
  const basePath = stripTrailingSlash(url.pathname || "");
  url.pathname = `${basePath}${pathname}`;
  url.search = search;
  return url;
}

function requestHasBody(method) {
  return method !== "GET" && method !== "HEAD";
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (url.pathname === "/healthz") {
      return json({ ok: true, service: "llm-wiki-mcp-edge" });
    }

    if (url.pathname !== "/mcp" && !url.pathname.startsWith("/mcp/")) {
      return json({ error: "Not found" }, { status: 404 });
    }

    if (!env.ORIGIN_BASE_URL) {
      return json({ error: "Missing ORIGIN_BASE_URL" }, { status: 500 });
    }

    const edgeToken = env.EDGE_API_TOKEN;
    if (edgeToken) {
      const authorization = request.headers.get("authorization");
      if (authorization !== `Bearer ${edgeToken}`) {
        return json({ error: "Unauthorized" }, { status: 401 });
      }
    }

    const upstreamHeaders = new Headers(request.headers);
    upstreamHeaders.delete("host");
    upstreamHeaders.delete("authorization");

    const accessClientId = env.ACCESS_CLIENT_ID;
    const accessClientSecret = env.ACCESS_CLIENT_SECRET;
    if (accessClientId || accessClientSecret) {
      if (!accessClientId || !accessClientSecret) {
        return json(
          { error: "ACCESS_CLIENT_ID and ACCESS_CLIENT_SECRET must both be set" },
          { status: 500 },
        );
      }
      upstreamHeaders.set("CF-Access-Client-Id", accessClientId);
      upstreamHeaders.set("CF-Access-Client-Secret", accessClientSecret);
    }

    const upstreamUrl = buildUpstreamUrl(env.ORIGIN_BASE_URL, url.pathname, url.search);
    const upstreamResponse = await fetch(upstreamUrl, {
      method: request.method,
      headers: upstreamHeaders,
      body: requestHasBody(request.method) ? request.body : undefined,
      redirect: "manual",
    });

    const responseHeaders = new Headers(upstreamResponse.headers);
    responseHeaders.set("cache-control", "no-store");
    return new Response(upstreamResponse.body, {
      status: upstreamResponse.status,
      statusText: upstreamResponse.statusText,
      headers: responseHeaders,
    });
  },
};
