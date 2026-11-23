import type { APIRoute } from "astro";
import siteMeta from "../data/meta.json";
import propertyCases from "../data/property_cases.json";
import comparePairs from "../data/compare_pairs.json";
import prefectures from "../data/prefectures.json";
import historyYearly from "../data/history_yearly.json";

export const GET: APIRoute = ({ site }) => {
  const baseUrl = (site ?? new URL("https://jikka-shisan.com")).toString().replace(/\/$/, "");
  const lastmod = siteMeta.date_to;

  const staticPaths = [
    "/",
    "/tools/disposal-simulator/",
    "/tools/akiya-tax/",
    "/tools/inheritance-deadline/",
    "/tools/hakajimai-simulator/",
    "/cases/",
    "/compare/",
    "/pref/",
    "/history/",
    "/guide/",
    "/guide/akiya-6x-tax-2023-reform/",
    "/guide/sarachi-vs-furuya-breakeven/",
    "/guide/sozoku-toki-penalty-3000man/",
    "/guide/kaitai-cost-asbestos-2026/",
    "/guide/hakajimai-cost-15year-payback/",
    "/about/",
    "/privacy/",
  ];

  const dynamicPaths = [
    ...propertyCases.map((c) => `/cases/${c.slug}/`),
    ...comparePairs.map((p) => `/compare/${p.slug}/`),
    ...prefectures.map((p) => `/pref/${p.slug}/`),
    ...historyYearly.map((y) => `/history/${y.year}/`),
  ];

  const urls = [...staticPaths, ...dynamicPaths]
    .map(
      (p) => `  <url>
    <loc>${baseUrl}${p}</loc>
    <lastmod>${lastmod}</lastmod>
  </url>`,
    )
    .join("\n");

  const xml = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${urls}
</urlset>
`;

  return new Response(xml, {
    headers: { "Content-Type": "application/xml; charset=utf-8" },
  });
};
