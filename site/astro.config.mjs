import { defineConfig } from "astro/config";
import tailwindcss from "@tailwindcss/vite";

// Cloudflare Pages の環境変数 SITE_URL を設定すれば、コード修正なしで独自ドメインへ切替可能
const siteUrl = process.env.SITE_URL || "https://jikkarate.com";

export default defineConfig({
  site: siteUrl,
  output: "static",
  vite: {
    plugins: [tailwindcss()],
  },
});
