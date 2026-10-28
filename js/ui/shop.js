/* =========================================================================
 *  shop.js —— 商店 5 张卡（购买 / 悬停 3D 倾斜 / 详情浮层）
 * ========================================================================= */
(function (global) {
  'use strict';

  var JJK = global.JJK = global.JJK || {};
  var U = JJK.util, D = JJK.data, W = JJK.Widgets, h = U.h;

  var app = null, rail = null, lastSig = '';

  function game() { return app.game; }

  function init(appRef) {
    app = appRef;
    rail = document.getElementById('shop-rail');
    rail.addEventListener('click', function (e) {
      var card = e.target.closest('.shop-card');
      if (!card || card.classList.contains('is-empty')) return;
      var idx = +card.dataset.index;
      tryBuy(idx, card);
    });
    rail.addEventListener('mousemove', onTilt);
    rail.addEventListener('mouseleave', function (e) {
      var card = e.target.closest ? e.target.closest('.shop-card') : null;
      if (card) { card.style.setProperty('--rx', '0deg'); card.style.setProperty('--ry', '0deg'); }
      JJK.Tooltip.hide();
    });
  }

  function onTilt(e) {
    var card = e.target.closest('.shop-card');
    if (!card) return;
    var r = card.getBoundingClientRect();
    var px = (e.clientX - r.left) / r.width;
    var py = (e.clientY - r.top) / r.height;
    card.style.setProperty('--ry', ((px - 0.5) * 14).toFixed(2) + 'deg');
    card.style.setProperty('--rx', (-(py - 0.5) * 12).toFixed(2) + 'deg');
    // 光泽跟着指针走
    card.style.setProperty('--mx', (px * 100).toFixed(1) + '%');
    card.style.setProperty('--my', (py * 100).toFixed(1) + '%');
  }

  function tryBuy(idx, card) {
    var g = game();
    if (g.phase !== 'planning') { JJK.Audio.play('deny'); return; }
    var res = g.buyFromShop(idx);
    if (!res.ok) {
      JJK.Audio.play('deny');
      if (res.reason === 'gold') app.toast('金币不足', 'warn');
      else if (res.reason === 'bench') app.toast('备战席已满：先上场或卖掉棋子', 'warn');
      return;
    }
    JJK.Audio.play('buy');
    if (card) {
      card.classList.add('is-bought');
      setTimeout(function () { render(); }, 200);
    }
    if (app && app.markReflow) app.markReflow();
  }

  function cardFor(id, idx) {
    var g = game();
    var u = D.unitById[id];
    var q = D.qualityOf(u.cost);
    var poor = g.gold < u.cost;
    var card = h('div', {
      class: 'shop-card ' + W.qualityClass(u.cost) + ' ' + (poor ? 'is-poor ' : '') + (g.shopLocked ? 'is-locked ' : ''),
      data: { index: idx, unit: id },
      style: '--qc:' + q.color + ';--qg:' + q.glow + ';'
    });
    card.appendChild(h('img', { class: 'sc-art', src: u.card, alt: u.name, draggable: 'false', loading: 'lazy' }));
    card.appendChild(h('div', { class: 'sc-scrim' }));
    card.appendChild(h('div', { class: 'sc-sheen' }));
    card.appendChild(h('div', { class: 'sc-toplight' }));
    card.appendChild(h('div', { class: 'sc-gloss' }));
    card.appendChild(h('div', {
      class: 'sc-rank' + (u.rarity ? ' rar-' + u.rarity : ''),
      text: u.rarity || q.key,
      style: 'background:' + (u.rarityColor || q.color) + ';box-shadow:0 0 12px ' + (u.rarityColor || q.glow) + ';'
    }));
    card.appendChild(h('div', { class: 'sc-cost', text: String(u.cost) }));
    // 四特性徽记（行 / 幻 / 夜 / 影）—— 取代原先的官方强度榜档位
    if (u.element) {
      var em = D.elemMeta(u.element);
      var elEl = h('div', {
        class: 'sc-elem',
        text: em.glyph,
        style: { '--ec': em.color, '--eg': em.glow }
      });
      elEl.title = '特性：' + u.element;
      card.appendChild(elEl);
    }
    // 能和我方已有棋子叠卡 → 高亮闪烁边框
    if (typeof game === 'function') {
      var g = game();
      if (g && g._canMergeIntoExisting && g._canMergeIntoExisting(u.id)) {
        card.classList.add('can-merge');
        card.appendChild(h('div', { class: 'sc-merge-tag', text: '可升星' }));
      }
    }

    var foot = h('div', { class: 'sc-foot' });
    if (u.variant) foot.appendChild(h('div', { class: 'sc-variant', text: '【' + u.variant + '】' }));
    foot.appendChild(h('div', { class: 'sc-name', text: u.baseCharacter || u.name }));
    var tr = h('div', { class: 'sc-traits' });
    (u.traits || []).forEach(function (tid) { tr.appendChild(W.traitChip(tid, false)); });
    foot.appendChild(tr);
    card.appendChild(foot);

    card.appendChild(h('div', { class: 'sc-buy', text: poor ? '金 币 不 足' : '购 买  · ' + u.cost }));

    // 已拥有提示：差一张就能升星时高亮
    var owned = [];
    for (var r = 0; r < g.roster.length; r++) if (g.roster[r].id === id) owned.push(g.roster[r]);
    if (owned.length) {
      var starN = owned.reduce(function (m, x) { return Math.max(m, x.star); }, 1);
      var near = (starN === 1 && owned.length === 2);
      card.appendChild(h('div', {
        class: 'sc-own' + (near ? ' is-near' : ''),
        text: (near ? '差 1 张升星 · ' : '已拥有 ') + owned.length + (starN > 1 ? ' · 最高 ' + starN + '★' : '')
      }));
    }

    card.addEventListener('mouseenter', function () {
      JJK.Tooltip.showUnit(id, card, { star: 1, items: [], showEquipHint: true });
    });
    return card;
  }

  function emptyCard(idx) {
    return h('div', { class: 'shop-card is-empty', data: { index: idx } });
  }

  function render() {
    var g = game();
    var sig = g.shop.join(',') + '|' + g.shopLocked + '|' + g.gold + '|' + g.phase;
    if (sig === lastSig) return;
    lastSig = sig;
    U.clear(rail);
    for (var i = 0; i < 5; i++) {
      var id = g.shop[i];
      var el = null;
      if (id && D.unitById[id]) el = cardFor(id, i);
      else el = emptyCard(i);
      rail.appendChild(el);
      if (el && id) syncLockBadge(el, !!g.shopLocked);
    }
    renderItemRail();
  }

  // 金币变化时只更新"买不起"状态，避免重建卡片打断悬停
  function refreshAffordability() {
    var g = game();
    U.qsa('.shop-card', rail).forEach(function (card) {
      var id = card.dataset.unit;
      if (!id) return;
      var u = D.unitById[id];
      card.classList.toggle('is-poor', g.gold < u.cost);
      var buy = card.querySelector('.sc-buy');
      if (buy) buy.textContent = g.gold < u.cost ? '金 币 不 足' : '购 买  · ' + u.cost;
      card.classList.toggle('is-locked', !!g.shopLocked);
      syncLockBadge(card, !!g.shopLocked);
    });
  }

  // 锁定标记：锁与链条全部画在同一个 SVG 坐标系里（viewBox 100x140）
  var NS_SVG = 'http://www.w3.org/2000/svg';
  function svgEl(tag, attrs) {
    var el = document.createElementNS(NS_SVG, tag);
    for (var k in attrs) if (attrs.hasOwnProperty(k)) el.setAttribute(k, attrs[k]);
    return el;
  }

  function lockSVG() {
    var svg = svgEl('svg', {
      viewBox: '0 0 100 140',
      preserveAspectRatio: 'xMidYMid meet',
      'class': 'sc-lock-svg'
    });
    // SVG 元素上 cssText 在部分 Chromium 版本不稳，用属性 + style 属性字符串
    svg.setAttribute('width', '100%');
    svg.setAttribute('height', '100%');
    svg.setAttribute('style', 'position:absolute;left:0;top:0;width:100%;height:100%;overflow:visible;');

    var CX = 50, CY = 70;

    // ---------- 四条链子：从中心向四角 ----------
    var corners = [[2, 2], [98, 2], [2, 138], [98, 138]];
    corners.forEach(function (c, ci) {
      var dx = c[0] - CX, dy = c[1] - CY;
      var len = Math.sqrt(dx * dx + dy * dy);
      var pitch = 7.0;
      var n = Math.max(3, Math.floor(len / pitch));
      var ang = Math.atan2(dy, dx) * 180 / Math.PI;

      for (var k = 1; k <= n; k++) {
        var t = (k - 0.5) / n;
        var px = CX + dx * t;
        var py = CY + dy * t;
        var along = (k % 2 === 1);
        var el = svgEl('ellipse', {
          cx: px.toFixed(2), cy: py.toFixed(2),
          rx: along ? '3.9' : '2.4',
          ry: along ? '2.3' : '3.8',
          transform: 'rotate(' + ang.toFixed(1) + ' ' + px.toFixed(2) + ' ' + py.toFixed(2) + ')',
          fill: 'none',
          stroke: along ? '#ffeab0' : '#c8b271',
          'stroke-width': '2.1',
          'class': 'sc-chain-link'
        });
        el.style.animationDelay = (ci * 0.05 + t * 0.24).toFixed(3) + 's';
        svg.appendChild(el);
      }
    });

    // ---------- 中央挂锁（画在同一坐标系） ----------
    var g = svgEl('g', { 'class': 'sc-padlock' });
    // 锁梁
    g.appendChild(svgEl('path', {
      d: 'M42 74 V62 a8 8 0 0 1 16 0 V74',
      fill: 'none', stroke: '#8a6512', 'stroke-width': '6.4', 'stroke-linecap': 'round'
    }));
    g.appendChild(svgEl('path', {
      d: 'M42 74 V62 a8 8 0 0 1 16 0 V74',
      fill: 'none', stroke: '#ffd97a', 'stroke-width': '4.0', 'stroke-linecap': 'round'
    }));
    // 锁体
    g.appendChild(svgEl('rect', {
      x: '34', y: '72', width: '32', height: '26', rx: '5',
      fill: '#f3c33f', stroke: '#8a6512', 'stroke-width': '1.8'
    }));
    // 锁体高光
    g.appendChild(svgEl('rect', {
      x: '36.5', y: '74', width: '27', height: '7', rx: '3',
      fill: 'rgba(255,255,255,.35)'
    }));
    // 钥匙孔
    g.appendChild(svgEl('circle', { cx: '50', cy: '83', r: '3.2', fill: '#4a3407' }));
    g.appendChild(svgEl('rect', { x: '48.7', y: '84', width: '2.6', height: '6.6', rx: '1.1', fill: '#4a3407' }));
    svg.appendChild(g);

    return svg;
  }

  function syncLockBadge(card, on) {
    var badge = card.querySelector('.sc-lock');
    if (on && !badge) {
      // 强制让卡片成为定位参照，否则绝对定位会挂到更外层容器上
      if (getComputedStyle(card).position === 'static') card.style.position = 'relative';
      badge = h('div', { class: 'sc-lock' });
      badge.style.cssText = 'position:absolute;left:0;top:0;width:100%;height:100%;' +
                            'pointer-events:none;z-index:9;overflow:visible;transform:none;';
      badge.appendChild(lockSVG());
      card.appendChild(badge);
    } else if (!on && badge) {
      badge.parentNode.removeChild(badge);
    }
  }

  /* ---------------------------------------------------- 咒具栏 ------ */
  function itemById(id) {
    for (var i = 0; i < D.items.length; i++) if (D.items[i].id === id) return D.items[i];
    return null;
  }

  function renderItemRail() {
    var el = document.getElementById('item-rail');
    if (!el) return;
    var g = game();
    if (!g || !g.itemShop) { el.innerHTML = ''; return; }
    var sig = g.itemShop.join(',') + '|' + g.gold + '|' + (g.itemsBag || []).join(',') + '|' + g.phase;
    if (el.dataset.sig === sig) return;
    el.dataset.sig = sig;
    el.innerHTML = '';

    var head = document.createElement('div');
    head.className = 'ir-head';
    head.innerHTML = '<span class="ir-title">咒 具</span><span class="ir-price">' + (g.itemPrice || 3) + ' 金/件</span>';
    el.appendChild(head);

    var grid = document.createElement('div');
    grid.className = 'ir-grid';
    el.appendChild(grid);

    for (var i = 0; i < 3; i++) {
      var id = g.itemShop[i];
      var it = id ? itemById(id) : null;
      var cell = document.createElement('button');
      cell.className = 'ir-item';
      if (!it) {
        cell.classList.add('is-empty');
        cell.disabled = true;
        grid.appendChild(cell);
        continue;
      }
      var craft = g.itemMergeHint ? g.itemMergeHint(id) : null;
      if (craft) cell.classList.add('can-craft');
      var afford = g.gold >= (g.itemPrice || 3);
      if (!afford) cell.classList.add('is-poor');
      cell.title = it.name + ' · ' + it.text + (craft ? ('\n可与已有组件融合成「' + craft.name + '」') : '');
      cell.innerHTML =
        '<img src="assets/items/' + it.icon + '" alt="" draggable="false">' +
        '<span class="ir-name">' + it.name + '</span>' +
        '<span class="ir-cost">' + (g.itemPrice || 3) + '</span>' +
        (craft ? '<span class="ir-craft">可融合</span>' : '');
      (function (idx) {
        cell.addEventListener('click', function () {
          var r = game().buyItemFromShop(idx);
          if (r && r.ok) {
            JJK.Audio.play('buy');
            el.dataset.sig = '';
            renderItemRail();
          } else {
            JJK.Audio.play('deny');
          }
        });
      })(i);
      grid.appendChild(cell);
    }
  }

  function invalidate() { lastSig = ''; }

  JJK.Shop = {
    init: init,
    render: render,
    refreshAffordability: refreshAffordability,
    invalidate: invalidate,
    renderItems: renderItemRail
  };

})(window);
