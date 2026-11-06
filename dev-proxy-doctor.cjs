/**
 * ACP Care — Doctor Portal Dev Proxy (port 8081)
 *
 * This proxy forwards all requests to the main TanStack Start dev server
 * running on port 8080.  When the root path "/" is requested it redirects
 * the browser to /doctor-login so the Doctor Portal is the entry point.
 *
 * Usage:
 *   node dev-proxy-doctor.cjs
 *
 * No npm packages required — uses only Node.js built-ins.
 */

const http = require("http");

const UPSTREAM_HOST = "127.0.0.1";
const UPSTREAM_PORT = 8080;
const PROXY_PORT = 8081;

const server = http.createServer((req, res) => {
  const url = req.url || "/";

  // Redirect bare root to doctor login page
  if (url === "/" || url === "") {
    res.writeHead(302, { Location: "/doctor-login" });
    res.end();
    return;
  }

  // Forward everything else to the upstream app
  const options = {
    hostname: UPSTREAM_HOST,
    port: UPSTREAM_PORT,
    path: url,
    method: req.method,
    headers: { ...req.headers, host: `${UPSTREAM_HOST}:${UPSTREAM_PORT}` },
  };

  const proxy = http.request(options, (upstreamRes) => {
    res.writeHead(upstreamRes.statusCode || 200, upstreamRes.headers);
    upstreamRes.pipe(res, { end: true });
  });

  proxy.on("error", (err) => {
    console.error("[doctor-proxy] upstream error:", err.message);
    res.writeHead(502);
    res.end("Bad Gateway — is the main app running on port 8080?\n");
  });

  req.pipe(proxy, { end: true });
});

server.listen(PROXY_PORT, "127.0.0.1", () => {
  console.log(`\n  ACP Care — Doctor Portal`);
  console.log(`  ► http://localhost:${PROXY_PORT}/doctor-login`);
  console.log(`  Proxying to main app on port ${UPSTREAM_PORT}\n`);
});

