/**
 * ACP Care — Doctor Portal Dev Proxy (port 8081)
 *
 * This proxy forwards requests to the main TanStack Start dev server
 * running on port 8080. When the root path "/" is requested it redirects
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
  const reqUrl = req.url || "/";
  const [pathname, search] = reqUrl.split("?");
  const query = search ? `?${search}` : "";

    // Never forward doctor portal root or index to the patient homepage.
    // Redirect bare root, empty path, or /index.html directly to /doctor-login.
    if (pathname === "/" || pathname === "" || pathname === "/index.html") {
      res.writeHead(302, {
        Location: "/doctor-login" + query,
        "Cache-Control": "no-cache, no-store, must-revalidate",
      });
      res.end();
      return;
    }

    // Forward everything else to upstream app
    const options = {
      hostname: UPSTREAM_HOST,
      port: UPSTREAM_PORT,
      path: reqUrl,
      method: req.method,
      headers: {
        ...req.headers,
        host: `${UPSTREAM_HOST}:${UPSTREAM_PORT}`,
        "x-forwarded-host": req.headers.host || `localhost:${PROXY_PORT}`,
        "x-forwarded-port": String(PROXY_PORT),
        "x-forwarded-proto": "http",
      },
    };

    const proxy = http.request(options, (upstreamRes) => {
      const headers = { ...upstreamRes.headers };

      // Rewrite Location header on redirects so the user stays on port 8081
      if (headers.location) {
        if (headers.location === "/" || headers.location === "") {
          headers.location = "/doctor-login";
        } else {
          headers.location = headers.location
            .replace(new RegExp(`http://${UPSTREAM_HOST}:${UPSTREAM_PORT}`, "g"), `http://localhost:${PROXY_PORT}`)
            .replace(new RegExp(`http://localhost:${UPSTREAM_PORT}`, "g"), `http://localhost:${PROXY_PORT}`);
        }
      }

      res.writeHead(upstreamRes.statusCode || 200, headers);
      upstreamRes.pipe(res, { end: true });
    });

    proxy.on("error", (err) => {
      console.error("[doctor-proxy] upstream error:", err.message);
      res.writeHead(502, { "Content-Type": "text/plain" });
      res.end("Bad Gateway - is the main app running on port 8080?\n");
    });

    req.pipe(proxy, { end: true });
  });

// Support Vite HMR WebSocket upgrade proxying
server.on("upgrade", (req, socket, head) => {
  const proxyReq = http.request({
    hostname: UPSTREAM_HOST,
    port: UPSTREAM_PORT,
    path: req.url,
    method: req.method,
    headers: {
      ...req.headers,
      host: `${UPSTREAM_HOST}:${UPSTREAM_PORT}`,
    },
  });

  proxyReq.on("upgrade", (proxyRes, proxySocket, proxyHead) => {
    socket.write(
      `HTTP/${proxyRes.httpVersion} ${proxyRes.statusCode} ${proxyRes.statusMessage}\r\n` +
      Object.entries(proxyRes.headers)
        .map(([k, v]) => `${k}: ${v}`)
        .join("\r\n") +
      "\r\n\r\n"
    );
    if (proxyHead && proxyHead.length) socket.unshift(proxyHead);
    proxySocket.pipe(socket);
    socket.pipe(proxySocket);
  });

  proxyReq.on("error", () => {
    socket.destroy();
  });

  proxyReq.end();
});

server.on("error", (err) => {
  if (err.code === "EADDRINUSE") {
    console.error(`\n[doctor-proxy] Port ${PROXY_PORT} is already in use.`);
    console.error(`Ensure no stale process is holding port ${PROXY_PORT}.\n`);
  } else {
    console.error("[doctor-proxy] Server error:", err.message);
  }
  process.exit(1);
});

server.listen(PROXY_PORT, "127.0.0.1", () => {
  console.log(`\n  ACP Care - Doctor Portal`);
  console.log(`  -> http://localhost:${PROXY_PORT}/doctor-login`);
  console.log(`  Proxying to main app on port ${UPSTREAM_PORT}\n`);
});
