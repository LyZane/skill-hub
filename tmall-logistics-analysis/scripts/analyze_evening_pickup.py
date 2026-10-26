from pathlib import Path
import json
import os
import pandas as pd

ROOT = Path(os.environ.get("TMALL_LOGISTICS_ROOT", Path(__file__).resolve().parent))
ARRIVALS = Path(os.environ["TMALL_LOGISTICS_ARRIVALS"])
ITEMS = Path(os.environ["TMALL_LOGISTICS_ITEMS"])


def load_matched_orders():
    arrivals = pd.read_excel(ARRIVALS, dtype={"订单编号": str})
    items = pd.read_excel(ITEMS, dtype={"子订单编号": str, "主订单编号": str})
    time_cols = ["订单创建时间", "订单付款时间", "发货时间", "确认收货时间"]
    for col in time_cols:
        items[col] = pd.to_datetime(items[col], errors="coerce")

    direct = arrivals.merge(
        items,
        left_on="订单编号",
        right_on="子订单编号",
        how="left",
        validate="many_to_one",
        suffixes=("", "_报表"),
    )
    missing = direct["子订单编号"].isna()
    for idx in direct.index[missing]:
        arrival = direct.loc[idx]
        candidates = items[
            (items["主订单编号"] == arrival["订单编号"])
            & (items["商品属性"] == arrival["商品sku"])
        ]
        if len(candidates) != 1:
            raise ValueError(f"订单 {arrival['订单编号']} 的SKU匹配数为 {len(candidates)}，无法唯一匹配")
        item = candidates.iloc[0]
        for col in items.columns:
            direct.loc[idx, col] = item[col]
    direct["匹配方式"] = ["子订单号" if not missing.loc[i] else "主订单号+SKU" for i in direct.index]
    direct["匹配方式"] = direct["匹配方式"].astype(str)
    direct["物流线路"] = direct["物流线路"].astype(str).str.replace(r"\s*-\s*", " - ", regex=True)
    direct["发货城市"] = direct["物流线路"].str.split(" - ").str[0]
    direct["适用本店班次"] = (
        (direct["发货城市"] == os.environ.get("TMALL_LOGISTICS_ORIGIN", "深圳市"))
        & (direct["快递公司"] == os.environ.get("TMALL_LOGISTICS_COURIER", "韵达快递"))
        & direct["发货时间"].notna()
    )
    if direct.empty or direct["子订单编号"].isna().any() or direct["发货时间"].isna().any():
        raise ValueError("考核订单未完整匹配或发货时间缺失")
    return direct


def current_pickup_hours():
    value = os.environ.get("TMALL_LOGISTICS_PICKUPS", "10:00,17:00")
    return sorted(int(part.split(":")[0]) + int(part.split(":")[1]) / 60 for part in value.split(","))


def next_pickup(dt, extra_hour=None):
    day = dt.normalize()
    current = current_pickup_hours()
    hours = current + ([] if extra_hour is None else [extra_hour])
    candidates = [day + pd.Timedelta(hours=h) for h in sorted(hours)]
    candidates.extend(day + pd.Timedelta(days=1, hours=h) for h in current)
    return min(candidate for candidate in candidates if candidate >= dt)


def run_scenarios(d):
    d = d.copy()
    d["当前模拟揽收"] = d["发货时间"].apply(next_pickup)
    d["当前等待小时"] = (d["当前模拟揽收"] - d["发货时间"]).dt.total_seconds() / 3600
    scenario_value = os.environ.get("TMALL_LOGISTICS_EXTRA_PICKUPS", "17:30,18:00,18:30,19:00,19:30,20:00,20:30,21:00,21:30,22:00,22:30,23:00")
    scenario_hours = [int(part.split(":")[0]) + int(part.split(":")[1]) / 60 for part in scenario_value.split(",")]
    rows = []
    for hour in scenario_hours:
        new_pickup = d["发货时间"].apply(lambda x: next_pickup(x, hour))
        saving = ((d["当前模拟揽收"] - new_pickup).dt.total_seconds() / 3600).where(d["适用本店班次"], 0).clip(lower=0)
        impacted = saving > 0
        simulated = d["物流到货时长/小时"] - saving
        hour_int = int(hour)
        minute = 30 if hour % 1 else 0
        rows.append({
            "新增揽收时间": f"{hour_int:02d}:{minute:02d}",
            "新增时间小时": hour,
            "受益订单数": int(impacted.sum()),
            "受益订单占比": float(impacted.mean()),
            "受益订单平均节省小时": float(saving[impacted].mean()) if impacted.any() else 0,
            "总节省小时": float(saving.sum()),
            "全店平均缩短小时": float(saving.sum() / len(d)),
            "模拟到货时长": float(simulated.mean()),
            "达到4.0档": bool(simulated.mean() <= 58.66),
            "达到4.2档": bool(simulated.mean() <= 56.00),
        })
        d[f"节省_{hour_int:02d}{minute:02d}"] = saving
    return d, pd.DataFrame(rows)


if __name__ == "__main__":
    matched = load_matched_orders()
    matched, scenarios = run_scenarios(matched)
    print(f"考核记录={len(matched)}；唯一子订单={matched['子订单编号'].nunique()}；发货时间完整={matched['发货时间'].notna().sum()}")
    print("匹配方式", matched["匹配方式"].value_counts().to_dict())
    print("适用本店班次", int(matched["适用本店班次"].sum()))
    print("发货城市×快递", matched.groupby(["发货城市", "快递公司"]).size().to_dict())
    print("适用订单发货小时分布", matched.loc[matched["适用本店班次"], "发货时间"].dt.hour.value_counts().sort_index().to_dict())
    print(scenarios.round(6).to_string(index=False))
    matched.to_excel(ROOT / "evening_pickup_orders.xlsx", index=False)
    scenarios.to_excel(ROOT / "evening_pickup_scenarios.xlsx", index=False)
    (ROOT / "evening_pickup_results.json").write_text(
        json.dumps(scenarios.to_dict(orient="records"), ensure_ascii=False, indent=2), encoding="utf-8"
    )
