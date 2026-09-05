const devScriptPolicy = process.env.NODE_ENV === "development" ? " 'unsafe-eval'" : "";
const devConnectPolicy =
  process.env.NODE_ENV === "development" ? " http://localhost:8000 http://127.0.0.1:8000" : "";

const securityHeaders = [
  { key: "X-Frame-Options", value: "DENY" },
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
  { key: "Strict-Transport-Security", value: "max-age=63072000; includeSubDomains; preload" },
  {
    key: "Content-Security-Policy",
    value:
      `default-src 'self'; script-src 'self' 'unsafe-inline' https://challenges.cloudflare.com${devScriptPolicy}; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; frame-src https://challenges.cloudflare.com; connect-src 'self' https:${devConnectPolicy}; object-src 'none'; base-uri 'none'; form-action 'self'; frame-ancestors 'none';`,
  },
];

/** @type {import('next').NextConfig} */
const nextConfig = {
  poweredByHeader: false,
  allowedDevOrigins: ["127.0.0.1"],
  async headers() {
    return [
      {
        source: "/(.*)",
        headers: securityHeaders,
      },
    ];
  },
};

export default nextConfig;
