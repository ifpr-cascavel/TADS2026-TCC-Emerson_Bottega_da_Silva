const { createProxyMiddleware } = require('http-proxy-middleware');

// When API_PROXY_TARGET is set (e.g. http://backend:5000 inside Docker Compose),
// the dev server forwards /api requests to the backend over the internal
// network, so the API does not need to be exposed to the browser.
module.exports = function setupProxy(app) {
  const target = process.env.API_PROXY_TARGET;
  if (!target) {
    return;
  }

  app.use(
    createProxyMiddleware('/api', {
      target,
      changeOrigin: true,
      // Keeps the client IP in X-Forwarded-For so the API rate limit stays per user.
      xfwd: true,
    })
  );
};
