import type { NextConfig } from "next";

// Static export served by FastAPI under Ingress /app (rewrite strips the prefix).
// No headers/rewrites/redirects/route handlers: unsupported with output "export".
const nextConfig: NextConfig = {
  output: "export",
  basePath: "/app",
  trailingSlash: true,
  images: { unoptimized: true },
  poweredByHeader: false,
  typedRoutes: true,
  env: { NEXT_PUBLIC_BASE_PATH: "/app" },
};

export default nextConfig;
