/* =========================================================================
 *  widgets.js —— 复用型 UI 构件（棋子令牌 / 星级 / 咒具 / 羁绊标签 / 列表协调）
 * ========================================================================= */
(function (global) {
  'use strict';

  var JJK = global.JJK = global.JJK || {};
  var U = JJK.util;
  var D = JJK.data;
  var h = U.h;

  /* ------------------------------------------------------------ 工具 */
  function qualityClass(cost) { return 'q-' + D.qualityOf(cost).key; }

  function elementClass(element) {
    var e = D.ELEMENTS[element];
    if (!e) return 'el-curse';
    return 'el-' + e.key;
  }

  function elementColor(element) {
    var e = D.ELEMENTS[element];
    return e ? e.color : '#e46a96';
  }

  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  /* ------------------------------------------------------------ 咒灵令牌 */
  // PvE 敌人没有立绘：用纯 CSS 画一张"咒灵面具"，比占位文字好看得多
  function curseToken(name) {
    var hue = 344;
    for (var i = 0; i < (name || '').length; i++) hue = (hue + (name.charCodeAt(i) % 23) * 3) % 360;
    if (hue > 60 && hue < 300) hue = 344;     // 只保留红紫区间，避免变成绿色咒灵
    var token = h('div', { class: 'token curse-token q-B', style: '--h:' + hue + ';--qc:#9aa3b2;--qg:rgba(154,163,178,.3);' });
    token.appendChild(h('div', { class: 'ct-aura' }));
    token.appendChild(h('span', { class: 'ct-eye l' }));
    token.appendChild(h('span', { class: 'ct-eye r' }));
    token.appendChild(h('span', { class: 'ct-mouth' }));
    token.appendChild(h('span', { class: 'ct-mark', text: '咒' }));
    token.appendChild(h('div', { class: 'tk-ring' }));
    return token;
  }

  /* ------------------------------------------------------------ 星级 */
  function starRow(n, cls) {
    var wrap = h('span', { class: 'tk-stars ' + (cls || '') });
    for (var i = 0; i < n; i++) wrap.appendChild(h('i', { class: 'tk-star' + (n >= 3 ? ' big' : '') }));
    return wrap;
  }

  /* ------------------------------------------------------------ 令牌 */
  // opts: { image: 'card'|'icon', showQuality, showElement, showItems, showStars, items, star, unit }
  function unitToken(unit, star, items, opts) {
    opts = opts || {};
    var q = D.qualityOf(unit.cost);
    var token = h('div', {
      class: 'token ' + qualityClass(unit.cost) + ' ' + elementClass(unit.element),
      style: { '--qc': q.color, '--qg': q.glow }
    });

    var img = h('img', {
      src: opts.image === 'icon' ? unit.icon : unit.card,
      alt: unit.name,
      loading: 'lazy',
      draggable: 'false'
    });
    token.appendChild(img);
    token.appendChild(h('div', { class: 'tk-scrim' }));
    token.appendChild(h('div', { class: 'tk-ring' }));

    if (opts.showQuality !== false) {
      // 角标显示**品质**（R / SR / SSR），而不是按费用分档的 B/A/S/SS。
      // 费用仍然由左上角的金色数字圈表达；老数据没有 rarity 字段时回退到旧字母。
      var rar = unit.rarity || (q.key === 'SS' ? 'SSR' : (q.key === 'S' ? 'SR' : 'R'));
      var rarColor = unit.rarityColor || q.color;
      token.appendChild(h('span', {
        class: 'tk-q' + (rar.length >= 3 ? ' l3' : (rar.length === 2 ? ' l2' : '')),
        text: rar,
        style: { '--qc': rarColor, '--qg': rarColor + 'aa' }
      }));
    }
    if (opts.showElement !== false) {
      var el = D.ELEMENTS[unit.element];
      token.appendChild(h('span', {
        class: 'tk-el',
        text: el ? el.glyph : '咒',
        title: unit.element,
        style: { '--ec': elementColor(unit.element) }
      }));
    }
    if (opts.showStars !== false && star > 1) token.appendChild(starRow(star));

    if (opts.showItems && items && items.length) {
      var wrap = h('div', { class: 'tk-items' });
      for (var i = 0; i < items.length; i++) {
        var meta = D.itemMeta(items[i]);
        wrap.appendChild(h('span', {
          class: 'tk-item',
          text: meta.glyph,
          style: { background: 'linear-gradient(180deg,' + meta.color + ',#8a6a1a)' }
        }));
      }
      token.appendChild(wrap);
    }
    return token;
  }

  /* ------------------------------------------------------------ 咒具 */
  function itemChip(itemId, opts) {
    opts = opts || {};
    var it = D.itemById[itemId];
    var meta = D.itemMeta(itemId);
    var el = h('div', {
      class: 'item-chip' + (it && it.kind === 'complete' ? ' is-complete' : '') + (opts.armed ? ' is-armed' : ''),
      style: { '--ic': meta.color },
      text: (it && it.icon) ? '' : meta.glyph,
      title: it ? it.name : itemId
    });
    if (it && it.icon) {
      el.appendChild(h('img', { class: 'ic-art', src: 'assets/items/' + it.icon, alt: it.name, draggable: 'false' }));
    }
    el.dataset.item = itemId;
    if (opts.count) el.appendChild(h('span', { class: 'ic-count', text: String(opts.count) }));
    return el;
  }

  /* ------------------------------------------------------------ 羁绊标签 */
  function traitChip(traitId, active, count) {
    var info = D.traitById[traitId];
    var color = D.traitColor(traitId);
    var label = (info ? info.name : traitId) + (count !== undefined ? ' ' + count : '');
    return h('span', {
      class: 'chip' + (active ? ' is-active' : ''),
      style: { '--tc': color },
      text: label
    });
  }

  /* ------------------------------------------------------------ 列表协调 */
  // 复用已有 DOM，避免每次刷新都重建（保留 CSS 过渡与焦点）
  function reconcile(container, items, keyFn, createFn, updateFn) {
    var existing = {};
    for (var i = 0; i < container.children.length; i++) {
      var c = container.children[i];
      if (c.dataset && c.dataset.key !== undefined) existing[c.dataset.key] = c;
    }
    var used = {};
    for (var j = 0; j < items.length; j++) {
      var key = String(keyFn(items[j], j));
      used[key] = true;
      var el = existing[key];
      if (!el) {
        el = createFn(items[j], j);
        el.dataset.key = key;
        container.appendChild(el);
      }
      if (updateFn) updateFn(el, items[j], j);
      // 保持顺序
      if (container.children[j] !== el) {
        var ref = container.children[j] || null;
        if (ref !== el) container.insertBefore(el, ref);
      }
    }
    for (var k in existing) {
      if (existing.hasOwnProperty(k) && !used[k]) {
        if (existing[k].parentNode) existing[k].parentNode.removeChild(existing[k]);
      }
    }
  }

  /* ------------------------------------------------------------ 其它 */
  function statCell(label, value, boost) {
    return h('div', { class: 'tt-stat' + (boost ? ' is-boost' : '') }, [
      h('span', { class: 's-label', text: label }),
      h('span', { class: 's-value', text: String(value) })
    ]);
  }

  function fmtPct(v) { return Math.round(v * 100) + '%'; }

  JJK.Widgets = {
    h: h,
    qualityClass: qualityClass,
    elementClass: elementClass,
    elementColor: elementColor,
    escapeHtml: escapeHtml,
    starRow: starRow,
    unitToken: unitToken,
    curseToken: curseToken,
    itemChip: itemChip,
    traitChip: traitChip,
    reconcile: reconcile,
    statCell: statCell,
    fmtPct: fmtPct
  };

})(window);
