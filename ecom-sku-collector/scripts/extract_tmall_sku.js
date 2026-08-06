(() => {
  try {
    const ctx = window.__ICE_APP_CONTEXT__;
    const res = ctx && ctx.loaderData && ctx.loaderData.home && ctx.loaderData.home.data && ctx.loaderData.home.data.res;
    if (!res || !res.skuCore || !res.skuBase) {
      return JSON.stringify({ error: 'no ICE sku data', hint: '页面未加载完成或为旧版框架，刷新后重试', hasIce: !!ctx, url: location.href });
    }
    const sku2info = res.skuCore.sku2info || {};
    const props = res.skuBase.props || [];
    const valMap = {};
    for (const p of props) for (const v of (p.values || [])) valMap[p.pid + ':' + v.vid] = { name: v.name, image: v.image || '' };
    const rows = [];
    for (const s of (res.skuBase.skus || [])) {
      if (String(s.skuId) === '0') continue; // 整品默认行（起步价），跳过
      const info = sku2info[s.skuId] || {};
      const segs = (s.propPath || '').split(';');
      const names = segs.map(seg => (valMap[seg] && valMap[seg].name) || seg);
      const imgSeg = segs.map(seg => valMap[seg]).find(v => v && v.image) || {};
      rows.push({
        skuId: s.skuId,
        skuName: names.join(' + '),
        propPath: s.propPath,
        listPrice: info.price ? info.price.priceText : null,
        promoPrice: info.subPrice ? info.subPrice.priceText : null,
        quantity: info.quantity != null ? info.quantity : null,
        image: imgSeg.image || ''
      });
    }
    const item = res.item || {};
    const seller = res.seller || {};
    const qid = new URLSearchParams(location.search).get('id');
    const itemId = item.itemId || qid;
    return JSON.stringify({
      itemId: itemId,
      title: item.title || document.title.replace(/-.*$/, '').trim(),
      shop: seller.shopName || seller.sellerNick || '',
      url: itemId ? (location.origin + '/item.htm?id=' + itemId) : location.href.split('&spm')[0],
      rows: rows
    });
  } catch (e) { return JSON.stringify({ error: String((e && e.message) || e) }); }
})()
