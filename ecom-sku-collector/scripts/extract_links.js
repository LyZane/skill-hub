(() => {
  const out = [];
  const seen = new Set();
  document.querySelectorAll('a[href*="item.htm"], a[href*="item.taobao.com"], a[href*="detail.tmall.com"]').forEach(a => {
    const u = a.href;
    const m = u && u.match(/[?&]id=(\d+)/);
    if (m && !seen.has(m[1])) {
      seen.add(m[1]);
      out.push('https://detail.tmall.com/item.htm?id=' + m[1]);
    }
  });
  if (out.length === 0) {
    // 兜底：扫描页面文本中的商品 id
    const m = (document.documentElement.innerHTML.match(/[?&]id=(\d{6,})/g) || []);
    m.forEach(s => {
      const id = s.replace(/^[?&]id=/, '');
      if (!seen.has(id)) { seen.add(id); out.push('https://detail.tmall.com/item.htm?id=' + id); }
    });
  }
  return JSON.stringify({ count: out.length, links: out });
})()
