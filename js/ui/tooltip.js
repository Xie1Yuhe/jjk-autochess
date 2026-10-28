/* =========================================================================
 *  tooltip.js —— 详情浮层（棋子 / 咒具 / 羁绊）
 *  鼠标悬停 90ms 后弹出；触摸端点击弹出。位置自动避让视口边缘。
 * ========================================================================= */
(function (global) {
  'use strict';

  var JJK = global.JJK = global.JJK || {};
  var U = JJK.util, D = JJK.data, W = JJK.Widgets, h = U.h;

  var el = null, timer = null, current = null;

  function ensure() {
    if (!el) el = document.getElementById('tooltip');
    return el;
  }

  function place(anchorEl) {
    var t = ensure();
    if (!t || !anchorEl) return;
    var r = anchorEl.getBoundingClientRect();
    var tw = t.offsetWidth || 322;
    var th = t.offsetHeight || 300;
    var vw = global.innerWidth, vh = global.innerHeight;

    var left = r.right + 12;
    if (left + tw > vw - 10) left = r.left - tw - 12;
    if (left < 10) left = Math.min(vw - tw - 10, Math.max(10, r.left));

    var top = r.top + r.height / 2 - th / 2;
    top = Math.max(10, Math.min(vh - th - 10, top));

    t.style.left = Math.round(left) + 'px';
    t.style.top = Math.round(top) + 'px';
  }

  function show(node, anchorEl, wide) {
    var t = ensure();
    if (!t) return;
    U.clear(t);
    t.appendChild(node);
    t.hidden = false;
    t.classList.toggle('is-wide', !!wide);
    place(anchorEl);
    // 内容高度可能变化，下一帧再校正一次
    requestAnimationFrame(function () { place(anchorEl); });
  }

  function hide() {
    if (timer) { clearTimeout(timer); timer = null; }
    var t = ensure();
    if (t) { t.hidden = true; U.clear(t); }
    current = null;
  }

  function schedule(anchorEl, build, wide) {
    if (timer) clearTimeout(timer);
    timer = setTimeout(function () {
      var node = build();
      if (node) show(node, anchorEl, wide);
    }, 90);
  }

  /* ------------------------------------------------------------ 棋子 */
  function unitNode(unitId, opts) {
    opts = opts || {};
    var u = D.unitById[unitId];
    if (!u) return null;

    var star = opts.star || 1;
    var items = opts.items || [];
    var q = D.qualityOf(u.cost);
    var st = D.statsAtStar(u, star);
    var skill = u.skill || {};
    var pas = u.passive || {};
    var stype = D.SKILL_TYPES[skill.type] || { label: skill.type || '—', glyph: '技', color: '#b18cff' };
    var ptype = D.PASSIVE_TYPES[pas.kind || pas.type] || { label: '被动', glyph: '被', color: '#c084fc' };

    var node = h('div', null, []);

    /* 头部 */
    var head = h('div', {
      class: 'tt-head ' + W.qualityClass(u.cost) + ' ' + W.elementClass(u.element),
      style: '--qc:' + q.color + ';--qg:' + q.glow + ';'
    });

    var bg = h('div', { class: 'tt-bg' });
    bg.style.backgroundImage = 'url("' + u.card + '")';
    head.appendChild(bg);
    head.appendChild(h('div', { class: 'tt-shade' }));

    var port = h('div', { class: 'tt-portrait' });
    port.style.borderColor = q.color;
    port.style.boxShadow = '0 0 18px ' + q.glow;
    port.appendChild(h('img', { src: u.icon, alt: u.name, draggable: 'false' }));
    head.appendChild(port);

    var box = h('div', { class: 'tt-title-box' });
    box.appendChild(h('div', { class: 'tt-name', text: u.name }));
    // 注：原先这里显示官方攻略评价（wikiComment，形如「⭕拥有领域展开⭕…」），
    // 作者要求删除 —— 攻略评价属于外部观点，和棋子自身的机制说明不是一回事。
    // 属性克制（行→幻→夜→影→行）
    var EL = JJK.data.raw.elements;
    if (EL && u.element) {
      var beatsMap = {};
      EL.cycle.forEach(function (c) { beatsMap[c.from] = c.to; });
      var beatenBy = {};
      EL.cycle.forEach(function (c) { beatenBy[c.to] = c.from; });
      var line = h('div', { class: 'tt-elem-line' });
      if (beatsMap[u.element]) {
        line.appendChild(h('span', { class: 'te-win', text: '克 ' + beatsMap[u.element] }));
      }
      if (beatenBy[u.element]) {
        line.appendChild(h('span', { class: 'te-lose', text: '被 ' + beatenBy[u.element] + ' 克' }));
      }
      if (line.childNodes.length) box.appendChild(line);
    }
    // 注：原先这里显示官方强度榜档位（SSS/SS/S/A/B/C），
    // 那是《幻影夜行》的 PVE 排行，跟本作的棋子强度无关，已删除。
    var meta = h('div', { class: 'tt-meta' });
    meta.appendChild(h('span', { class: 'tt-cost', text: u.cost + ' 费' }));
    var rank = h('span', { class: 'tt-rank', text: u.rarity || q.key });
    rank.style.cssText = 'background:' + (u.rarityColor || q.color) + ';box-shadow:0 0 12px ' + (u.rarityColor || q.glow) + ';';
    meta.appendChild(rank);
    if (star > 1) meta.appendChild(W.starRow(star));
    box.appendChild(meta);
    head.appendChild(box);
    node.appendChild(head);

    var body = h('div', { class: 'tt-body' });

    /* 羁绊 */
    var tr = h('div', { class: 'tt-traits' });
    (u.traits || []).forEach(function (tid) {
      tr.appendChild(W.traitChip(tid, false));
    });
    tr.appendChild(h('span', { class: 'tag-role', text: u.dmg || '' }));
    tr.appendChild(h('span', { class: 'tag-role', text: u.role || '' }));
    body.appendChild(tr);

    /* 属性 */
    var stats = h('div', { class: 'tt-stats' });
    var base = D.statsAtStar(u, 1);
    stats.appendChild(W.statCell('生命', st.hp, st.hp > base.hp));
    stats.appendChild(W.statCell('体术', st.ad, st.ad > base.ad));
    stats.appendChild(W.statCell('术式', st.spell, st.spell > base.spell));
    stats.appendChild(W.statCell('攻速', st.as.toFixed(2), false));
    stats.appendChild(W.statCell('射程', st.range, false));
    stats.appendChild(W.statCell('咒力', st.start_mana + '/' + st.mana, false));
    if (u.ultCost) stats.appendChild(W.statCell('必杀值', String(u.ultCost), false));
    body.appendChild(stats);

    /* 技能 */
    var sb = h('div', { class: 'tt-block is-skill', style: '--bc:' + stype.color });
    var sh = h('div', { class: 'b-head' });
    var sg = h('span', { class: 'b-glyph', text: stype.glyph });
    sg.style.background = stype.color;
    sh.appendChild(sg);
    sh.appendChild(h('span', { class: 'b-name', text: skill.name || '—' }));
    sh.appendChild(h('span', { class: 'b-type', text: stype.label + (skill.power ? ' ×' + skill.power : '') }));
    sb.appendChild(sh);
    sb.appendChild(h('div', { class: 'b-desc', text: skill.desc || '' }));
    body.appendChild(sb);

    /* 必杀 */
    if (u.ult && u.ult.combat) {
      var ub = h('div', { class: 'tt-block is-ult', style: '--bc:#ffb020' });
      var uh = h('div', { class: 'b-head' });
      var ug = h('span', { class: 'b-glyph', text: '杀' });
      ug.style.background = '#ffb020';
      uh.appendChild(ug);
      uh.appendChild(h('span', { class: 'b-name', text: u.ult.name || '必杀' }));
      uh.appendChild(h('span', { class: 'b-type', text: '必杀值 ' + (u.ultCost || 100) }));
      ub.appendChild(uh);
      ub.appendChild(h('div', { class: 'b-desc', text: u.ult.desc || '' }));
      body.appendChild(ub);
    }

    /* 被动 */
    if (pas.name) {
      var pb = h('div', { class: 'tt-block is-passive', style: '--bc:' + ptype.color });
      var ph = h('div', { class: 'b-head' });
      var pg = h('span', { class: 'b-glyph', text: ptype.glyph });
      pg.style.background = ptype.color;
      ph.appendChild(pg);
      ph.appendChild(h('span', { class: 'b-name', text: pas.name }));
      ph.appendChild(h('span', { class: 'b-type', text: ptype.label }));
      pb.appendChild(ph);
      pb.appendChild(h('div', { class: 'b-desc', text: pas.desc || '' }));
      body.appendChild(pb);
    }

    /* 咒具 */
    if (items.length) {
      var iw = h('div', { class: 'tt-items' });
      items.forEach(function (iid) {
        iw.appendChild(W.itemChip(iid));
      });
      items.forEach(function (iid) {
        var it = D.itemById[iid];
        if (it) iw.appendChild(h('span', { class: 'tt-note', text: it.name }));
      });
      body.appendChild(iw);
    } else if (opts.showEquipHint) {
      body.appendChild(h('div', { class: 'tt-note', text: '未装备咒具 · 从右侧咒具栏点选后再点此棋子即可装备' }));
    }

    if (opts.bagHint) body.appendChild(h('div', { class: 'tt-bag-tip', text: '点击装备到选中的棋子' }));

    node.appendChild(body);
    return node;
  }

  /* ------------------------------------------------------------ 咒具 */
  function itemNode(itemId) {
    var it = D.itemById[itemId];
    if (!it) return null;
    var meta = D.itemMeta(itemId);
    var node = h('div', null, []);
    var head = h('div', { class: 'tt-head' });
    head.style.cssText = '--qc:' + meta.color + ';--qg:' + meta.color + '44;';
    var port = h('div', { class: 'tt-portrait', style: 'border-color:' + meta.color + ';box-shadow:0 0 18px ' + meta.color + '55;' });
    if (it.icon) {
      var art = h('img', {
        src: 'assets/items/' + it.icon, alt: it.name, draggable: 'false',
        style: 'width:100%;height:100%;object-fit:cover;border-radius:inherit'
      });
      port.appendChild(art);
    } else {
      var glyph = h('div', {
        style: {
          width: '100%', height: '100%', display: 'grid', placeItems: 'center',
          fontFamily: 'var(--font-display)', fontWeight: '900', fontSize: '26px',
          color: meta.color, background: 'rgba(0,0,0,.45)',
          textShadow: '0 0 16px ' + meta.color
        },
        text: meta.glyph
      });
      port.appendChild(glyph);
    }
    head.appendChild(port);
    var box = h('div', { class: 'tt-title-box' });
    box.appendChild(h('div', { class: 'tt-name', text: it.name, style: 'font-size:15px' }));
    box.appendChild(h('div', {
      class: 'tt-title',
      text: it.kind === 'complete' ? '成装 · 由两件组件合成' : '组件 · 可与另一件组件合成'
    }));
    head.appendChild(box);
    node.appendChild(head);

    var body = h('div', { class: 'tt-body' });
    var stat = it.stat || {};
    var stats = h('div', { class: 'tt-stats' });
    var labels = { hp: '生命', ad: '攻击', spell: '术式', as: '攻速', start_mana: '初始咒力', armor: '减伤', domain_plus: '领域提前' };
    var any = false;
    Object.keys(stat).forEach(function (k) {
      any = true;
      var v = stat[k];
      if (k === 'as') v = '+' + Math.round(v * 100) + '%';
      else if (k === 'armor') v = '+' + v + '%';
      else if (k === 'domain_plus') v = '-' + v + 's';
      else v = '+' + v;
      stats.appendChild(W.statCell(labels[k] || k, v, true));
    });
    if (any) body.appendChild(stats);
    body.appendChild(h('div', { class: 'tt-note', text: it.text || '' }));
    if (it.recipe && it.recipe.length) {
      var rec = h('div', { class: 'tt-items' });
      it.recipe.forEach(function (r) {
        rec.appendChild(W.itemChip(r));
        rec.appendChild(h('span', { class: 'tt-note', text: '+' }));
      });
      rec.appendChild(h('span', { class: 'tt-bag-tip', text: '同装在一个棋子上自动合成' }));
      body.appendChild(rec);
    }
    node.appendChild(body);
    return node;
  }

  /* ------------------------------------------------------------ 羁绊 */
  function traitNode(traitId, count) {
    var info = D.traitById[traitId];
    if (!info) return null;
    var color = D.traitColor(traitId);
    var tiers = info.tiers || [];
    var level = 0;
    tiers.forEach(function (t, i) { if ((count || 0) >= t.count) level = i + 1; });

    var node = h('div', null, []);
    var head = h('div', { class: 'tt-head' });
    var port = h('div', {
      class: 'tt-portrait',
      style: 'border-color:' + color + ';box-shadow:0 0 18px ' + color + '55;'
    });
    port.appendChild(h('div', {
      style: {
        width: '100%', height: '100%', display: 'grid', placeItems: 'center',
        fontFamily: 'var(--font-display)', fontWeight: '900', fontSize: '26px',
        color: color, background: 'rgba(0,0,0,.45)', textShadow: '0 0 16px ' + color
      },
      text: info.glyph || info.name[0]
    }));
    head.appendChild(port);
    var box = h('div', { class: 'tt-title-box' });
    box.appendChild(h('div', { class: 'tt-name', text: info.name, style: 'font-size:15px' }));
    box.appendChild(h('div', {
      class: 'tt-title',
      text: ({ element: '元素羁绊', class: '职业羁绊', faction: '阵营羁绊' })[info.type] || '羁绊'
    }));
    head.appendChild(box);
    node.appendChild(head);

    var body = h('div', { class: 'tt-body' });
    var list = h('div', null, []);
    tiers.forEach(function (t, i) {
      var on = (count || 0) >= t.count;
      var row = h('div', { class: 'tt-tier' + (on ? ' on' : ''), style: '--tc:' + color });
      var n = h('span', { class: 't-count', text: t.count + ' 人' });
      if (on) n.style.cssText = 'background:' + color + ';color:#08060e;font-weight:700;';
      row.appendChild(n);
      row.appendChild(h('span', { class: 't-text', text: t.text }));
      list.appendChild(row);
    });
    body.appendChild(list);
    body.appendChild(h('div', {
      class: 'tt-note',
      text: '当前场上 ' + (count || 0) + ' 名 · ' + (level > 0 ? '已激活 ' + level + ' 档' : '尚未激活'),
      style: 'margin-top:6px;color:' + (level > 0 ? color : 'var(--text-faint)')
    }));
    node.appendChild(body);
    return node;
  }

  /* ------------------------------------------------------------ 对外 */
  function bindHover(anchorEl, build, wide) {
    function enter() { schedule(anchorEl, build, wide); }
    function leave() { if (current !== anchorEl) hide(); }
    anchorEl.addEventListener('mouseenter', enter);
    anchorEl.addEventListener('mouseleave', leave);
    anchorEl.addEventListener('pointerdown', function () {
      // 触摸端：点一下就展示
      if (global.matchMedia && global.matchMedia('(hover: none)').matches) {
        var node = build();
        if (node) { show(node, anchorEl, wide); current = anchorEl; }
      }
    });
  }

  /* ------------------------------------------------------------ 联动 */
  function linkNode(L) {
    var node = h('div', null, []);
    var head = h('div', { class: 'tt-head' });
    head.style.cssText = '--qc:' + L.color + ';--qg:' + L.color + '55;';
    var port = h('div', { class: 'tt-portrait', style: 'border-color:' + L.color + ';box-shadow:0 0 18px ' + L.color + '66;' });
    port.appendChild(h('div', {
      style: {
        width: '100%', height: '100%', display: 'grid', placeItems: 'center',
        fontFamily: 'var(--font-display)', fontWeight: '900', fontSize: '22px',
        color: L.color, background: 'rgba(0,0,0,.5)', textShadow: '0 0 16px ' + L.color
      },
      text: L.short
    }));
    head.appendChild(port);
    var box = h('div', { class: 'tt-title-box' });
    box.appendChild(h('div', { class: 'tt-name', text: L.name, style: 'font-size:15px;color:' + L.color }));
    box.appendChild(h('div', { class: 'tt-title', text: '异格联动 · ' + L.base }));
    head.appendChild(box);
    node.appendChild(head);
    var body = h('div', { class: 'tt-body' });
    body.appendChild(h('div', { class: 'tt-block', style: '--bc:' + L.color }, [
      h('div', { class: 'b-head' }, [
        (function () { var g = h('span', { class: 'b-glyph', text: '联' }); g.style.background = L.color; return g; })(),
        h('span', { class: 'b-name', text: L.mechanic || '机制联动' })
      ]),
      h('div', { class: 'b-desc', text: L.desc })
    ]));
    var mem = h('div', { class: 'tt-items' });
    (L.memberNames || []).forEach(function (n) { mem.appendChild(h('span', { class: 'chip', style: '--tc:' + L.color, text: n })); });
    body.appendChild(mem);
    node.appendChild(body);
    return node;
  }

  JJK.Tooltip = {
    showLink: function (L, anchorEl) {
      var node = linkNode(L);
      if (node) show(node, anchorEl, true);
    },
    init: function () { ensure(); },
    showUnit: function (unitId, anchorEl, opts) {
      current = anchorEl;
      schedule(anchorEl, function () { return unitNode(unitId, opts); });
    },
    showUnitNow: function (unitId, anchorEl, opts) {
      var node = unitNode(unitId, opts);
      if (node) show(node, anchorEl, true);
    },
    showItem: function (itemId, anchorEl) {
      current = anchorEl;
      schedule(anchorEl, function () { return itemNode(itemId); });
    },
    showItemNow: function (itemId, anchorEl) {
      var node = itemNode(itemId);
      if (node) show(node, anchorEl);
    },
    showTrait: function (traitId, count, anchorEl) {
      current = anchorEl;
      schedule(anchorEl, function () { return traitNode(traitId, count); });
    },
    bindHover: bindHover,
    hide: hide,
    unitNode: unitNode,
    itemNode: itemNode,
    traitNode: traitNode
  };

})(window);
