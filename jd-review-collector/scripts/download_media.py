#!/usr/bin/env python3
"""Download all images/videos for collected reviews into media/.
usage: download_media.py <workdir>
Naming: R{序号}_img{n}.jpg / R{序号}_vid{n}.mp4 (+ _cover.jpg); writes media_manifest.json.
"""
import json, os, sys, concurrent.futures as cf, urllib.request

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Referer": "https://item.jd.com/",
}

def fetch(url, dest, tries=3):
    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        return dest, "cached"
    last = None
    for _ in range(tries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=30) as r:
                data = r.read()
            if len(data) < 100:
                raise IOError(f"too small: {len(data)}")
            open(dest, "wb").write(data)
            return dest, "ok"
        except Exception as e:
            last = e
    return dest, f"FAIL: {last}"

def main():
    workdir = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.getcwd()
    media = os.path.join(workdir, "media")
    os.makedirs(media, exist_ok=True)
    reviews = json.load(open(os.path.join(workdir, "reviews_all.json"), encoding="utf-8"))
    tasks, manifest = [], []
    for idx, ci in enumerate(reviews, 1):
        rid = f"R{idx:02d}"
        entry = {"rid": rid, "commentId": ci.get("commentId"), "images": [], "videos": [], "video_covers": []}
        img_n = vid_n = 0
        for p in ci.get("pictureInfoList") or []:
            mt = str(p.get("mediaType", "1"))
            if mt == "1":
                img_n += 1
                url = p.get("largePicURL") or p.get("picURL") or ""
                primary = url[:-4] if url.endswith(".dpg") else url  # strip .dpg -> original JPEG
                dest = os.path.join(media, f"{rid}_img{img_n}.jpg")
                tasks.append((primary, dest, url))
                entry["images"].append(os.path.basename(dest))
            elif mt == "2":
                vid_n += 1
                dest = os.path.join(media, f"{rid}_vid{vid_n}.mp4")
                tasks.append((p.get("videoPlayUrl", ""), dest, None))
                entry["videos"].append(os.path.basename(dest))
                if p.get("picURL"):
                    cdest = os.path.join(media, f"{rid}_vid{vid_n}_cover.jpg")
                    tasks.append((p["picURL"], cdest, None))
                    entry["video_covers"].append(os.path.basename(cdest))
        manifest.append(entry)
    json.dump(manifest, open(os.path.join(workdir, "media_manifest.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"total download tasks: {len(tasks)}")
    ok = cached = 0
    fails = []
    def work(t):
        url, dest, fb = t
        d, st = fetch(url, dest)
        if st.startswith("FAIL") and fb:
            d, st = fetch(fb, dest)
        return st
    with cf.ThreadPoolExecutor(max_workers=6) as ex:
        for st in ex.map(work, tasks):
            if st == "ok": ok += 1
            elif st == "cached": cached += 1
            else: fails.append(st)
    print(f"ok={ok} cached={cached} fail={len(fails)}")
    for f in fails[:20]:
        print("  ", f)

if __name__ == "__main__":
    main()
