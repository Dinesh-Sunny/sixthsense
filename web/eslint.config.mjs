import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  {
    files: ["src/**/*.{ts,tsx}"],
    rules: {
      // Static export: Google Fonts is blocked, images are unoptimized, no server code.
      "no-restricted-imports": [
        "error",
        {
          paths: [
            { name: "next/font/google", message: "Use src/app/fonts.ts (local fonts)." },
            { name: "next/image", message: "Static export: use <img> or <video>." },
            { name: "next/server", message: "Static export has no server." },
          ],
        },
      ],
      // One fetch site: src/lib/api/client.ts (basePath + ApiError).
      "no-restricted-globals": ["error", { name: "fetch", message: "Call the API through src/lib/api/client.ts." }],
    },
  },
  {
    files: ["src/lib/api/**"],
    rules: { "no-restricted-globals": "off" },
  },
  globalIgnores([".next/**", "out/**", "build/**", "next-env.d.ts"]),
]);

export default eslintConfig;
