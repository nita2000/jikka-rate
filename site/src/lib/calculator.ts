/**
 * 2026年最新税制・改正空家等対策特措法に準拠したクライアント／SSG共通計算ヘルパー。
 */
import taxRules from "../data/tax_rules.json";

export function calcBrokerageFeeYen(salePriceYen: number): number {
  if (salePriceYen <= 0) return 0;
  const rules = taxRules.sale_and_kaitori_rules;
  if (salePriceYen <= rules.low_price_threshold_yen) {
    return Math.min(rules.low_price_brokerage_max_yen, Math.round(salePriceYen * 0.15));
  }
  const exTax = salePriceYen * rules.brokerage_fee_rate + rules.brokerage_fee_fixed_yen;
  return Math.round(exTax * (1 + rules.consumption_tax_rate));
}
