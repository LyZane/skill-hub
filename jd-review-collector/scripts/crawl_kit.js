/* jd-review-collector: in-page hook + crawler. Inject once via javascript_tool.
 * Usage after injection:
 *   window.__runs.media = window.__mkRun('media');          // create a run
 *   window.__crawl('media', 5, 50);                          // (name, maxPages, maxCount)
 *   window.__runStatus();                                    // poll progress
 * Optional: window.__recvUrl = 'http://127.0.0.1:18923';    // receiver base (default shown)
 */
(function () {
  if (window.__jdRevKit) return 'kit already installed';
  window.__jdRevKit = true;
  var RECV = window.__recvUrl || 'http://127.0.0.1:18923';

  window.__rateReq = [];
  var XS = XMLHttpRequest.prototype.send, XO = XMLHttpRequest.prototype.open;
  XMLHttpRequest.prototype.open = function (m, u) { this.__url = u; return XO.apply(this, arguments); };
  XMLHttpRequest.prototype.send = function (body) {
    var xhr = this, u = xhr.__url || '';
    if (u.indexOf('api.m.jd.com') >= 0 && typeof body === 'string' && body.indexOf('pc-rate-qa') >= 0) {
      var entry = { body: body.slice(0, 4000), resp: null };
      window.__rateReq.push(entry);
      xhr.addEventListener('load', function () { entry.resp = (xhr.responseText || '').slice(0, 300000); });
    }
    return XS.apply(this, arguments);
  };

  window.__post = function (name, pageNum, comments) {
    try {
      fetch(RECV + '/run_' + name, {
        method: 'POST',
        headers: { 'Content-Type': 'text/plain' },
        body: JSON.stringify({ run: name, pageNum: pageNum, comments: comments })
      }).then(function () { window.__lastPost = 'ok p' + pageNum; })
        .catch(function (e) { window.__lastPost = 'fail p' + pageNum + ':' + e; });
    } catch (e) { window.__lastPost = 'ex p' + pageNum + ':' + e; }
  };

  window.__mkRun = function (name) {
    return { name: name, processed: 0, comments: {}, order: [], pageNum: 0, hasNext: true, maxPage: null, errors: [], done: false };
  };

  window.__crawl = function (name, maxPages, maxCount) {
    var st = window.__runs[name];
    (async function () {
      var c = findScrollContainer();
      var idle = 0;
      while (!st.done) {
        var progressed = false;
        while (st.processed < window.__rateReq.length) {
          var got = window.__rateReq[st.processed++];
          progressed = true;
          try {
            var sp = new URLSearchParams(got.body);
            var b = JSON.parse(sp.get('body'));
            var pageNum = parseInt(b.pageNum) || 1;
            var j = JSON.parse(got.resp);
            got.resp = null;
            var listFloor = null;
            for (var k = 0; k < j.result.floors.length; k++) {
              if (j.result.floors[k].mId === 'commentlist-list') { listFloor = j.result.floors[k]; break; }
            }
            var arr = (listFloor && listFloor.data) || [];
            var fresh = [];
            for (var i = 0; i < arr.length; i++) {
              var ci = arr[i].commentInfo;
              if (ci && ci.commentId && !st.comments[ci.commentId]) {
                st.comments[ci.commentId] = ci; st.order.push(ci.commentId); fresh.push(ci);
              }
            }
            if (fresh.length) window.__post(name, pageNum, fresh);
            st.pageNum = Math.max(st.pageNum, pageNum);
            var pi = j.result.pageInfo && j.result.pageInfo.data;
            if (pi) { st.hasNext = !!pi.hasNextPage; if (pi.maxPage) st.maxPage = parseInt(pi.maxPage); }
            if (!st.hasNext || st.order.length >= maxCount || (st.maxPage && st.pageNum >= st.maxPage) || st.pageNum >= maxPages) { st.done = true; break; }
          } catch (e) { st.errors.push('p' + st.pageNum + ':' + String(e).slice(0, 80)); }
        }
        if (st.done) break;
        if (progressed) { idle = 0; await sleep(3000 + Math.floor(Math.random() * 2000)); continue; }
        idle++;
        if (idle > 5) { st.errors.push('idle stop at page ' + st.pageNum + ' count ' + st.order.length); st.done = true; break; }
        if (c) c.scrollTop = c.scrollHeight;
        await sleep(3500 + Math.floor(Math.random() * 2000));
      }
    })();
    return 'started ' + name;
  };

  function sleep(ms) { return new Promise(function (r) { setTimeout(r, ms); }); }

  /* locate overlay inner scroll container without hard-coded hash classnames */
  function findScrollContainer() {
    var ov = document.querySelector('.jdc-page-overlay');
    if (!ov) return null;
    var found = null;
    (function walk(el) {
      for (var i = 0; i < el.children.length; i++) {
        var c = el.children[i];
        var cs = getComputedStyle(c);
        if ((cs.overflowY === 'auto' || cs.overflowY === 'scroll') && c.scrollHeight > c.clientHeight + 10) { found = c; return; }
        walk(c); if (found) return;
      }
    })(ov);
    return found;
  }

  window.__runStatus = function () {
    var out = {};
    for (var k in window.__runs) {
      var s = window.__runs[k];
      out[k] = { count: s.order.length, pageNum: s.pageNum, maxPage: s.maxPage, hasNext: s.hasNext, done: s.done, lastPost: window.__lastPost || null, errors: s.errors.slice(-3) };
    }
    return JSON.stringify(out);
  };
  return 'kit installed';
})();
