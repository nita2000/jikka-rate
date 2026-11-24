"""2026年最新税制・改正空家特措法・解体単価・墓じまい基準に準拠した実家じまい損益計算エンジン。"""

from __future__ import annotations

from typing import Any


def calc_brokerage_fee(sale_price_yen: int, tax_rules: dict[str, Any]) -> int:
    """不動産売買の仲介手数料（税込・2024年7月改正の800万円以下33万円上限特例反映）を計算する。"""
    if sale_price_yen <= 0:
        return 0
    rules = tax_rules["sale_and_kaitori_rules"]
    if sale_price_yen <= int(rules["low_price_threshold_yen"]):
        # 空き家等の低廉な空家等の媒介特例（800万円以下は最大33万円税込、ただし超低額時は物件価格の15%を上限目安）
        return min(int(rules["low_price_brokerage_max_yen"]), round(sale_price_yen * 0.15))
    fee_ex_tax = sale_price_yen * float(rules["brokerage_fee_rate"]) + int(rules["brokerage_fee_fixed_yen"])
    return round(fee_ex_tax * (1.0 + float(rules["consumption_tax_rate"])))


def calc_property_tax(
    land_tsubo: float,
    floor_tsubo: float,
    structure: str,
    building_age_years: int,
    land_price_man_per_tsubo: float,
    tax_rules: dict[str, Any],
    market_demand_factor: float = 1.0,
    include_city_tax: bool = True,
) -> dict[str, Any]:
    """土地・建物の固定資産税・都市計画税と、管理不全空き家等の特例解除（実効4.2倍・本則6倍）インパクトを計算する。"""
    if structure == "grave" or (land_tsubo <= 0 and floor_tsubo <= 0):
        return {
            "land_sqm": 0.0,
            "land_market_yen": 0,
            "land_assessed_yen": 0,
            "bldg_assessed_yen": 0,
            "normal_land_tax_annual": 0,
            "normal_bldg_tax_annual": 0,
            "normal_total_tax_annual": 0,
            "heavy_effective_land_tax_annual": 0,
            "heavy_effective_total_tax_annual": 0,
            "heavy_principle_total_tax_annual": 0,
            "sarachi_total_tax_annual": 0,
            "extra_tax_annual_effective": 0,
            "extra_tax_5y_effective": 0,
            "extra_tax_10y_effective": 0,
            "land_tax_multiplier_effective": 1.0,
            "land_tax_multiplier_principle": 1.0,
        }

    pt = tax_rules["property_tax_rules"]
    fixed_rate = float(pt["fixed_asset_tax_rate"])
    city_rate = float(pt["city_planning_tax_rate"]) if include_city_tax else 0.0

    land_sqm = round(land_tsubo * 3.305785, 1)
    land_market_yen = round(land_tsubo * land_price_man_per_tsubo * 10000 * max(0.08, min(1.3, market_demand_factor)))
    land_assessed_yen = round(land_market_yen * float(pt["market_to_assessed_land_ratio"]))

    # 小規模住宅用地（200㎡以下：固定1/6・都市計画1/3）と一般住宅用地（200㎡超：固定1/3・都市計画2/3）
    small_limit = float(pt["small_residential_limit_sqm"])
    small_ratio = min(1.0, small_limit / max(1.0, land_sqm))
    general_ratio = max(0.0, 1.0 - small_ratio)

    fixed_tokurei_base = land_assessed_yen * (
        small_ratio * float(pt["small_residential_fixed_factor"])
        + general_ratio * float(pt["general_residential_fixed_factor"])
    )
    city_tokurei_base = land_assessed_yen * (
        small_ratio * float(pt["small_residential_city_factor"])
        + general_ratio * float(pt["general_residential_city_factor"])
    )
    normal_land_tax = round(fixed_tokurei_base * fixed_rate + city_tokurei_base * city_rate)

    # 特例解除時（管理不全空き家勧告・特定空き家勧告・または解体更地化）
    # 実務上は商業地等と同じ負担調整措置（評価額の70%上限）が適用されるため固定資産税は 0.70 / (1/6) = 4.2倍
    cap_factor = float(pt["non_residential_burden_cap_factor"])
    heavy_effective_land_tax = round(land_assessed_yen * cap_factor * (fixed_rate + city_rate))
    heavy_principle_land_tax = round(land_assessed_yen * 1.0 * (fixed_rate + city_rate))

    # 建物の固定資産税評価額（経年減点補正率反映）
    bldg_base_man = float(pt["building_assessed_base_man_per_tsubo"].get(structure, 28.0))
    dep_map = pt["building_age_depreciation"]
    if building_age_years >= 40:
        dep = float(dep_map["age_40_plus"])
    elif building_age_years >= 30:
        dep = float(dep_map["age_30"])
    else:
        dep = float(dep_map["age_20"])
    # 木造は築35年超でさらに評価減が進む実態を反映
    if structure == "wood" and building_age_years >= 35:
        dep *= 0.65

    bldg_assessed_yen = round(floor_tsubo * bldg_base_man * 10000 * dep)
    normal_bldg_tax = round(bldg_assessed_yen * (fixed_rate + city_rate))

    normal_total = normal_land_tax + normal_bldg_tax
    heavy_effective_total = heavy_effective_land_tax + normal_bldg_tax
    heavy_principle_total = heavy_principle_land_tax + normal_bldg_tax
    sarachi_total = heavy_effective_land_tax

    extra_annual = max(0, heavy_effective_total - normal_total)
    mult_eff = round(heavy_effective_land_tax / max(1, normal_land_tax), 2)
    mult_prin = round(heavy_principle_land_tax / max(1, normal_land_tax), 2)

    return {
        "land_sqm": land_sqm,
        "land_market_yen": land_market_yen,
        "land_assessed_yen": land_assessed_yen,
        "bldg_assessed_yen": bldg_assessed_yen,
        "normal_land_tax_annual": normal_land_tax,
        "normal_bldg_tax_annual": normal_bldg_tax,
        "normal_total_tax_annual": normal_total,
        "heavy_effective_land_tax_annual": heavy_effective_land_tax,
        "heavy_effective_total_tax_annual": heavy_effective_total,
        "heavy_principle_total_tax_annual": heavy_principle_total,
        "sarachi_total_tax_annual": sarachi_total,
        "extra_tax_annual_effective": extra_annual,
        "extra_tax_5y_effective": extra_annual * 5,
        "extra_tax_10y_effective": extra_annual * 10,
        "land_tax_multiplier_effective": mult_eff,
        "land_tax_multiplier_principle": mult_prin,
    }


def calc_demolition_cost(
    floor_tsubo: float,
    structure: str,
    road_condition: str,
    residual_level: str,
    has_asbestos_risk: bool,
    unit_prices: dict[str, float],
    tax_rules: dict[str, Any],
    is_hiraya: bool = False,
) -> dict[str, Any]:
    """建物構造・延床坪数・道路条件・残置物・アスベスト有無から解体工事総額と内訳を算出する。"""
    if structure == "grave" or floor_tsubo <= 0:
        return {
            "unit_price_man_per_tsubo": 0.0,
            "building_body_yen": 0,
            "road_surcharge_yen": 0,
            "exterior_fence_yen": 0,
            "residual_items_yen": 0,
            "asbestos_yen": 0,
            "total_demolition_yen": 0,
        }

    rules = tax_rules["demolition_base_rules"]
    if structure == "rc":
        base_man = float(unit_prices["rc_man_per_tsubo"])
    elif structure == "steel":
        base_man = float(unit_prices["steel_man_per_tsubo"])
    else:
        base_man = float(unit_prices["wood_man_per_tsubo"])

    if is_hiraya:
        base_man = round(base_man * 1.12, 2)

    body_yen = round(floor_tsubo * base_man * 10000)

    if road_condition == "slope":
        mult = float(rules["slope_land_multiplier"])
    elif road_condition == "narrow":
        mult = float(rules["narrow_road_multiplier"])
    else:
        mult = 1.0

    road_surcharge_yen = round(body_yen * (mult - 1.0))
    exterior_yen = int(rules["exterior_fence_tree_base_yen"])
    if floor_tsubo >= 45:
        exterior_yen = round(exterior_yen * 1.45)

    residual_map = rules["residual_items_cost_yen"]
    residual_yen = int(residual_map.get(residual_level, residual_map["normal"]))
    asbestos_yen = int(rules["asbestos_level3_survey_and_removal_yen"]) if has_asbestos_risk else 0

    total_yen = body_yen + road_surcharge_yen + exterior_yen + residual_yen + asbestos_yen
    return {
        "unit_price_man_per_tsubo": base_man,
        "building_body_yen": body_yen,
        "road_surcharge_yen": road_surcharge_yen,
        "exterior_fence_yen": exterior_yen,
        "residual_items_yen": residual_yen,
        "asbestos_yen": asbestos_yen,
        "total_demolition_yen": total_yen,
    }


def calc_hakajimai_cost(
    grave_sqm: float,
    grave_removal_factor: float,
    road_condition: str,
    is_temple_danka: bool,
    annual_keep_cost_yen: int,
    next_kuyo_type: str,
    funeral_grant_yen: int,
    tax_rules: dict[str, Any],
    years: int = 15,
) -> dict[str, Any]:
    """墓じまい（墓石撤去＋閉眼供養・離檀＋永代供養/樹木葬/納骨堂）の費用内訳と15年損益分岐を計算する。"""
    rules = tax_rules["hakajimai_base_rules"]
    slope_mult = 1.28 if road_condition in ("slope", "narrow") else 1.0
    stone_removal_yen = round(grave_sqm * int(rules["stone_removal_yen_per_sqm"]) * grave_removal_factor * slope_mult)

    ceremony_yen = int(rules["closing_ceremony_ofuse_yen"])
    ridan_yen = int(rules["ridan_fee_standard_yen"]) if is_temple_danka else 0
    admin_yen = int(rules["admin_permit_fee_yen"])

    kuyo_opts = rules["next_kuyo_options"]
    next_opt = kuyo_opts.get(next_kuyo_type, kuyo_opts["jumokusou"])
    next_initial_yen = int(next_opt["initial_cost_yen"])
    next_annual_yen = int(next_opt["annual_fee_yen"])

    initial_total_yen = stone_removal_yen + ceremony_yen + ridan_yen + admin_yen + next_initial_yen
    keep_total_15y = annual_keep_cost_yen * years
    hakajimai_total_15y = initial_total_yen + next_annual_yen * years
    saving_15y = keep_total_15y - hakajimai_total_15y

    annual_diff = max(1, annual_keep_cost_yen - next_annual_yen)
    payback_years = round(initial_total_yen / annual_diff, 1)

    return {
        "stone_removal_yen": stone_removal_yen,
        "ceremony_and_ridan_yen": ceremony_yen + ridan_yen,
        "admin_permit_yen": admin_yen,
        "next_kuyo_label": next_opt["label"],
        "next_kuyo_initial_yen": next_initial_yen,
        "next_kuyo_annual_yen": next_annual_yen,
        "initial_total_yen": initial_total_yen,
        "annual_keep_cost_yen": annual_keep_cost_yen,
        "keep_total_15y_yen": keep_total_15y,
        "hakajimai_total_15y_yen": hakajimai_total_15y,
        "saving_15y_yen": saving_15y,
        "payback_years": payback_years,
        "funeral_grant_yen": funeral_grant_yen,
        "net_initial_after_grant_yen": max(0, initial_total_yen - funeral_grant_yen),
    }


def calc_case_comprehensive(
    case: dict[str, Any],
    unit_prices: dict[str, float],
    land_price_man_per_tsubo: float,
    tax_rules: dict[str, Any],
    grave_removal_factor: float = 1.0,
    funeral_grant_yen: int = 50000,
) -> dict[str, Any]:
    """物件・お墓ケース1件の維持費・解体費・6倍重課・売却/買取手残り・10年キャッシュフローを一括計算する。"""
    is_grave_only = case["structure"] == "grave"
    has_grave = float(case.get("grave_sqm", 0)) > 0

    tax_info = calc_property_tax(
        land_tsubo=float(case["land_tsubo"]),
        floor_tsubo=float(case["floor_tsubo"]),
        structure=case["structure"],
        building_age_years=int(case["building_age_years"]),
        land_price_man_per_tsubo=land_price_man_per_tsubo,
        tax_rules=tax_rules,
        market_demand_factor=float(case.get("market_demand_factor", 1.0)),
    )

    is_hiraya = "hiraya" in case["slug"]
    demo_info = calc_demolition_cost(
        floor_tsubo=float(case["floor_tsubo"]),
        structure=case["structure"],
        road_condition=case["road_condition"],
        residual_level=case["residual_level"],
        has_asbestos_risk=bool(case["has_asbestos_risk"]),
        unit_prices=unit_prices,
        tax_rules=tax_rules,
        is_hiraya=is_hiraya,
    )
    if case["slug"] == "old-mansion-70sqm-age42":
        # 区分マンションは戸別解体が不要、残置物整理のみ
        demo_info = {
            "unit_price_man_per_tsubo": 0.0,
            "building_body_yen": 0,
            "road_surcharge_yen": 0,
            "exterior_fence_yen": 0,
            "residual_items_yen": 220000,
            "asbestos_yen": 0,
            "total_demolition_yen": 220000,
        }

    maint_rules = tax_rules["akiya_maintenance_rules"]
    if is_grave_only:
        base_maint_annual = int(case.get("annual_extra_maint_yen", 88000))
    elif case["slug"] == "old-mansion-70sqm-age42":
        base_maint_annual = int(case.get("annual_extra_maint_yen", 336000)) + 24000
    else:
        base_maint_annual = (
            int(maint_rules["annual_utility_base_yen"])
            + int(maint_rules["annual_insurance_fire_yen"])
            + int(maint_rules["annual_cleaning_yard_yen"])
            + int(maint_rules["annual_travel_inspection_yen"])
            + int(maint_rules["annual_aging_repair_reserve_yen"])
            + int(case.get("annual_extra_maint_yen", 0))
        )

    annual_keep_normal = tax_info["normal_total_tax_annual"] + base_maint_annual
    annual_keep_heavy = tax_info["heavy_effective_total_tax_annual"] + base_maint_annual
    keep_5y_normal = annual_keep_normal * 5
    keep_10y_normal = annual_keep_normal * 10
    keep_10y_heavy = annual_keep_normal * 2 + annual_keep_heavy * 8  # 3年目から管理不全勧告想定

    # 売却・買取シナリオ計算
    land_market = tax_info["land_market_yen"]
    if case["slug"] == "old-mansion-70sqm-age42":
        land_market = round(12800000 * (land_price_man_per_tsubo / 24.5) ** 0.55)

    # シナリオ1：解体して更地仲介売却
    if case["slug"] in ("non-rebuildable-wood-25tsubo", "urban-control-area-38tsubo"):
        # 再建築不可・市街化調整区域を誤って解体すると再建築制限で土地価値が大きく下落
        sarachi_gross_sale = round(land_market * 0.38)
    elif case["slug"] == "leased-land-shakuchi-28tsubo":
        # 借地権を自費解体して地主へ無償返還すると売却収入0円
        sarachi_gross_sale = 0
    else:
        sarachi_gross_sale = land_market

    sarachi_broker_fee = calc_brokerage_fee(sarachi_gross_sale, tax_rules)
    # 更地にしてから売れるまでの1年分の更地固定資産税を加味
    sarachi_net_proceeds = sarachi_gross_sale - demo_info["total_demolition_yen"] - sarachi_broker_fee - tax_info["sarachi_total_tax_annual"]

    # シナリオ2：古家付き仲介売却（買主側での解体見込み値引き82%反映＋売主の残置物片付け）
    if case["slug"] == "old-mansion-70sqm-age42":
        furuya_gross_sale = round(land_market * 0.94)
    elif case["building_age_years"] <= 32 and case["category"] in ("wood_standard", "steel_rc"):
        # 築30年前後の新耐震・軽量鉄骨等は中古戸建てとして建物プラス評価
        furuya_gross_sale = round(land_market * 1.05 + 1800000)
    else:
        furuya_gross_sale = round(land_market * 0.96 - demo_info["total_demolition_yen"] * 0.82)
    furuya_gross_sale = max(0, furuya_gross_sale)
    furuya_broker_fee = calc_brokerage_fee(furuya_gross_sale, tax_rules)
    furuya_net_proceeds = furuya_gross_sale - furuya_broker_fee - demo_info["residual_items_yen"]

    # シナリオ3：解体せず・残置物そのまま専門買取（仲介手数料0円・残置物撤去0円・即現金化）
    kaitori_rules = tax_rules["sale_and_kaitori_rules"]
    kaitori_gross = round(
        land_market * float(kaitori_rules["kaitori_land_discount_factor"])
        - demo_info["total_demolition_yen"] * float(kaitori_rules["kaitori_demolition_deduction_factor"]) * 0.55
    )
    if case["category"] == "wakeari":
        # 訳あり・再建築不可・借地権・残置物大量は専門買取業者が再生ノウハウを持つため最低買取保証ラインを維持
        kaitori_gross = max(kaitori_gross, round(land_market * 0.52), 800000)
    else:
        kaitori_gross = max(kaitori_gross, round(land_market * 0.42), 500000)
    kaitori_net_proceeds = kaitori_gross  # 直接買取のため仲介手数料・解体費・残置物費すべて0円

    # 墓じまい計算（お墓または実家＋墓セット）
    is_temple = "public-cemetery" not in case["slug"] and "private-cemetery" not in case["slug"] and "community" not in case["slug"]
    hakajimai_info = None
    if has_grave:
        hakajimai_info = calc_hakajimai_cost(
            grave_sqm=float(case["grave_sqm"]),
            grave_removal_factor=grave_removal_factor,
            road_condition=case["road_condition"],
            is_temple_danka=is_temple,
            annual_keep_cost_yen=int(case.get("annual_extra_maint_yen", 88000)),
            next_kuyo_type="jumokusou",
            funeral_grant_yen=funeral_grant_yen,
            tax_rules=tax_rules,
            years=15,
        )
        if case["slug"] == "jikka-and-grave-bundle-30tsubo":
            furuya_net_proceeds -= hakajimai_info["initial_total_yen"]
            sarachi_net_proceeds -= hakajimai_info["initial_total_yen"]
            kaitori_net_proceeds -= hakajimai_info["initial_total_yen"]

    # 10年間キャッシュフロー推移（放置維持した場合の累積流出：3年目から管理不全重課または修繕発生を可視化）
    ten_year_curve = []
    cum = 0
    for yr in range(1, 11):
        if is_grave_only and hakajimai_info:
            event_hit = yr in (3, 7, 10)
            yr_cost = hakajimai_info["annual_keep_cost_yen"] + (35000 if event_hit else 0)
            event_label = "年忌法要・お布施＋遠方帰省" if event_hit else "年間管理料・お墓参り帰省"
        else:
            heavy_hit = yr >= 3
            repair_hit = yr in (4, 8)
            tax_part = tax_info["heavy_effective_total_tax_annual"] if heavy_hit else tax_info["normal_total_tax_annual"]
            repair_part = 180000 if repair_hit else 0
            yr_cost = tax_part + base_maint_annual + repair_part
            if repair_hit:
                event_label = "固定資産税の軽減解除 ＋ 屋根・外壁の応急修繕"
            elif heavy_hit:
                event_label = "管理不全空き家の勧告後（住宅用地の軽減解除）"
            else:
                event_label = "通常の空き家維持（住宅用地の軽減1/6適用）"
        cum += yr_cost
        ten_year_curve.append(
            {
                "year": yr,
                "year_cost": yr_cost,
                "cumulative": cum,
                "is_alert_year": yr >= 3,
                "event_label": event_label,
            }
        )

    # 最適戦略の判定（カード上で途切れない端正なラベル）
    best_sale_net = max(sarachi_net_proceeds, furuya_net_proceeds, kaitori_net_proceeds)
    if case["slug"] == "old-mansion-70sqm-age42":
        if kaitori_net_proceeds >= sarachi_net_proceeds and kaitori_net_proceeds >= furuya_net_proceeds:
            best_strategy_label = "片付け不要の専門買取"
        else:
            best_strategy_label = "管理費がかさむ前に仲介売却"
    elif kaitori_net_proceeds >= sarachi_net_proceeds and kaitori_net_proceeds >= furuya_net_proceeds:
        best_strategy_label = "壊さず・片付けず専門買取"
    elif furuya_net_proceeds >= sarachi_net_proceeds:
        best_strategy_label = "壊さず古家付きで仲介売却"
    else:
        best_strategy_label = "解体して更地で仲介売却"

    return {
        "tax": tax_info,
        "demolition": demo_info,
        "maintenance": {
            "base_maint_annual": base_maint_annual,
            "annual_keep_normal": annual_keep_normal,
            "annual_keep_monthly": round(annual_keep_normal / 12),
            "annual_keep_heavy": annual_keep_heavy,
            "keep_5y_normal": keep_5y_normal,
            "keep_10y_normal": keep_10y_normal,
            "keep_10y_heavy": keep_10y_heavy,
        },
        "disposal": {
            "land_market_yen": land_market,
            "sarachi_gross_sale_yen": sarachi_gross_sale,
            "sarachi_broker_fee_yen": sarachi_broker_fee,
            "sarachi_net_proceeds_yen": sarachi_net_proceeds,
            "furuya_gross_sale_yen": furuya_gross_sale,
            "furuya_broker_fee_yen": furuya_broker_fee,
            "furuya_net_proceeds_yen": furuya_net_proceeds,
            "kaitori_net_proceeds_yen": kaitori_net_proceeds,
            "best_sale_net_yen": best_sale_net,
            "best_strategy_label": best_strategy_label,
            "net_benefit_vs_10y_keep_yen": best_sale_net + keep_10y_heavy,
        },
        "hakajimai": hakajimai_info,
        "ten_year_curve": ten_year_curve,
    }


def evaluate_strategy_metrics(
    case_enriched: dict[str, Any],
    strategy: str,
    tax_rules: dict[str, Any],
) -> dict[str, Any]:
    """比較ペア用に、特定ケース×戦略の『初期手出し』『5年累計負担（または純収支）』『10年/15年累計負担』を返す。

    ※正の値は『累積コスト（支出）』、負の値は『手残りプラス（売却純収入がコストを上回る状態）』として統一比較する。
    """
    c = case_enriched["calc"]
    tax = c["tax"]
    demo = c["demolition"]
    maint = c["maintenance"]
    disp = c["disposal"]
    haka = c["hakajimai"]

    if strategy == "keep_normal":
        return {
            "initial_outlay_yen": 0,
            "annual_ongoing_yen": maint["annual_keep_normal"],
            "cost_5y_yen": maint["keep_5y_normal"],
            "cost_10y_yen": maint["keep_10y_normal"],
            "net_cash_5y_yen": -maint["keep_5y_normal"],
            "net_cash_10y_yen": -maint["keep_10y_normal"],
            "short_winner": "通常維持",
            "note": f"年間維持費 {maint['annual_keep_normal']:,}円（固定資産税＋維持管理）が毎年発生",
        }

    if strategy == "keep_6x_heavy":
        cost_5y = maint["annual_keep_normal"] * 1 + maint["annual_keep_heavy"] * 4
        cost_10y = maint["annual_keep_normal"] * 1 + maint["annual_keep_heavy"] * 9
        return {
            "initial_outlay_yen": 0,
            "annual_ongoing_yen": maint["annual_keep_heavy"],
            "cost_5y_yen": cost_5y,
            "cost_10y_yen": cost_10y,
            "net_cash_5y_yen": -cost_5y,
            "net_cash_10y_yen": -cost_10y,
            "short_winner": "軽減解除での維持",
            "note": f"軽減解除後の年間負担 {maint['annual_keep_heavy']:,}円（土地の固定資産税が実効約{tax['land_tax_multiplier_effective']}倍）",
        }

    if strategy == "sarachi_sale":
        initial_outlay = demo["total_demolition_yen"]
        net_proceeds = disp["sarachi_net_proceeds_yen"]
        return {
            "initial_outlay_yen": initial_outlay,
            "annual_ongoing_yen": 0,
            "cost_5y_yen": max(0, -net_proceeds),
            "cost_10y_yen": max(0, -net_proceeds),
            "net_cash_5y_yen": net_proceeds,
            "net_cash_10y_yen": net_proceeds,
            "short_winner": f"{case_enriched['short_name']}の解体売却",
            "note": f"解体費 {initial_outlay:,}円を先行支出 → 売却後の最終手残り {net_proceeds:+,}円",
        }

    if strategy == "furuya_broker":
        initial_outlay = demo["residual_items_yen"]
        net_proceeds = disp["furuya_net_proceeds_yen"]
        return {
            "initial_outlay_yen": initial_outlay,
            "annual_ongoing_yen": 0,
            "cost_5y_yen": max(0, -net_proceeds),
            "cost_10y_yen": max(0, -net_proceeds),
            "net_cash_5y_yen": net_proceeds,
            "net_cash_10y_yen": net_proceeds,
            "short_winner": "実家＋墓じまい一括" if case_enriched["slug"] == "jikka-and-grave-bundle-30tsubo" else ("早期の仲介売却" if case_enriched["slug"] == "old-mansion-70sqm-age42" else "古家付き仲介売却"),
            "note": f"解体せず仲介売却 → 売却後の最終手残り {net_proceeds:+,}円",
        }

    if strategy == "buyer_demolition_3000man":
        # 2024年改正：古家付きで譲渡し買主が翌年2月15日までに解体して3,000万円特別控除を適用
        net_proceeds = disp["furuya_net_proceeds_yen"] + round(tax["sarachi_total_tax_annual"] * 0.8)
        return {
            "initial_outlay_yen": demo["residual_items_yen"],
            "annual_ongoing_yen": 0,
            "cost_5y_yen": max(0, -net_proceeds),
            "cost_10y_yen": max(0, -net_proceeds),
            "net_cash_5y_yen": net_proceeds,
            "net_cash_10y_yen": net_proceeds,
            "short_winner": "古家付き売却（買主解体）",
            "note": f"先行解体ゼロで3,000万円控除適用 → 最終手残り {net_proceeds:+,}円",
        }

    if strategy == "direct_kaitori":
        net_proceeds = disp["kaitori_net_proceeds_yen"]
        return {
            "initial_outlay_yen": 0,
            "annual_ongoing_yen": 0,
            "cost_5y_yen": max(0, -net_proceeds),
            "cost_10y_yen": max(0, -net_proceeds),
            "net_cash_5y_yen": net_proceeds,
            "net_cash_10y_yen": net_proceeds,
            "short_winner": "壊さず専門買取",
            "note": f"解体費0円・残置物片付け0円・仲介手数料0円で即現金化 → 手残り {net_proceeds:+,}円",
        }

    # 墓じまい系戦略
    grave_sqm = float(case_enriched.get("grave_sqm", 2.0)) or 2.0
    is_temple = "public-cemetery" not in case_enriched["slug"]
    annual_grave_keep = int(case_enriched.get("annual_extra_maint_yen", 98000))

    if strategy == "grave_keep":
        c5 = annual_grave_keep * 5
        c15 = annual_grave_keep * 15
        return {
            "initial_outlay_yen": 0,
            "annual_ongoing_yen": annual_grave_keep,
            "cost_5y_yen": c5,
            "cost_10y_yen": c15,
            "net_cash_5y_yen": -c5,
            "net_cash_10y_yen": -c15,
            "short_winner": "遠方の墓を維持",
            "note": f"年間 {annual_grave_keep:,}円（管理料＋お布施＋帰省交通費）×15年＝{c15:,}円の維持負担",
        }

    kuyo_key = "jumokusou"
    if strategy == "hakajimai_goshi":
        kuyo_key = "goshi"
    elif strategy == "hakajimai_nokotsudo":
        kuyo_key = "nokotsudo"

    hk = calc_hakajimai_cost(
        grave_sqm=grave_sqm,
        grave_removal_factor=1.0,
        road_condition=case_enriched["road_condition"],
        is_temple_danka=is_temple,
        annual_keep_cost_yen=annual_grave_keep,
        next_kuyo_type=kuyo_key,
        funeral_grant_yen=50000,
        tax_rules=tax_rules,
        years=15,
    )
    c5 = hk["initial_total_yen"] + hk["next_kuyo_annual_yen"] * 5
    c15 = hk["hakajimai_total_15y_yen"]
    return {
        "initial_outlay_yen": hk["initial_total_yen"],
        "annual_ongoing_yen": hk["next_kuyo_annual_yen"],
        "cost_5y_yen": c5,
        "cost_10y_yen": c15,
        "net_cash_5y_yen": -c5,
        "net_cash_10y_yen": -c15,
        "payback_years": hk["payback_years"],
        "note": f"初期総額 {hk['initial_total_yen']:,}円（{hk['next_kuyo_label']}）→ 約{hk['payback_years']}年で回収",
    }
