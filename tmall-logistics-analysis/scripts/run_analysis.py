"""Generate a Tmall logistics arrival-duration analysis workbook from seller exports."""
import argparse
import os
from pathlib import Path
import sys

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

DEFAULT_EXTRA = "17:30,18:00,18:30,19:00,19:30,20:00,20:30,21:00,21:30,22:00,22:30,23:00"


def parse_args():
    parser = argparse.ArgumentParser(description="天猫物流到货时长：城市、线路、揽收和临时剔除分析")
    parser.add_argument("--arrivals", required=True, help="体验分页面导出的物流到货时长订单明细.xlsx")
    parser.add_argument("--items", required=True, help="千牛宝贝销售明细报表.xlsx")
    parser.add_argument("--output", required=True, help="输出xlsx路径")
    parser.add_argument("--expected-mean", required=True, type=float, help="体验分页面展示的平均到货时长，用于口径核验")
    parser.add_argument("--period", help="考核订单实际付款范围；默认由匹配数据生成")
    parser.add_argument("--pickups", default="10:00,17:00", help="当前每日揽收班次，逗号分隔")
    parser.add_argument("--extra-pickups", default=DEFAULT_EXTRA, help="候选新增班次；必须包含18:00")
    parser.add_argument("--origin", default="深圳市", help="适用本店班次的发货城市")
    parser.add_argument("--courier", default="韵达快递", help="适用本店班次的快递公司")
    parser.add_argument("--exclude-city", help="临时剔除的收货城市")
    parser.add_argument("--exclude-product-id", help="临时剔除的商品ID")
    parser.add_argument("--arrival-score", type=float, default=3.9)
    parser.add_argument("--pickup-score", type=float, default=4.9)
    parser.add_argument("--speed-score", type=float, default=4.5)
    parser.add_argument("--overall-score", type=float, default=4.76)
    return parser.parse_args()


def main():
    args = parse_args()
    arrivals = Path(args.arrivals).expanduser().resolve()
    items = Path(args.items).expanduser().resolve()
    output = Path(args.output).expanduser().resolve()
    for path, label in [(arrivals, "物流到货时长明细"), (items, "宝贝销售明细")]:
        if not path.is_file():
            raise FileNotFoundError(f"{label}不存在：{path}")
    if output.suffix.lower() != ".xlsx":
        raise ValueError("输出文件必须为.xlsx")
    if bool(args.exclude_city) != bool(args.exclude_product_id):
        raise ValueError("临时剔除必须同时提供--exclude-city和--exclude-product-id")
    if "18:00" not in args.extra_pickups.split(","):
        raise ValueError("候选新增班次必须包含18:00")

    output.parent.mkdir(parents=True, exist_ok=True)
    env = os.environ
    env["TMALL_LOGISTICS_ROOT"] = str(output.parent)
    env["TMALL_LOGISTICS_ARRIVALS"] = str(arrivals)
    env["TMALL_LOGISTICS_ITEMS"] = str(items)
    env["TMALL_LOGISTICS_OUTPUT"] = str(output)
    env["TMALL_LOGISTICS_PICKUPS"] = args.pickups
    env["TMALL_LOGISTICS_EXTRA_PICKUPS"] = args.extra_pickups
    env["TMALL_LOGISTICS_ORIGIN"] = args.origin
    env["TMALL_LOGISTICS_COURIER"] = args.courier
    env["TMALL_LOGISTICS_ARRIVAL_SCORE"] = str(args.arrival_score)
    env["TMALL_LOGISTICS_PICKUP_SCORE"] = str(args.pickup_score)
    env["TMALL_LOGISTICS_SPEED_SCORE"] = str(args.speed_score)
    env["TMALL_LOGISTICS_OVERALL_SCORE"] = str(args.overall_score)
    if args.exclude_city:
        env["TMALL_LOGISTICS_EXCLUDE_CITY"] = args.exclude_city
        env["TMALL_LOGISTICS_EXCLUDE_PRODUCT_ID"] = args.exclude_product_id
    else:
        env.pop("TMALL_LOGISTICS_EXCLUDE_CITY", None)
        env.pop("TMALL_LOGISTICS_EXCLUDE_PRODUCT_ID", None)

    from analyze_evening_pickup import load_matched_orders
    matched = load_matched_orders()
    actual_mean = matched["物流到货时长/小时"].mean()
    if round(actual_mean, 2) != round(args.expected_mean, 2):
        raise ValueError(
            f"口径核验失败：{len(matched)}笔导出订单均值{actual_mean:.3f}小时，"
            f"与页面{args.expected_mean:.2f}小时不一致。请检查考核日期、导出明细和有效订单口径。"
        )
    if not args.period:
        start = matched["订单付款时间"].min().date().isoformat()
        end = matched["订单付款时间"].max().date().isoformat()
        args.period = f"{start} 至 {end}（考核订单实际付款范围）"
    env["TMALL_LOGISTICS_PERIOD"] = args.period

    import build_logistics_report  # noqa: F401  # Executes the base report build.
    import integrate_evening_pickup
    integrate_evening_pickup.main()
    import add_exclusion_and_polish
    add_exclusion_and_polish.main()

    print(f"口径核验通过：{len(matched)}笔，平均{actual_mean:.6f}小时")
    print(f"适用本店班次：{int(matched['适用本店班次'].sum())}笔")
    print(f"报告已生成：{output}")
    print("下一步：运行Excel重算与verify，并对关键结果做独立QA。")


if __name__ == "__main__":
    main()
