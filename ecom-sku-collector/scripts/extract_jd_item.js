(() => {
  try {
    const txt = el => el ? el.innerText.trim() : null;
    const skuId = (location.pathname.match(/(\d+)/) || [])[1] || new URLSearchParams(location.search).get('sku');
    if (!skuId) return JSON.stringify({ error: 'no skuId in url', url: location.href });
    // 价格面板：主价格 + 口径标签（到手价/补贴价/PLUS价）+ 划线原价
    const priceBox = document.querySelector('.page-right-price') || document.querySelector('[class*="price-panel"]');
    let price = null, priceTag = null, listPrice = null;
    if (priceBox) {
      price = txt(priceBox.querySelector('.product-price--value'));
      priceTag = txt(priceBox.querySelector('.product-price--activity-item--tag'));
      listPrice = (txt(priceBox.querySelector('.product-price--gray-line-through')) || '').replace(/[¥￥]/, '');
    }
    if (!price) return JSON.stringify({ error: 'price panel not found (页面未加载完或结构变化)', skuId, url: location.href });
    // 规格选项：京东变体是独立商品页，此处仅记录选项名与缩略图（无 skuId 映射）
    const variants = Array.from(document.querySelectorAll('.specification-item-sku')).map(e => {
      const img = e.querySelector('img');
      return { name: txt(e), selected: e.className.includes('selected'), image: img ? img.src : null };
    });
    const selected = variants.find(v => v.selected) || null;
    const shopA = document.querySelector('a[href*="mall.jd.com"], a[href*="shop.jd.com"]');
    let mainImg = null;
    const gal = document.querySelector('[class*="preview"] img, [class*="gallery"] img, .spec-items img, [class*="main-img"] img');
    if (gal) mainImg = gal.src || gal.getAttribute('data-origin');
    if (!mainImg && selected) mainImg = selected.image;
    return JSON.stringify({
      platform: 'jd',
      itemId: skuId,
      title: txt(document.querySelector('.sku-title-name')) || document.title.replace(/【[^】]*】.*$/, '').trim(),
      url: 'https://item.jd.com/' + skuId + '.html',
      shop: shopA ? txt(shopA) : null,
      shopId: shopA ? (shopA.href.match(/index-(\d+)/) || [])[1] || null : null,
      commentCount: txt(document.querySelector('.product-price-panel--options-comment-count')),
      variants: variants,
      rows: [{
        skuId: skuId,
        skuName: selected ? selected.name : (txt(document.querySelector('.sku-title-name')) || ''),
        listPrice: listPrice || null,
        promoPrice: price,
        priceTag: priceTag,
        quantity: null,
        image: (selected && selected.image) || mainImg || ''
      }]
    });
  } catch (e) { return JSON.stringify({ error: String((e && e.message) || e) }); }
})()
