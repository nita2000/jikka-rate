import type { APIRoute } from "astro";
import latest from "../data/latest.json";

export const GET: APIRoute = ({ site }) => {
  const baseUrl = (site ?? new URL("https://jikka-shisan.com")).toString().replace(/\/$/, "");
  const items = [...latest.national_series]
    .reverse()
    .slice(0, 12)
    .map(
      (row) => `    <item>
      <title>全国解体工事単価（${row.date}）：木造 ${row.wood_man_per_tsubo.toFixed(2)}万円/坪 / 鉄骨 ${row.steel_man_per_tsubo.toFixed(2)}万円/坪 / RC ${row.rc_man_per_tsubo.toFixed(2)}万円/坪</title>
      <link>${baseUrl}/pref/</link>
      <guid isPermaLink="false">jikka-shisan-${row.date}</guid>
      <description>基準日 ${row.date} の全国平均解体工事坪単価は木造 ${row.wood_man_per_tsubo.toFixed(2)}万円/坪、鉄骨造 ${row.steel_man_per_tsubo.toFixed(2)}万円/坪、RC造 ${row.rc_man_per_tsubo.toFixed(2)}万円/坪（維持修繕単価指数 ${row.repair_index.toFixed(1)}）です。</description>
    </item>`,
    )
    .join("\n");

  const xml = `<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>実家と空き家の試算表 解体相場・空き家税制・墓じまいフィード</title>
    <link>${baseUrl}/</link>
    <description>全国47都道府県の解体工事単価・空き家率と実家処分・墓じまい損益データ更新フィード</description>
    <language>ja</language>
${items}
  </channel>
</rss>
`;

  return new Response(xml, {
    headers: { "Content-Type": "application/xml; charset=utf-8" },
  });
};
