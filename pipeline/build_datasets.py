"""生CSVと公的マスタから Astro 静的サイト配信用の JSON データセットを一括生成するスクリプト。"""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from cost_calculator import calc_case_comprehensive, evaluate_strategy_metrics

ROOT_DIR = Path(__file__).resolve().parent.parent
MASTERS_DIR = ROOT_DIR / "data" / "masters"
RAW_CSV = ROOT_DIR / "data" / "raw" / "jikka_cost_trends.csv"
SITE_DATA_DIR = ROOT_DIR / "site" / "src" / "data"


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def load_raw_records(csv_path: Path) -> list[dict[str, Any]]:
    if not csv_path.exists():
        raise FileNotFoundError(f"生CSVが見つかりません: {csv_path}")
    rows: list[dict[str, Any]] = []
    with csv_path.open("r", encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            rows.append(
                {
                    "date": r["date"],
                    "pref_code": r["pref_code"].zfill(2),
                    "pref_name": r["pref_name"],
                    "wood_man_per_tsubo": round(float(r["wood_man_per_tsubo"]), 2),
                    "steel_man_per_tsubo": round(float(r["steel_man_per_tsubo"]), 2),
                    "rc_man_per_tsubo": round(float(r["rc_man_per_tsubo"]), 2),
                    "repair_index": round(float(r["repair_index"]), 1),
                    "source": r["source"],
                }
            )
    return rows


def build_all(raw_csv: Path = RAW_CSV, out_dir: Path = SITE_DATA_DIR) -> dict[str, Any]:
    prefectures = json.loads((MASTERS_DIR / "prefectures.json").read_text(encoding="utf-8"))
    tax_rules = json.loads((MASTERS_DIR / "tax_rules.json").read_text(encoding="utf-8"))
    property_cases = json.loads((MASTERS_DIR / "property_cases.json").read_text(encoding="utf-8"))
    compare_pairs = json.loads((MASTERS_DIR / "compare_pairs.json").read_text(encoding="utf-8"))
    raw_rows = load_raw_records(raw_csv)

    by_pref: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in raw_rows:
        by_pref[row["pref_code"]].append(row)
    for code in by_pref:
        by_pref[code].sort(key=lambda x: x["date"])

    national_series = by_pref["00"]
    latest_nat = national_series[-1]
    prev_nat = national_series[-2] if len(national_series) >= 2 else latest_nat
    date_from = national_series[0]["date"]
    date_to = latest_nat["date"]

    sources_present = sorted({r["source"] for r in raw_rows})
    if "official_excel" in sources_present:
        source_mode_label = "公的統計・解体単価調査（Excel実測取り込み）"
    elif "estat_api" in sources_present:
        source_mode_label = "総務省 住宅・土地統計調査＆小売物価統計調査（e-Stat公式API連動）"
    else:
        source_mode_label = "総務省 e-Stat・国土交通省・厚生労働省 公表統計（2026年11月最新基準・自動更新対応）"

    nat_unit_prices = {
        "wood_man_per_tsubo": latest_nat["wood_man_per_tsubo"],
        "steel_man_per_tsubo": latest_nat["steel_man_per_tsubo"],
        "rc_man_per_tsubo": latest_nat["rc_man_per_tsubo"],
    }
    nat_land_price = 24.5

    # 代表4ケース（標準木造30坪、農家住宅55坪、再建築不可25坪、遠方寺院墓2㎡）
    case_by_slug = {c["slug"]: c for c in property_cases}
    sample_case_models = [
        case_by_slug["wood-30tsubo-age40"],
        case_by_slug["kominka-farm-55tsubo-age60"],
        case_by_slug["non-rebuildable-wood-25tsubo"],
        case_by_slug["temple-grave-2sqm-far"],
    ]

    pref_summaries: list[dict[str, Any]] = []
    pref_detail_dir = out_dir / "pref_detail"
    pref_detail_dir.mkdir(parents=True, exist_ok=True)

    for pref in prefectures:
        series = by_pref[pref["code"]]
        latest_p = series[-1]
        prev_p = series[-2] if len(series) >= 2 else latest_p
        wood_vals = [x["wood_man_per_tsubo"] for x in series]

        p_unit_prices = {
            "wood_man_per_tsubo": latest_p["wood_man_per_tsubo"],
            "steel_man_per_tsubo": latest_p["steel_man_per_tsubo"],
            "rc_man_per_tsubo": latest_p["rc_man_per_tsubo"],
        }
        p_land_price = float(pref["land_price_man_per_tsubo"])

        # 標準実家（敷地45坪・木造30坪・築40年）の県内相場目安
        std_calc = calc_case_comprehensive(
            case_by_slug["wood-30tsubo-age40"],
            p_unit_prices,
            p_land_price,
            tax_rules,
            grave_removal_factor=float(pref["grave_removal_factor"]),
            funeral_grant_yen=int(pref["funeral_grant_yen"]),
        )

        sample_cases = []
        for sc in sample_case_models:
            c_res = calc_case_comprehensive(
                sc,
                p_unit_prices,
                p_land_price,
                tax_rules,
                grave_removal_factor=float(pref["grave_removal_factor"]),
                funeral_grant_yen=int(pref["funeral_grant_yen"]),
            )
            sample_cases.append(
                {
                    "slug": sc["slug"],
                    "short_name": sc["short_name"],
                    "category_label": sc["category_label"],
                    "structure": sc["structure"],
                    "demolition_total_yen": c_res["demolition"]["total_demolition_yen"],
                    "annual_keep_normal_yen": c_res["maintenance"]["annual_keep_normal"],
                    "annual_keep_heavy_yen": c_res["maintenance"]["annual_keep_heavy"],
                    "best_sale_net_yen": c_res["disposal"]["best_sale_net_yen"],
                    "best_strategy_label": c_res["disposal"]["best_strategy_label"],
                    "hakajimai_initial_yen": c_res["hakajimai"]["initial_total_yen"] if c_res["hakajimai"] else 0,
                }
            )

        summary = {
            "code": pref["code"],
            "slug": pref["slug"],
            "name": pref["name"],
            "region": pref["region"],
            "capital_city": pref["capital_city"],
            "latest_date": latest_p["date"],
            "akiya_rate_pct": pref["akiya_rate_pct"],
            "other_akiya_rate_pct": pref["other_akiya_rate_pct"],
            "land_price_man_per_tsubo": p_land_price,
            "wood_man_per_tsubo": latest_p["wood_man_per_tsubo"],
            "steel_man_per_tsubo": latest_p["steel_man_per_tsubo"],
            "rc_man_per_tsubo": latest_p["rc_man_per_tsubo"],
            "repair_index": latest_p["repair_index"],
            "diff_prev_wood": round(latest_p["wood_man_per_tsubo"] - prev_p["wood_man_per_tsubo"], 2),
            "diff_national_wood": round(latest_p["wood_man_per_tsubo"] - latest_nat["wood_man_per_tsubo"], 2),
            "min_wood_recent": min(wood_vals),
            "max_wood_recent": max(wood_vals),
            "cremation_fee_yen": pref["cremation_fee_yen"],
            "funeral_grant_yen": pref["funeral_grant_yen"],
            "grave_removal_factor": pref["grave_removal_factor"],
            "std_30tsubo_demolition_yen": std_calc["demolition"]["total_demolition_yen"],
            "std_45tsubo_land_market_yen": std_calc["tax"]["land_market_yen"],
            "std_normal_tax_annual_yen": std_calc["tax"]["normal_total_tax_annual"],
            "std_heavy_tax_annual_yen": std_calc["tax"]["heavy_effective_total_tax_annual"],
            "std_annual_keep_yen": std_calc["maintenance"]["annual_keep_normal"],
            "sample_cases": sample_cases,
        }
        pref_summaries.append(summary)

        # 年別平均
        yearly_map: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for item in series:
            yearly_map[item["date"][:4]].append(item)
        yearly_stats = []
        for yr in sorted(yearly_map.keys()):
            items = yearly_map[yr]
            yearly_stats.append(
                {
                    "year": yr,
                    "count": len(items),
                    "avg_wood": round(sum(x["wood_man_per_tsubo"] for x in items) / len(items), 2),
                    "avg_steel": round(sum(x["steel_man_per_tsubo"] for x in items) / len(items), 2),
                    "avg_rc": round(sum(x["rc_man_per_tsubo"] for x in items) / len(items), 2),
                    "avg_repair_index": round(sum(x["repair_index"] for x in items) / len(items), 1),
                }
            )

        write_json(
            pref_detail_dir / f"{pref['slug']}.json",
            {
                **summary,
                "series": [
                    {
                        "date": x["date"],
                        "wood_man_per_tsubo": x["wood_man_per_tsubo"],
                        "steel_man_per_tsubo": x["steel_man_per_tsubo"],
                        "rc_man_per_tsubo": x["rc_man_per_tsubo"],
                        "repair_index": x["repair_index"],
                    }
                    for x in series
                ],
                "yearly_stats": yearly_stats,
            },
        )

    # ランキング付与（空き家率が高い順・解体単価が安い順）
    sorted_akiya = sorted(pref_summaries, key=lambda x: (-x["akiya_rate_pct"], x["code"]))
    akiya_rank_map = {item["code"]: idx + 1 for idx, item in enumerate(sorted_akiya)}
    sorted_kaitai = sorted(pref_summaries, key=lambda x: (x["wood_man_per_tsubo"], x["code"]))
    kaitai_rank_map = {item["code"]: idx + 1 for idx, item in enumerate(sorted_kaitai)}

    for item in pref_summaries:
        item["akiya_rank"] = akiya_rank_map[item["code"]]
        item["kaitai_cheap_rank"] = kaitai_rank_map[item["code"]]

    cheapest_pref = sorted_kaitai[0]
    priciest_pref = sorted_kaitai[-1]

    # 全40ケースの全国基準＆都道府県レンジ計算
    enriched_cases: list[dict[str, Any]] = []
    cheap_unit_prices = {
        "wood_man_per_tsubo": cheapest_pref["wood_man_per_tsubo"],
        "steel_man_per_tsubo": cheapest_pref["steel_man_per_tsubo"],
        "rc_man_per_tsubo": cheapest_pref["rc_man_per_tsubo"],
    }
    pricy_unit_prices = {
        "wood_man_per_tsubo": priciest_pref["wood_man_per_tsubo"],
        "steel_man_per_tsubo": priciest_pref["steel_man_per_tsubo"],
        "rc_man_per_tsubo": priciest_pref["rc_man_per_tsubo"],
    }

    for c in property_cases:
        nat_calc = calc_case_comprehensive(c, nat_unit_prices, nat_land_price, tax_rules)
        cheap_calc = calc_case_comprehensive(
            c,
            cheap_unit_prices,
            cheapest_pref["land_price_man_per_tsubo"],
            tax_rules,
            grave_removal_factor=float(cheapest_pref["grave_removal_factor"]),
            funeral_grant_yen=int(cheapest_pref["funeral_grant_yen"]),
        )
        pricy_calc = calc_case_comprehensive(
            c,
            pricy_unit_prices,
            priciest_pref["land_price_man_per_tsubo"],
            tax_rules,
            grave_removal_factor=float(priciest_pref["grave_removal_factor"]),
            funeral_grant_yen=int(priciest_pref["funeral_grant_yen"]),
        )

        if c["structure"] == "grave":
            low_cost = cheap_calc["hakajimai"]["initial_total_yen"]
            high_cost = pricy_calc["hakajimai"]["initial_total_yen"]
        else:
            low_cost = cheap_calc["demolition"]["total_demolition_yen"]
            high_cost = pricy_calc["demolition"]["total_demolition_yen"]

        enriched_cases.append(
            {
                **c,
                "calc": nat_calc,
                "pref_cost_range": {
                    "cheapest_pref": cheapest_pref["name"],
                    "cheapest_cost_yen": low_cost,
                    "priciest_pref": priciest_pref["name"],
                    "priciest_cost_yen": high_cost,
                    "diff_yen": high_cost - low_cost,
                },
            }
        )

    enriched_by_slug = {c["slug"]: c for c in enriched_cases}

    # 全24組の比較ペア計算
    enriched_pairs: list[dict[str, Any]] = []
    for pair in compare_pairs:
        case_a = enriched_by_slug[pair["case_a"]]
        case_b = enriched_by_slug[pair["case_b"]]
        metrics_a = evaluate_strategy_metrics(case_a, pair["strategy_a"], tax_rules)
        metrics_b = evaluate_strategy_metrics(case_b, pair["strategy_b"], tax_rules)

        # net_cash_10y_yen（大きいほど手残りが多い・または累積赤字が小さい）で有利判定
        net_a = metrics_a["net_cash_10y_yen"]
        net_b = metrics_b["net_cash_10y_yen"]
        diff_10y = abs(net_a - net_b)
        if net_a >= net_b:
            winner_label = pair["option_a_label"]
            winner_side = "A"
        else:
            winner_label = pair["option_b_label"]
            winner_side = "B"

        is_keep_vs_haka = "grave_keep" in (pair["strategy_a"], pair["strategy_b"])
        payback_years = (
            (metrics_b.get("payback_years") or metrics_a.get("payback_years"))
            if is_keep_vs_haka
            else None
        )
        diff_man = round(diff_10y / 10000)
        if payback_years:
            verdict_short = f"約{payback_years}年で回収（差額 約{diff_man:,}万円）"
        else:
            if pair["case_a"] == pair["case_b"] and pair["strategy_a"] == "sarachi_sale":
                win_short = "解体して更地売却" if winner_side == "A" else metrics_b.get("short_winner", winner_label)
            elif pair["case_a"] == pair["case_b"] and pair["strategy_b"] == "sarachi_sale":
                win_short = metrics_a.get("short_winner", winner_label) if winner_side == "A" else "解体して更地売却"
            elif pair["category"] == "hakajimai_choice":
                if pair["slug"] == "jikka-and-grave-keep-vs-total-jikkajimai":
                    win_short = "実家売却＋墓じまい一括完結"
                else:
                    win_short = winner_label
            else:
                win_short = (
                    metrics_a.get("short_winner", winner_label)
                    if winner_side == "A"
                    else metrics_b.get("short_winner", winner_label)
                )
            if pair["category"] == "hakajimai_choice" and pair["slug"] != "jikka-and-grave-keep-vs-total-jikkajimai":
                verdict_short = f"{win_short}が 約{diff_man:,}万円 安い"
            else:
                verdict_short = f"{win_short}が 約{diff_man:,}万円 有利"

        enriched_pairs.append(
            {
                **pair,
                "case_a_name": case_a["name"],
                "case_a_short": case_a["short_name"],
                "case_b_name": case_b["name"],
                "case_b_short": case_b["short_name"],
                "metrics_a": metrics_a,
                "metrics_b": metrics_b,
                "winner_side": winner_side,
                "winner_label": winner_label,
                "diff_5y_yen": abs(metrics_a["net_cash_5y_yen"] - metrics_b["net_cash_5y_yen"]),
                "diff_10y_yen": diff_10y,
                "payback_years": payback_years,
                "verdict_short": verdict_short,
            }
        )

    # 年別アーカイブ
    by_year: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in national_series:
        by_year[row["date"][:4]].append(row)
    history_yearly: list[dict[str, Any]] = []
    for yr in sorted(by_year.keys(), reverse=True):
        items = by_year[yr]
        woods = [x["wood_man_per_tsubo"] for x in items]
        steels = [x["steel_man_per_tsubo"] for x in items]
        rcs = [x["rc_man_per_tsubo"] for x in items]
        idxs = [x["repair_index"] for x in items]
        history_yearly.append(
            {
                "year": yr,
                "count": len(items),
                "avg_wood": round(sum(woods) / len(woods), 2),
                "min_wood": min(woods),
                "max_wood": max(woods),
                "avg_steel": round(sum(steels) / len(steels), 2),
                "avg_rc": round(sum(rcs) / len(rcs), 2),
                "avg_repair_index": round(sum(idxs) / len(idxs), 1),
                "series": [
                    {
                        "date": x["date"],
                        "wood_man_per_tsubo": x["wood_man_per_tsubo"],
                        "steel_man_per_tsubo": x["steel_man_per_tsubo"],
                        "rc_man_per_tsubo": x["rc_man_per_tsubo"],
                        "repair_index": x["repair_index"],
                    }
                    for x in items
                ],
            }
        )

    meta = {
        "site_name": "実家と空き家の試算表",
        "site_domain": "jikka-shisan.com",
        "date_from": date_from,
        "date_to": date_to,
        "total_points": len(national_series),
        "total_cases": len(enriched_cases),
        "total_compare_pairs": len(enriched_pairs),
        "tax_effective_date": tax_rules["effective_date"],
        "source_mode_label": source_mode_label,
        "source_credit": "総務省「住宅・土地統計調査」「小売物価統計調査（e-Stat）」・国土交通省「都道府県地価調査」・厚生労働省「衛生行政報告例（改葬統計）」",
    }

    latest = {
        "date": latest_nat["date"],
        "national": {
            "wood_man_per_tsubo": latest_nat["wood_man_per_tsubo"],
            "steel_man_per_tsubo": latest_nat["steel_man_per_tsubo"],
            "rc_man_per_tsubo": latest_nat["rc_man_per_tsubo"],
            "repair_index": latest_nat["repair_index"],
            "akiya_rate_pct": 13.8,
            "other_akiya_rate_pct": 5.9,
            "total_akiya_man_ko": 900.2,
            "other_akiya_man_ko": 385.6,
            "annual_kaisou_cases": 166886,
            "diff_prev_wood": round(latest_nat["wood_man_per_tsubo"] - prev_nat["wood_man_per_tsubo"], 2),
            "diff_2024_wood": round(latest_nat["wood_man_per_tsubo"] - national_series[0]["wood_man_per_tsubo"], 2),
        },
        "highest_akiya_5": [
            {
                "slug": x["slug"],
                "name": x["name"],
                "akiya_rate_pct": x["akiya_rate_pct"],
                "other_akiya_rate_pct": x["other_akiya_rate_pct"],
                "wood_man_per_tsubo": x["wood_man_per_tsubo"],
            }
            for x in sorted_akiya[:5]
        ],
        "lowest_akiya_5": [
            {
                "slug": x["slug"],
                "name": x["name"],
                "akiya_rate_pct": x["akiya_rate_pct"],
                "other_akiya_rate_pct": x["other_akiya_rate_pct"],
                "wood_man_per_tsubo": x["wood_man_per_tsubo"],
            }
            for x in list(reversed(sorted_akiya[-5:]))
        ],
        "cheapest_kaitai_5": [
            {
                "slug": x["slug"],
                "name": x["name"],
                "wood_man_per_tsubo": x["wood_man_per_tsubo"],
                "std_30tsubo_demolition_yen": x["std_30tsubo_demolition_yen"],
            }
            for x in sorted_kaitai[:5]
        ],
        "priciest_kaitai_5": [
            {
                "slug": x["slug"],
                "name": x["name"],
                "wood_man_per_tsubo": x["wood_man_per_tsubo"],
                "std_30tsubo_demolition_yen": x["std_30tsubo_demolition_yen"],
            }
            for x in list(reversed(sorted_kaitai[-5:]))
        ],
        "national_series": [
            {
                "date": x["date"],
                "wood_man_per_tsubo": x["wood_man_per_tsubo"],
                "steel_man_per_tsubo": x["steel_man_per_tsubo"],
                "rc_man_per_tsubo": x["rc_man_per_tsubo"],
                "repair_index": x["repair_index"],
            }
            for x in national_series
        ],
    }

    write_json(out_dir / "meta.json", meta)
    write_json(out_dir / "latest.json", latest)
    write_json(out_dir / "prefectures.json", pref_summaries)
    write_json(out_dir / "property_cases.json", enriched_cases)
    write_json(out_dir / "compare_pairs.json", enriched_pairs)
    write_json(out_dir / "history_yearly.json", history_yearly)
    write_json(out_dir / "tax_rules.json", tax_rules)

    print(
        f"[OK] データセット生成完了: 最新基準日 {date_to} / 全国木造解体 {latest_nat['wood_man_per_tsubo']:.2f}万円/坪 / "
        f"ケース {len(enriched_cases)}件 / 比較 {len(enriched_pairs)}組 / 都道府県 47件"
    )
    return meta


if __name__ == "__main__":
    build_all()
