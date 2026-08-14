#!/usr/bin/env python3
"""Inject collected data into the report template -> index.html.
usage: build_report.py <workdir> <productId> <productName> [shortTitle] [templatePath] [outPath]
"""
import json, os, sys, datetime, glob

def main():
    if len(sys.argv) < 4:
        print(__doc__); sys.exit(1)
    workdir = os.path.abspath(sys.argv[1])
    pid = sys.argv[2]
    pname = sys.argv[3]
    short = sys.argv[4] if len(sys.argv) > 4 else pname[:10]
    script_dir = os.path.dirname(os.path.abspath(__file__))
    tpl_path = sys.argv[5] if len(sys.argv) > 5 else (
        os.path.join(script_dir, "..", "templates", "report.html")
        if os.path.exists(os.path.join(script_dir, "..", "templates", "report.html"))
        else os.path.join(script_dir, "template_report.html"))
    out_path = sys.argv[6] if len(sys.argv) > 6 else os.path.join(workdir, "index.html")

    reviews = json.load(open(os.path.join(workdir, "reviews_all.json"), encoding="utf-8"))
    analysis = json.load(open(os.path.join(workdir, "sentiment_keywords.json"), encoding="utf-8"))
    manifest = {m["rid"]: m for m in json.load(open(os.path.join(workdir, "media_manifest.json"), encoding="utf-8"))}

    data = []
    for idx, ci in enumerate(reviews, 1):
        rid = f"R{idx:02d}"
        an = analysis.get(rid, {"sentiment": "中性", "keywords": ""})
        man = manifest.get(rid, {})
        videos = []
        for vi, p in enumerate([p for p in ci.get("pictureInfoList") or [] if str(p.get("mediaType")) == "2"]):
            vs, vc = man.get("videos", []), man.get("video_covers", [])
            videos.append({"src": "media/" + vs[vi] if vi < len(vs) else "",
                           "cover": "media/" + vc[vi] if vi < len(vc) else "",
                           "len": p.get("mediaLength", "")})
        reply = ""
        rl = ci.get("replyList") or []
        if rl:
            reply = rl[0].get("content", "")
        ac = ci.get("afterComment") or {}
        after = (ac.get("commentData") or ac.get("content") or ac.get("commentText") or "").strip()
        after_date = (ac.get("commentDate") or ac.get("date") or "")[:10]
        data.append({
            "rid": rid, "nick": ci.get("userNickName", ""),
            "date": (ci.get("commentDate") or "")[:10], "fullDate": ci.get("commentDate", ""),
            "score": ci.get("commentScore", ""),
            "spec": (ci.get("productSpecifications") or "").replace("已购", "").strip(),
            "text": (ci.get("commentData") or ci.get("noCommentMessage") or "").strip(),
            "sent": an["sentiment"],
            "kw": [k.strip() for k in an["keywords"].split(",") if k.strip()],
            "imgs": ["media/" + f for f in man.get("images", [])],
            "vids": videos, "praise": ci.get("praiseCnt", "0"), "reply": reply,
            "after": after, "afterDate": after_date,
            "id": ci.get("commentId", ""),
        })

    sent_counts = {"正面": 0, "有褒有贬": 0, "中性": 0, "负面": 0}
    for d in data:
        sent_counts[d["sent"]] = sent_counts.get(d["sent"], 0) + 1

    NEG_MARKERS = ("重", "水流声", "不值", "退货", "雾量小", "操作不便", "不及预期", "不可调")
    kw_count, kw_neg = {}, set()
    for d in data:
        for k in d["kw"]:
            kw_count[k] = kw_count.get(k, 0) + 1
            if any(m in k for m in NEG_MARKERS) or d["sent"] == "负面":
                kw_neg.add(k)
    top_kw = sorted(kw_count.items(), key=lambda x: -x[1])[:18]

    # auto pain text
    pains = [f"{k}（{n} 条）" for k, n in top_kw if k in kw_neg]
    negs = [f"差评 {d['rid']}：{d['text'][:46]}…" for d in data if d["sent"] == "负面"]
    pain_text = " · ".join(pains + negs) if (pains or negs) else "本次采集未发现明显吐槽点。"

    # collect timestamp from newest incoming file
    inc = sorted(glob.glob(os.path.join(workdir, "incoming", "run_*.json")), key=os.path.getmtime)
    if inc:
        ts = datetime.datetime.fromtimestamp(os.path.getmtime(inc[-1])).strftime("%Y-%m-%d %H:%M")
    else:
        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

    n = len(data)
    total_imgs = sum(len(d["imgs"]) for d in data)
    total_vids = sum(len(d["vids"]) for d in data)

    repl = {
        "__PTITLE__": f"{short} {pid}",
        "__HTITLE__": f'京东评论洞察 <span class="serif">/</span> {short}',
        "__DATE__": datetime.date.today().isoformat(),
        "__PNAME__": pname, "__PID__": pid,
        "__N_REV__": str(n), "__N_IMG__": str(total_imgs), "__N_VID__": str(total_vids),
        "__POS_RATE__": str(round(sent_counts["正面"] / n * 100)) if n else "0",
        "__S_POS__": str(sent_counts["正面"]), "__S_MIX__": str(sent_counts["有褒有贬"]),
        "__S_NEU__": str(sent_counts["中性"]), "__S_NEG__": str(sent_counts["负面"]),
        "__N_KW__": str(len(top_kw)), "__PAIN_TEXT__": pain_text, "__COLLECT_TS__": ts,
        "__DATA__": json.dumps(data, ensure_ascii=False),
        "__KW__": json.dumps([{"k": k, "n": c, "neg": k in kw_neg} for k, c in top_kw], ensure_ascii=False),
        "__SENT__": json.dumps(sent_counts, ensure_ascii=False),
    }
    html = open(tpl_path, encoding="utf-8").read()
    for k, v in repl.items():
        html = html.replace(k, v)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    open(out_path, "w", encoding="utf-8").write(html)
    print("written:", out_path, len(html) // 1024, "KB")

if __name__ == "__main__":
    main()
