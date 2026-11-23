/**
 * アフィリエイト（収益化）リンクの一元管理モジュール。
 * A8.net等の規約に完全準拠（コード改変禁止・1pxインプレッション計測画像出力・GA4クリック計測対応）。
 * ASP提携後、各枠にクリックURL（url）と計測用1px画像URL（impPixel）を設定するだけで、
 * 全ページのCTAおよびシミュレーター結果連動型の動的CTAへ一斉反映されます。
 */
export type AffiliateSlot = "akiya" | "sell" | "kaitai" | "kuyo";

export interface AffiliateEntry {
  url: string;
  impPixel: string;
  providerLabel: string;
  buttonText: string;
}

export const AFFILIATE_LINKS: Record<AffiliateSlot, AffiliateEntry> = {
  /** 1. 訳あり物件・空き家専門買取（アルバリンク「訳あり物件買取プロ / 空き家買取プロ」等） */
  akiya: {
    url: "",
    impPixel: "",
    providerLabel: "訳あり物件・空き家専門買取（無料査定）",
    buttonText: "再建築不可・残置物そのまま無料買取査定",
  },
  /** 2. 実家・土地の不動産一括査定（イエウール / HOME4U / リガイド等） */
  sell: {
    url: "",
    impPixel: "",
    providerLabel: "実家・土地の不動産一括査定（無料）",
    buttonText: "実家・土地の売却相場を複数社で無料一括査定",
  },
  /** 3. 解体工事・遺品整理一括見積もり（クラッソーネ等） */
  kaitai: {
    url: "",
    impPixel: "",
    providerLabel: "解体工事・空き家撤去一括見積もり（無料）",
    buttonText: "地域の優良解体業者で最安相場を無料比較",
  },
  /** 4. 墓じまい・永代供養・葬儀資料請求（【ミキワ】墓じまい資料請求 等） */
  kuyo: {
    url: "//af.moshimo.com/af/c/click?a_id=5918328&p_id=1672&pc_id=3119&pl_id=90825",
    impPixel: "//i.moshimo.com/af/i/impression?a_id=5918328&p_id=1672&pc_id=3119&pl_id=90825",
    providerLabel: "墓じまい資料請求（ミキワ）",
    buttonText: "墓じまいの費用・手順の資料を請求する →",
  },
};

export function getAffiliate(slot: AffiliateSlot): AffiliateEntry {
  return AFFILIATE_LINKS[slot];
}
