// 在语雀文档页面内通过 javascript_tool 执行。
// 自读 window.appData 取 slug/book_id；解压 lakesheet body；提取单元格/合并/列带色。
// 第一次调用返回 JSON 长度，第二次调用 `window.__extract` 取回全文。
(async () => {
  const A = window.appData;
  const slug = A.doc.slug, bookId = A.book.id;
  const r = await fetch(`/api/docs/${slug}?book_id=${bookId}&merge_dynamic_data=false`, { headers: { accept: 'application/json' } });
  const d = (await r.json()).data;
  const obj = JSON.parse(d.body);
  const sheetStr = obj.sheet;
  const bytes = new Uint8Array(sheetStr.length);
  for (let i = 0; i < sheetStr.length; i++) bytes[i] = sheetStr.charCodeAt(i) & 0xff;
  const text = await new Response(new Blob([bytes]).stream().pipeThrough(new DecompressionStream('deflate'))).text();
  const sh = JSON.parse(text)[0];
  const styles = (sh.vStore && sh.vStore.style) || [];
  const backColors = (sh.vStore && sh.vStore.style_backColor) || [];

  let maxR = 0, maxC = 0;
  for (const [rk, row] of Object.entries(sh.data || {})) {
    for (const [ck, cell] of Object.entries(row)) {
      const v = cell && cell.v;
      if (v !== undefined && v !== null && v !== '') { maxR = Math.max(maxR, +rk); maxC = Math.max(maxC, +ck); }
    }
  }

  const out = { title: A.doc.title, backColors, cells: [], merges: [] };
  for (const m of Object.values(sh.mergeCells || {})) out.merges.push([m.row, m.col, m.rowCount, m.colCount]);
  for (let r0 = 0; r0 <= maxR; r0++) {
    const row = sh.data[String(r0)]; if (!row) continue;
    for (let c0 = 0; c0 <= maxC; c0++) {
      const cell = row[String(c0)];
      if (!cell || cell.v === undefined || cell.v === null || cell.v === '') continue;
      const v = cell.v;
      let val;
      if (typeof v === 'object') {
        if (v.class === 'image') val = { img: v.src };
        else if (v.class === 'link') val = { link: v.text };
        else continue;
      } else val = v;
      const bm = (styles[cell.s] || '').match(/_b(\d+)/);
      out.cells.push([r0, c0, val, bm ? +bm[1] : -1]);
    }
  }
  window.__extract = JSON.stringify(out);
  return window.__extract.length;
})()
