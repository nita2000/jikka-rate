/**
 * アフィリエイト（収益化）リンクの一元管理モジュール。
 * A8.net等の規約に完全準拠（コード改変禁止・1pxインプレッション計測画像出力・GA4クリック計測対応）。
 * ASP提携後、各枠にクリックURL（url）と計測用1px画像URL（impPixel）を設定するだけで、
 * 全ページのCTAおよびシミュレーター結果連動型の動的CTAへ一斉反映されます。
 */
export type AffiliateSlot = "akiya" | "akiya_house" | "shakuchi" | "sell" | "kaitai" | "kuyo" | "sozoku";

export interface AffiliateEntry {
  url: string;
  impPixel: string;
  providerLabel: string;
  buttonText: string;
  microCopy: string;
  disclaimer: string;
  useAttributionSrc?: boolean;
}

export const AFFILIATE_LINKS: Record<AffiliateSlot, AffiliateEntry> = {
  /** 1. 訳あり物件専門買取（訳アリ不動産買取専門店【ラクウル】） */
  akiya: {
    url: "https://px.a8.net/svt/ejp?a8mat=4BGS18+3F8X6A+56AO+5YJRM",
    impPixel: "https://www16.a8.net/0.gif?a8mat=4BGS18+3F8X6A+56AO+5YJRM",
    providerLabel: "訳あり物件専門買取（ラクウル）",
    buttonText: "訳あり物件の専門店【ラクウル】",
    microCopy: "解体や片付けを始める前の段階で、現状のままの買取目安を確認できます。",
    disclaimer:
      "※実際の買取額は立地・接道条件・残置物や建物の状態により異なります。解体を発注する前の判断材料としてご活用ください。",
  },
  /** 1-b. 空き家・中古戸建て専門買取（空き家・中古戸建ての買取専門【ラクウル】） */
  akiya_house: {
    url: "https://px.a8.net/svt/ejp?a8mat=4BGS18+42GTRM+56AO+HV7V6",
    impPixel: "https://www15.a8.net/0.gif?a8mat=4BGS18+42GTRM+56AO+HV7V6",
    providerLabel: "空き家・中古戸建て専門買取（ラクウル）",
    buttonText: "空き家・中古戸建ての買取専門【ラクウル】",
    microCopy: "解体費や片付け費用をかける前に、空き家そのままの買取目安を確認できます。",
    disclaimer:
      "※実際の買取額は立地・築年数・敷地条件や残置物の量により異なります。解体を発注する前の判断材料としてご活用ください。",
  },
  /** 1-c. 借地権専門相談・買取（借地権 無料相談ドットコム） */
  shakuchi: {
    url: "https://px.a8.net/svt/ejp?a8mat=4BGS18+4MPKC2+5TEW+5YJRM",
    impPixel: "https://www14.a8.net/0.gif?a8mat=4BGS18+4MPKC2+5TEW+5YJRM",
    providerLabel: "借地権の売却・買取相談（借地権 無料相談ドットコム）",
    buttonText: "相談からワンストップで対応【借地権 無料相談ドットコム】",
    microCopy: "地主への承諾交渉や解体返還が必要になる前に、借地権付き建物のまま手放せるか相談できます。",
    disclaimer:
      "※借地権の評価や譲渡承諾料は契約内容・残存期間・地主との交渉条件により異なります。自費解体して更地返還する前に専門窓口へ確認するのが安全です。",
  },
  /** 2. 実家・相続不動産の売却相談（相続の窓口） */
  sell: {
    url: "https://px.a8.net/svt/ejp?a8mat=4BGS18+3PDAGI+56AO+BWVTE",
    impPixel: "https://www11.a8.net/0.gif?a8mat=4BGS18+3PDAGI+56AO+BWVTE",
    providerLabel: "相続不動産の売却相談（相続の窓口）",
    buttonText: "相続の面倒ごとをワンストップで解決【相続の窓口】",
    microCopy: "売却を決める前の段階でも、現状のままの相場確認や手続きの段取りを相談できます。",
    disclaimer:
      "※同じ都道府県内でも、前面道路の幅員・再建築の可否・近隣の成約事例により実勢価格は大きく変わります。解体や片付けの前に実額を確認しておくのが安全です。",
  },
  /** 3. 解体工事・遺品整理一括見積もり（提携待ち） */
  kaitai: {
    url: "",
    impPixel: "",
    providerLabel: "解体工事・空き家撤去一括見積もり",
    buttonText: "地域の解体業者で見積もりを比較する",
    microCopy: "明細の内訳を比較することで、外構撤去やアスベスト調査費の過不足を確認しやすくなります。",
    disclaimer:
      "※解体工事費は前面道路の幅員・地中埋設物・アスベスト事前調査の結果により変動します。着工前の自治体補助金とあわせて確認してください。",
  },
  /** 4. 墓じまい代行・相見積もり相談（墓じまいパートナーズ） */
  kuyo: {
    url: "//af.moshimo.com/af/c/click?a_id=5918327&p_id=7496&pc_id=21651&pl_id=93975",
    impPixel: "//i.moshimo.com/af/i/impression?a_id=5918327&p_id=7496&pc_id=21651&pl_id=93975",
    providerLabel: "墓じまい代行・相見積もり相談（墓じまいパートナーズ）",
    buttonText: "墓じまいの費用目安・代行手順を相談する →",
    microCopy: "離檀の段取り・行政手続き・石材撤去の見積もりまで、家族会議の前に全体費用を確認できます。",
    disclaimer:
      "※実際の墓じまい費用は区画の広さ・搬出経路・寺院や霊園の規約により異なります。撤去工事の前に全体の費用と手順を確認しておくと安心です。",
    useAttributionSrc: true,
  },
  /** 5. 相続登記・名義変更・相続手続き相談（相続手続きの「nocos」） */
  sozoku: {
    url: "https://px.a8.net/svt/ejp?a8mat=4BGS18+3SXW36+5N2A+5YZ76",
    impPixel: "https://www14.a8.net/0.gif?a8mat=4BGS18+3SXW36+5N2A+5YZ76",
    providerLabel: "相続登記・手続き相談（nocos）",
    buttonText: "相続専門の司法書士が100名以上！【nocos-ノコス】",
    microCopy: "名義変更や戸籍収集・遺産分割の段取りなど、期限前に必要な手続きを専門家へ相談できます。",
    disclaimer:
      "※相続登記や名義変更に必要な書類・手続き期間は、相続人の人数や過去の未登記の有無により異なります。",
  },
};

export function getAffiliate(slot: AffiliateSlot): AffiliateEntry {
  return AFFILIATE_LINKS[slot];
}
