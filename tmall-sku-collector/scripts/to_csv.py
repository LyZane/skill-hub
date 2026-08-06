# -*- coding: utf-8 -*-
"""data.json 展平为 CSV 明细。用法: python3 to_csv.py <data.json> <out.csv>"""
import json, csv, sys

def main():
    if len(sys.argv) < 3:
        sys.exit("用法: python3 to_csv.py <data.json> <out.csv>")
    with open(sys.argv[1], encoding="utf-8") as f:
        data = json.load(f)
    with open(sys.argv[2], "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["商品ID", "商品标题", "商品链接", "SKU ID", "SKU名称",
                    "原价(元)", "实付价(元)", "库存", "SKU图片链接"])
        n = 0
        for item in data.get("items", []):
            for row in item.get("rows", []):
                w.writerow([item["itemId"], item["title"], item["url"], row["skuId"],
                            row["skuName"], row["listPrice"], row["promoPrice"],
                            row.get("quantity", ""), row["image"]])
                n += 1
    print(f"rows={n}")

if __name__ == "__main__":
    main()
