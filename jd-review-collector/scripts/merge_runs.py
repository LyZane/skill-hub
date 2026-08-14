#!/usr/bin/env python3
"""Merge received crawl pages into reviews_all.json + review_texts.txt.
usage: merge_runs.py <workdir>
"""
import json, glob, os, sys

def main():
    workdir = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.getcwd()
    inc = os.path.join(workdir, "incoming")
    files = sorted(glob.glob(os.path.join(inc, "run_*.json")))
    if not files:
        print("no run files found in", inc); sys.exit(1)
    reviews, order = {}, []
    for f in files:
        payload = json.load(open(f, encoding="utf-8"))
        comments = payload.get("comments", [])
        print(f"{os.path.basename(f)}: page {payload.get('pageNum')}, {len(comments)} comments")
        for ci in comments:
            cid = ci.get("commentId")
            if cid and cid not in reviews:
                reviews[cid] = ci
                order.append(cid)
    dataset = [reviews[c] for c in order]
    json.dump(dataset, open(os.path.join(workdir, "reviews_all.json"), "w", encoding="utf-8"), ensure_ascii=False)
    lines = []
    for i, ci in enumerate(dataset, 1):
        txt = (ci.get("commentData") or ci.get("tagCommentContent") or ci.get("noCommentMessage") or "").strip()
        lines.append(f"---R{i:02d}|{ci.get('commentScore')}星|{ci.get('commentDate')}|{ci.get('productSpecifications','')}|赞{ci.get('praiseCnt')}")
        lines.append(txt)
    open(os.path.join(workdir, "review_texts.txt"), "w", encoding="utf-8").write("\n".join(lines))
    with_media = sum(1 for d in dataset if d.get("pictureInfoList"))
    print(f"total unique reviews: {len(dataset)} (with media: {with_media})")

if __name__ == "__main__":
    main()
