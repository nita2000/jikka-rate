import type { APIRoute } from "astro";
import siteMeta from "../data/meta.json";
import latest from "../data/latest.json";
import propertyCases from "../data/property_cases.json";
import comparePairs from "../data/compare_pairs.json";

export const GET: APIRoute = ({ site }) => {
  const baseUrl = (site ?? new URL("https://jikka-shisan.com")).toString().replace(/\/$/, "");

  const topCases = propertyCases
    .slice(0, 12)
    .map((c) => {
      const isGrave = c.structure === "grave";
      const cost = isGrave && c.calc.hakajimai
        ? `墓じまい初期総額 ${c.calc.hakajimai.initial_total_yen.toLocaleString("ja-JP")}円 / 約${c.calc.hakajimai.payback_years}年回収`
        : `解体処分総額 ${c.calc.demolition.total_demolition_yen.toLocaleString("ja-JP")}円 / 通常維持費 年${c.calc.maintenance.annual_keep_normal.toLocaleString("ja-JP")}円 / 最適処分 ${c.calc.disposal.best_strategy_label}`;
      return `- ${c.name}: ${baseUrl}/cases/${c.slug}/ （${cost}）`;
    })
    .join("\n");

  const topPairs = comparePairs
    .slice(0, 12)
    .map((p) => `- ${p.title}: ${baseUrl}/compare/${p.slug}/ （結論: ${p.verdict_short}）`)
    .join("\n");

  const body = `# 実家と空き家の試算表

> 総務省・国土交通省・厚生労働省の公的統計と最新税制（空き家の固定資産税特例解除・譲渡所得税と3,000万円特別控除・相続登記義務化）にもとづき、全国47都道府県の空き家率・解体坪単価、実家処分・買取・相続期限・墓じまいの損益分岐点を試算・比較できるサイトです。

## データ収録範囲・適用基準
- 解体単価・修繕指数収録期間: ${siteMeta.date_from} 〜 ${siteMeta.date_to}（${siteMeta.total_points}期分）
- 最新全国平均（${latest.date}）: 木造解体 ${latest.national.wood_man_per_tsubo.toFixed(2)}万円/坪 / 鉄骨造解体 ${latest.national.steel_man_per_tsubo.toFixed(2)}万円/坪 / RC造解体 ${latest.national.rc_man_per_tsubo.toFixed(2)}万円/坪 / 全国空き家率 ${latest.national.akiya_rate_pct}%（放置型空き家 ${latest.national.other_akiya_rate_pct}%）
- 適用法改正・税制基準: 2023年12月施行「管理不全空家等の住宅用地特例解除（実効約4.2倍・本則最大6倍）」、2024年1月改正「空き家3,000万円特別控除（買主側での翌年2月15日までの解体・耐震改修対応）」、2024年4月施行「相続登記義務化（10万円以下の過料）」、2026年4月施行「住所変更登記義務化（5万円以下の過料）」
- 出典: ${siteMeta.source_credit}

## 主要ページ・インタラクティブ試算ツール
- トップ（全国空き家率・解体単価＆総合試算表）: ${baseUrl}/
- 実家の手残り試算（空き家維持 vs 更地解体売却 vs そのまま売却・買取、譲渡税・3,000万円控除・きょうだい分配対応）: ${baseUrl}/tools/disposal-simulator/
- 空き家の固定資産税（住宅用地特例解除）＆相続登記費用シミュレーター: ${baseUrl}/tools/akiya-tax/
- 相続手続き期限＆空き家3,000万円特別控除 逆算カレンダー: ${baseUrl}/tools/inheritance-deadline/
- 遠方の墓維持 vs 墓じまい（永代供養・樹木葬）15年損益＆葬祭費シミュレーター: ${baseUrl}/tools/hakajimai-simulator/
- 売れない実家・土地の最終出口（相続土地国庫帰属制度・法定負担金 vs 維持・買取・相続放棄）シミュレーター: ${baseUrl}/tools/kokko-kizoku/
- 主要${siteMeta.total_cases}パターン 実家・空き家・お墓タイプ別相場データベース: ${baseUrl}/cases/
- 実家・終活の2択損益分岐比較一覧（${siteMeta.total_compare_pairs}組）: ${baseUrl}/compare/
- 全国47都道府県別 空き家率・解体坪単価・葬祭費一覧: ${baseUrl}/pref/
- 年別 解体工事単価・維持修繕指数アーカイブ: ${baseUrl}/history/
- データ連動検証ガイド: ${baseUrl}/guide/
- RSSフィード: ${baseUrl}/rss.xml
- サイトマップ: ${baseUrl}/sitemap.xml

## 代表ケース別ページ（抜粋）
${topCases}

## 2択損益分岐比較ページ（抜粋）
${topPairs}
`;

  return new Response(body, {
    headers: { "Content-Type": "text/plain; charset=utf-8" },
  });
};
