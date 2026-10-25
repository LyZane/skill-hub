# -*- coding: utf-8 -*-
"""天猫在售商品数据总览报告生成器。
读取 data-dir 下的 products.json / reviews_*.json / wdj_raw.json，
过滤非实物商品，按累计销量降序，校验主图链接（404 则退出码 2），生成单文件 HTML。
"""
import json, re, os, sys, glob, argparse
import urllib.request

def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument('--data-dir', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--exclude', default='运费,补差,非实物,滤网,配件', help='标题命中任一关键词的商品被过滤')
    ap.add_argument('--skip-image-check', action='store_true')
    return ap.parse_args()

def check_images(products):
    broken, warned = [], []
    for p in products:
        try:
            r = urllib.request.urlopen(p['img'], timeout=10)
            if r.getcode() != 200:
                warned.append((p['id'], r.getcode()))
        except urllib.error.HTTPError as e:
            if e.code == 404:
                broken.append((p['id'], p['img']))
            else:
                warned.append((p['id'], e.code))
        except Exception as e:
            warned.append((p['id'], 'NETERR'))
    return broken, warned

ANS_RE = re.compile(r'展开\s*(.*?)\s*(\S+?)于\s*(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\s*回答\s*(\d+)')

def parse_answers(shown):
    out = []
    for m in ANS_RE.finditer(shown or ''):
        c, w, t, _ = m.groups()
        if c.strip():
            out.append({'content': c.strip(), 'who': w, 'time': t})
    return out

def big_img(url):
    return re.sub(r'_\d+x\d+[^.]*\.webp$', '', url)

def main():
    args = parse_args()
    base = args.data_dir
    products = json.load(open(os.path.join(base, 'products.json'), encoding='utf-8'))
    reviews = {}
    for f in sorted(glob.glob(os.path.join(base, 'reviews_*.json'))):
        reviews.update(json.load(open(f, encoding='utf-8')))
    wdj_path = os.path.join(base, 'wdj_raw.json')
    wdj = json.load(open(wdj_path, encoding='utf-8')) if os.path.exists(wdj_path) else []

    kw = [k for k in args.exclude.split(',') if k]
    kept, dropped = [], []
    for p in products:
        (dropped if any(k in p['title'] for k in kw) else kept).append(p)
    print('excluded %d non-product items: %s' % (len(dropped), ', '.join('%s(%s)' % (d['id'], d['title'][:10]) for d in dropped)))

    for p in kept:  # 主图统一为原图 URL
        p['img'] = big_img(p['img'])

    broken, warned = ([], []) if args.skip_image_check else check_images(kept)
    for pid, code in warned:
        print('WARN image %s -> %s' % (pid, code))

    wdj_by_id = {}
    for item in wdj:
        wdj_by_id.setdefault(item['id'], []).append({
            'q': item['q'], 'asker': item['asker'], 'time': item['time'],
            'answers': parse_answers(item.get('shown', ''))})

    data = []
    for p in kept:
        rv = reviews.get(p['id'], {})
        data.append({'id': p['id'], 'title': p['title'], 'img': p['img'], 'price': p['price'],
                     'stock': p['stock'], 'cum_sales': p['cum_sales'], 'sales_30d': p['sales_30d'],
                     'sold_front': rv.get('sold'), 'review_count': rv.get('rc'),
                     'comments': rv.get('comments', []), 'wdj': wdj_by_id.get(p['id'], [])})
    data.sort(key=lambda d: d['cum_sales'], reverse=True)

    payload = json.dumps(data, ensure_ascii=False)
    html = HTML_TEMPLATE.replace('__PAYLOAD__', payload)
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, 'w', encoding='utf-8') as f:
        f.write(html)
    print('written %s (%d bytes) | products: %d | comments: %d | wdj: %d' % (
        args.out, os.path.getsize(args.out), len(data),
        sum(len(d['comments']) for d in data), sum(len(d['wdj']) for d in data)))

    if broken:
        print('BROKEN (404) main images — fix products.json and rerun:')
        for pid, url in broken:
            print('  %s  %s' % (pid, url))
        sys.exit(2)

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>天猫在售商品数据总览</title>
<style>
  :root{--bg:#f5f6f8;--panel:#fff;--line:#e6e8ee;--text:#1f2333;--sub:#6b7280;--accent:#ff5000;--accent-soft:#fff1ea;--blue-soft:#eef4ff;--green-soft:#e9f7f1;--radius:12px;}
  *{box-sizing:border-box;margin:0;padding:0;}
  html,body{height:100%;}
  body{font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif;background:var(--bg);color:var(--text);display:flex;flex-direction:column;}
  header{background:var(--panel);border-bottom:1px solid var(--line);padding:14px 22px;display:flex;align-items:baseline;gap:14px;flex-wrap:wrap;}
  header h1{font-size:18px;font-weight:700;}
  header .meta{color:var(--sub);font-size:12px;}
  .wrap{flex:1;display:flex;min-height:0;}
  aside{width:270px;min-width:270px;background:var(--panel);border-right:1px solid var(--line);overflow-y:auto;padding:10px;}
  .p-item{display:flex;gap:10px;padding:9px;border-radius:10px;cursor:pointer;align-items:center;border:1px solid transparent;}
  .p-item:hover{background:#f8f9fb;}
  .p-item.active{background:var(--accent-soft);border-color:#ffd9c4;}
  .p-item img{width:52px;height:52px;border-radius:8px;object-fit:cover;background:#eee;flex:none;}
  .p-item .t{font-size:12px;line-height:1.45;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;}
  .p-item .b{font-size:11px;color:var(--sub);margin-top:3px;}
  .p-item .b b{color:var(--accent);font-weight:600;}
  main{flex:1;overflow-y:auto;padding:20px 24px;}
  .card{background:var(--panel);border:1px solid var(--line);border-radius:var(--radius);padding:18px 20px;margin-bottom:16px;}
  .p-head{display:flex;gap:16px;}
  .p-head img{width:96px;height:96px;border-radius:10px;object-fit:cover;background:#eee;}
  .p-head h2{font-size:16px;font-weight:700;line-height:1.5;}
  .p-head h2 a.plink{color:inherit;text-decoration:none;}
  .p-head h2 a.plink:hover{color:var(--accent);text-decoration:underline;}
  .stats{display:flex;gap:8px;flex-wrap:wrap;margin-top:10px;}
  .stat{font-size:12px;padding:4px 10px;border-radius:999px;background:#f2f3f7;color:var(--sub);}
  .stat b{color:var(--text);}
  .stat.hot{background:var(--accent-soft);color:#c2410c;}
  .stat.hot b{color:var(--accent);}
  .tabs{display:flex;gap:8px;margin:4px 0 14px;}
  .tab{padding:7px 16px;border-radius:999px;font-size:13px;cursor:pointer;background:#eef0f4;color:var(--sub);border:none;}
  .tab.on{background:var(--text);color:#fff;}
  .comment{border-top:1px dashed var(--line);padding:14px 0;}
  .comment:first-child{border-top:none;}
  .c-top{display:flex;justify-content:space-between;font-size:12px;color:var(--sub);margin-bottom:6px;}
  .c-top .u{color:var(--text);font-weight:600;}
  .c-content{font-size:13.5px;line-height:1.7;}
  .c-sku{font-size:12px;color:var(--sub);margin-top:4px;}
  .imgs{display:flex;gap:8px;flex-wrap:wrap;margin-top:8px;}
  .imgs img{width:84px;height:84px;border-radius:8px;object-fit:cover;cursor:pointer;background:#eee;border:1px solid var(--line);}
  .append{margin-top:8px;padding:8px 12px;background:var(--blue-soft);border-radius:8px;font-size:12.5px;color:#1e40af;line-height:1.6;}
  .reply{margin-top:8px;padding:8px 12px;background:var(--green-soft);border-radius:8px;font-size:12.5px;color:#065f46;line-height:1.6;}
  .qa{border-top:1px dashed var(--line);padding:14px 0;}
  .qa:first-child{border-top:none;}
  .q{font-size:13.5px;font-weight:600;}
  .q .ask{font-weight:400;color:var(--sub);font-size:12px;margin-left:8px;}
  .a{margin-top:8px;padding:8px 12px;background:#f6f7fa;border-radius:8px;font-size:12.5px;line-height:1.6;}
  .a .who{color:var(--sub);font-size:11.5px;margin-top:2px;}
  .empty{color:var(--sub);font-size:13px;padding:18px 0;text-align:center;}
  #lightbox{position:fixed;inset:0;background:rgba(15,17,26,.82);display:none;align-items:center;justify-content:center;z-index:99;cursor:zoom-out;}
  #lightbox img{max-width:88vw;max-height:88vh;border-radius:8px;background:#fff;}
</style>
</head>
<body>
<header>
  <h1>天猫在售商品数据总览</h1>
  <span class="meta">共 <span id="pn"></span> 件商品（已剔除运费/配件类） · 按累计销量降序 · 评论每商品最多 20 条 / 问大家全量</span>
</header>
<div class="wrap">
  <aside id="side"></aside>
  <main id="main"></main>
</div>
<div id="lightbox" onclick="this.style.display='none'"><img id="lbimg" alt=""></div>
<script>
const DATA = __PAYLOAD__;
document.getElementById('pn').textContent = DATA.length;
const side = document.getElementById('side');
const main = document.getElementById('main');
let cur = 0, curTab = 'reviews';
const esc = s => String(s == null ? '' : s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function renderSide(){
  side.innerHTML = DATA.map((p,i)=>`
    <div class="p-item ${i===cur?'active':''}" onclick="select(${i})">
      <img src="${esc(p.img)}" loading="lazy" alt="">
      <div>
        <div class="t">${esc(p.title)}</div>
        <div class="b">累计销量 <b>${esc(p.cum_sales)}</b> · 评论 ${p.comments.length} · 问大家 ${p.wdj.length}</div>
      </div>
    </div>`).join('');
}
function statRow(p){
  return `<div class="stats">
    <span class="stat hot">累计销量 <b>${esc(p.cum_sales)}</b></span>
    <span class="stat">30日销量 <b>${esc(p.sales_30d)}</b></span>
    <span class="stat">前端已售 <b>${esc(p.sold_front || '-')}</b></span>
    <span class="stat">售价 <b>¥${esc(p.price)}</b></span>
    <span class="stat">库存 <b>${esc(p.stock)}</b></span>
    <span class="stat">评价数 <b>${esc(p.review_count || p.comments.length)}</b></span>
    <span class="stat">问大家 <b>${p.wdj.length}</b></span>
  </div>`;
}
function commentHTML(c){
  const imgs = (c.imgs||[]).concat(c.appendImgs||[]);
  return `<div class="comment">
    <div class="c-top"><span class="u">${esc(c.user)}</span><span>${esc((c.meta||'').split('已购：')[0])}</span></div>
    <div class="c-content">${esc(c.content)}</div>
    <div class="c-sku">已购：${esc((c.meta||'').split('已购：')[1] || '')}</div>
    ${imgs.length?`<div class="imgs">${imgs.map(u=>`<img src="${esc(u)}" loading="lazy" onclick="lb('${esc(u)}')" alt="">`).join('')}</div>`:''}
    ${c.append?`<div class="append">${esc(c.append)}</div>`:''}
    ${c.reply?`<div class="reply">${esc(c.reply)}</div>`:''}
  </div>`;
}
function qaHTML(q){
  return `<div class="qa">
    <div class="q">${esc(q.q)}<span class="ask">${esc(q.asker)} 于 ${esc(q.time)} 提问</span></div>
    ${q.answers.length ? q.answers.map(a=>`<div class="a">${esc(a.content)}<div class="who">${esc(a.who)} 于 ${esc(a.time)} 回答</div></div>`).join('') : '<div class="a" style="color:var(--sub)">暂无回答</div>'}
  </div>`;
}
function renderMain(){
  const p = DATA[cur];
  const body = curTab==='reviews'
    ? (p.comments.length ? p.comments.map(commentHTML).join('') : '<div class="empty">该商品暂无评论数据</div>')
    : (p.wdj.length ? p.wdj.map(qaHTML).join('') : '<div class="empty">该商品暂无问大家数据</div>');
  main.innerHTML = `
    <div class="card">
      <div class="p-head">
        <img src="${esc(p.img)}" alt="">
        <div style="flex:1">
          <h2><a class="plink" href="https://detail.tmall.com/item.htm?id=${esc(p.id)}" target="_blank" rel="noopener" title="在新标签页打开商品详情页">${esc(p.title)}</a></h2>
          <div style="font-size:12px;color:var(--sub);margin-top:4px">商品ID：${esc(p.id)}</div>
          ${statRow(p)}
        </div>
      </div>
    </div>
    <div class="card">
      <div class="tabs">
        <button class="tab ${curTab==='reviews'?'on':''}" onclick="setTab('reviews')">用户评价 · ${p.comments.length}</button>
        <button class="tab ${curTab==='wdj'?'on':''}" onclick="setTab('wdj')">问大家 · ${p.wdj.length}</button>
      </div>
      <div>${body}</div>
    </div>`;
  main.scrollTop = 0;
}
window.select = i => { cur = i; renderSide(); renderMain(); };
window.setTab = t => { curTab = t; renderMain(); };
window.lb = u => { const L = document.getElementById('lightbox'); document.getElementById('lbimg').src = u; L.style.display = 'flex'; };
renderSide(); renderMain();
</script>
</body>
</html>"""

if __name__ == '__main__':
    main()
