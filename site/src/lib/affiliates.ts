/**
 * アフィリエイト（収益化）リンクの一元管理モジュール。
 * A8.net等の規約に完全準拠（コード改変禁止・1pxインプレッション計測画像出力・GA4クリック計測対応）。
 * ASP提携後、各枠にクリックURL（url）と計測用1px画像URL（impPixel）を設定するだけで、
 * 全ページのCTAおよびシミュレーター結果連動型の動的CTAへ一斉反映されます。
 */
export type AffiliateSlot = "akiya" | "sell" | "kaitai" | "kuyo" | "sozoku";

export interface AffiliateEntry {
  url: string;
  impPixel: string;
  providerLabel: string;
  buttonText: string;
  useAttributionSrc?: boolean;
}

export const AFFILIATE_LINKS: Record<AffiliateSlot, AffiliateEntry> = {
  /** 1. 訳あり物件・空き家専門買取（訳アリ不動産買取専門店【ラクウル】） */
  akiya: {
    url: "https://px.a8.net/svt/ejp?a8mat=4BGS18+3F8X6A+56AO+5YJRM",
    impPixel: "https://www16.a8.net/0.gif?a8mat=4BGS18+3F8X6A+56AO+5YJRM",
    providerLabel: "訳あり物件・空き家専門買取（ラクウル）",
    buttonText: "訳あり物件の専門店【ラクウル】",
  },
  /** 2. 実家・相続不動産の売却相談（相続の窓口） */
  sell: {
    url: "https://px.a8.net/svt/ejp?a8mat=4BGS18+3PDAGI+56AO+BWVTE",
    impPixel: "https://www11.a8.net/0.gif?a8mat=4BGS18+3PDAGI+56AO+BWVTE",
    providerLabel: "相続不動産の売却相談（相続の窓口）",
    buttonText: "相続の面倒ごとをワンストップで解決【相続の窓口】",
  },
  /** 3. 解体工事・遺品整理一括見積もり（提携待ち） */
  kaitai: {
    url: "",
    impPixel: "",
    providerLabel: "解体工事・空き家撤去一括見積もり",
    buttonText: "地域の解体業者で見積もりを比較する",
  },
  /** 4. 墓じまい・永代供養・葬儀資料請求（【ミキワ】墓じまい資料請求 等） */
  kuyo: {
    url: "//af.moshimo.com/af/c/click?a_id=5918328&p_id=1672&pc_id=3119&pl_id=90825",
    impPixel: "//i.moshimo.com/af/i/impression?a_id=5918328&p_id=1672&pc_id=3119&pl_id=90825",
    providerLabel: "墓じまい資料請求（ミキワ）",
    buttonText: "墓じまいの費用・手順の資料を請求する →",
    useAttributionSrc: true,
  },
  /** 5. 相続登記・名義変更・相続手続き相談（相続手続きの「nocos」） */
  sozoku: {
    url: "https://px.a8.net/svt/ejp?a8mat=4BGS18+3SXW36+5N2A+5YZ76",
    impPixel: "https://www14.a8.net/0.gif?a8mat=4BGS18+3SXW36+5N2A+5YZ76",
    providerLabel: "相続登記・手続き相談（nocos）",
    buttonText: "相続専門の司法書士が100名以上！【nocos-ノコス】",
  },
};

export function getAffiliate(slot: AffiliateSlot): AffiliateEntry {
  return AFFILIATE_LINKS[slot];
}
