"""実家と空き家の試算表 データパイプラインおよび2026年最新税制・解体・墓じまい計算エンジンの自動テスト。"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

PIPELINE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PIPELINE_DIR))

from cost_calculator import (  # noqa: E402
    calc_brokerage_fee,
    calc_case_comprehensive,
    calc_demolition_cost,
    calc_hakajimai_cost,
    calc_property_tax,
)
from fetch_jikka_stats import load_masters, validate_stat_records  # noqa: E402


class CostCalculatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.prefectures, cls.tax_rules = load_masters()
        cls.cases = json.loads(
            (PIPELINE_DIR.parent / "data" / "masters" / "property_cases.json").read_text(encoding="utf-8")
        )

    def test_property_tax_6x_and_effective_multiplier(self) -> None:
        # 敷地45坪（約148.8㎡ <= 200㎡小規模住宅用地）：
        # 固定資産税のみ(include_city_tax=False)なら特例1/6 -> 解除後負担調整上限70%でちょうど4.2倍（本則比6.0倍）
        res_fixed_only = calc_property_tax(
            land_tsubo=45.0,
            floor_tsubo=30.0,
            structure="wood",
            building_age_years=40,
            land_price_man_per_tsubo=24.5,
            tax_rules=self.tax_rules,
            include_city_tax=False,
        )
        self.assertAlmostEqual(res_fixed_only["land_tax_multiplier_effective"], 4.2, places=1)
        self.assertAlmostEqual(res_fixed_only["land_tax_multiplier_principle"], 6.0, places=1)
        self.assertGreater(res_fixed_only["extra_tax_5y_effective"], 150000)

    def test_general_residential_land_over_200sqm(self) -> None:
        # 200㎡超（例：150坪＝約495㎡）は一般住宅用地(1/3)が含まれるため倍率が小規模単独より緩やかになる
        res_large = calc_property_tax(
            land_tsubo=150.0,
            floor_tsubo=55.0,
            structure="wood",
            building_age_years=50,
            land_price_man_per_tsubo=15.0,
            tax_rules=self.tax_rules,
            include_city_tax=True,
        )
        self.assertGreater(res_large["land_sqm"], 200.0)
        self.assertGreater(res_large["heavy_effective_total_tax_annual"], res_large["normal_total_tax_annual"])

    def test_demolition_cost_structure_and_asbestos(self) -> None:
        unit_prices = {"wood_man_per_tsubo": 4.8, "steel_man_per_tsubo": 6.3, "rc_man_per_tsubo": 7.8}
        d_wood = calc_demolition_cost(30, "wood", "normal", "normal", False, unit_prices, self.tax_rules)
        d_wood_asb = calc_demolition_cost(30, "wood", "normal", "normal", True, unit_prices, self.tax_rules)
        d_rc = calc_demolition_cost(30, "rc", "normal", "normal", True, unit_prices, self.tax_rules)
        self.assertEqual(d_wood_asb["total_demolition_yen"] - d_wood["total_demolition_yen"], 240000)
        self.assertGreater(d_rc["total_demolition_yen"], d_wood_asb["total_demolition_yen"])

    def test_low_price_brokerage_fee_2024_rule(self) -> None:
        # 800万円以下の空き家等売買仲介手数料は最大33万円（税込）特例
        fee_500m = calc_brokerage_fee(5000000, self.tax_rules)
        self.assertEqual(fee_500m, 330000)
        fee_2000m = calc_brokerage_fee(20000000, self.tax_rules)
        self.assertEqual(fee_2000m, 726000)

    def test_hakajimai_15y_payback(self) -> None:
        res = calc_hakajimai_cost(
            grave_sqm=2.0,
            grave_removal_factor=1.0,
            road_condition="normal",
            is_temple_danka=True,
            annual_keep_cost_yen=98000,
            next_kuyo_type="goshi",
            funeral_grant_yen=50000,
            tax_rules=self.tax_rules,
            years=15,
        )
        self.assertGreater(res["saving_15y_yen"], 800000)
        self.assertLess(res["payback_years"], 6.0)

    def test_non_rebuildable_kaitori_beats_sarachi(self) -> None:
        # 再建築不可物件は解体更地化より建物を残した専門買取の方が手残りが必ず有利
        by_slug = {c["slug"]: c for c in self.cases}
        unit_prices = {"wood_man_per_tsubo": 4.8, "steel_man_per_tsubo": 6.3, "rc_man_per_tsubo": 7.8}
        c_res = calc_case_comprehensive(by_slug["non-rebuildable-wood-25tsubo"], unit_prices, 24.5, self.tax_rules)
        self.assertGreater(
            c_res["disposal"]["kaitori_net_proceeds_yen"],
            c_res["disposal"]["sarachi_net_proceeds_yen"],
        )

    def test_validation_rejects_outlier(self) -> None:
        bad = [
            {
                "date": "2026-11-01",
                "pref_code": "00",
                "pref_name": "全国",
                "wood_man_per_tsubo": 25.0,
                "steel_man_per_tsubo": 28.0,
                "rc_man_per_tsubo": 30.0,
                "repair_index": 120.0,
                "source": "official_excel",
            }
        ]
        with self.assertRaises(ValueError):
            validate_stat_records(bad)


class DatasetOutputTests(unittest.TestCase):
    def test_generated_site_datasets(self) -> None:
        data_dir = PIPELINE_DIR.parent / "site" / "src" / "data"
        self.assertTrue((data_dir / "meta.json").exists())
        prefectures = json.loads((data_dir / "prefectures.json").read_text(encoding="utf-8"))
        cases = json.loads((data_dir / "property_cases.json").read_text(encoding="utf-8"))
        pairs = json.loads((data_dir / "compare_pairs.json").read_text(encoding="utf-8"))
        self.assertEqual(len(prefectures), 47)
        self.assertEqual(len(cases), 40)
        self.assertEqual(len(pairs), 24)
        detail_files = list((data_dir / "pref_detail").glob("*.json"))
        self.assertEqual(len(detail_files), 47)

        # 地方農家住宅55坪は解体費用倒れとなるため専門買取が更地解体より有利になること
        by_case = {c["slug"]: c for c in cases}
        kominka_disp = by_case["kominka-farm-55tsubo-age60"]["calc"]["disposal"]
        self.assertGreater(
            kominka_disp["kaitori_net_proceeds_yen"],
            kominka_disp["sarachi_net_proceeds_yen"],
        )

        # 墓じまい同士の比較では回収年数(payback_years)がNoneになること
        by_pair = {p["slug"]: p for p in pairs}
        self.assertIsNone(by_pair["hakajimai-goshi-vs-jumokusou-vs-nokotsudo"]["payback_years"])
        self.assertIsNone(by_pair["public-cemetery-vs-temple-danka-hakajimai"]["payback_years"])
        self.assertIsNotNone(by_pair["temple-grave-keep-15y-vs-hakajimai-jumokusou"]["payback_years"])

        # 区分マンションの最適戦略ラベルに「解体」「更地」が混入しないこと
        mansion = by_case["old-mansion-70sqm-age42"]
        self.assertNotIn("更地", mansion["calc"]["disposal"]["best_strategy_label"])
        self.assertNotIn("解体", mansion["calc"]["disposal"]["best_strategy_label"])

        # 通常ケースの買取額が単純42%固定ではなく解体費控除の計算値を反映していること
        std_wood = by_case["wood-30tsubo-age40"]["calc"]["disposal"]
        self.assertGreater(std_wood["kaitori_net_proceeds_yen"], round(std_wood["land_market_yen"] * 0.42))

        # 比較ペアの論理整合（木造30坪 vs 軽量鉄骨32坪は木造が解体安、売主解体 vs 買主解体は買主解体が有利）
        self.assertEqual(by_pair["wood-30tsubo-vs-steel-32tsubo-demolition"]["winner_side"], "A")
        self.assertEqual(by_pair["seller-demolition-vs-buyer-demolition-3000man"]["winner_side"], "B")

    def test_dist_internal_links_if_built(self) -> None:
        import re

        dist_dir = PIPELINE_DIR.parent / "site" / "dist"
        if not dist_dir.exists():
            return
        html_files = list(dist_dir.rglob("*.html"))
        self.assertEqual(len(html_files), 132)
        for hf in html_files:
            text = hf.read_text(encoding="utf-8")
            for m in re.finditer(r'href="(/[^"#?]*)"', text):
                href = m.group(1)
                if href.startswith("//"):
                    continue
                target = dist_dir / href.lstrip("/")
                if target.is_dir() or not target.suffix:
                    target = target / "index.html"
                self.assertTrue(target.exists(), f"リンク切れ検知: {hf} -> {href}")


if __name__ == "__main__":
    unittest.main()
