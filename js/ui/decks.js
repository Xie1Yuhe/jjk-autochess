/**
 *  decks.js —— 卡组选择 / 自定义 / 本地持久化
 *
 *  持久化用 localStorage，不需要任何服务器：
 *    jjk_deckpick : { mode:'preset'|'all'|'custom', id:'...', units:[...] }
 *
 *  弹窗沿用项目里的 #modal-root 机制（class is-open + modal-veil），
 *  否则创建出来的 .modal 是隐藏的——这是之前「点自定义没反应」的原因。
 */
(function (window) {
  'use strict';

  var KEY = 'jjk_deckpick';

  function allDecks() {
    var raw = (window.JJK && JJK.data && JJK.data.raw) || {};
    var d = raw.decks || {};
    return d.decks || [];
  }

  function load() {
    try {
      var s = localStorage.getItem(KEY);
      if (!s) return null;
      var o = JSON.parse(s);
      if (!o || !o.mode) return null;
      return o;
    } catch (e) { return null; }
  }

  function save(obj) {
    try { localStorage.setItem(KEY, JSON.stringify(obj)); } catch (e) {}
  }

  /* ==================================================== 卡组合法性校验 */
  var RULES = {
    size: 36,
    quota: { 1: 8, 2: 8, 3: 8, 4: 8, 5: 4 },
    maxPerChar: 2,
    minTraitsAt3: 3
  };

  function validate(ids) {
    var errs = [];
    var list = [];
    for (var i = 0; i < ids.length; i++) {
      var u = window.JJK.data.unitById[ids[i]];
      if (u) list.push(u);
    }
    if (list.length !== RULES.size) {
      errs.push('必须是 ' + RULES.size + ' 张（当前 ' + list.length + ' 张）');
    }
    var byCost = {}, byChar = {};
    list.forEach(function (u) {
      byCost[u.cost] = (byCost[u.cost] || 0) + 1;
      byChar[u.baseCharacter] = (byChar[u.baseCharacter] || 0) + 1;
    });
    var parts = [];
    for (var c = 1; c <= 5; c++) {
      var want = RULES.quota[c], got = byCost[c] || 0;
      parts.push(c + '费 ' + got + '/' + want);
      if (got !== want) errs.push(c + ' 费必须正好 ' + want + ' 张（当前 ' + got + '）');
    }
    var over = [];
    for (var k in byChar) {
      if (byChar[k] > RULES.maxPerChar) over.push(k + '×' + byChar[k]);
    }
    if (over.length) errs.push('同一角色最多 ' + RULES.maxPerChar + ' 张：' + over.join('、'));
    var tc = {};
    list.forEach(function (u) {
      (u.traits || []).forEach(function (t) { tc[t] = (tc[t] || 0) + 1; });
    });
    var okTraits = 0;
    for (var t in tc) if (tc[t] >= 3) okTraits++;
    if (okTraits < RULES.minTraitsAt3) {
      errs.push('至少 ' + RULES.minTraitsAt3 + ' 条羁绊要能凑到 3 档（当前 ' + okTraits + ' 条）');
    }
    return { ok: errs.length === 0, errors: errs, detail: parts.join(' / ') };
  }

  function distOf(ids) {
    var byCost = {};
    ids.forEach(function (id) {
      var u = window.JJK.data.unitById[id];
      if (u) byCost[u.cost] = (byCost[u.cost] || 0) + 1;
    });
    var parts = [];
    for (var i = 1; i <= 5; i++) parts.push(String(byCost[i] || 0));
    return parts.join(' / ');
  }

  /** 返回 { id, name, units } ；units 为 null 表示全开 */
  function chosen() {
    var pick = load();
    if (!pick || pick.mode === 'all') return { id: '', name: '全部棋子', units: null };
    if (pick.mode === 'custom') {
      var list = (pick.units || []).filter(function (id) {
        return window.JJK.data.unitById[id];
      });
      if (!validate(list).ok) return { id: '', name: '全部棋子', units: null };
      return { id: 'custom', name: '自定义卡组', units: list };
    }
    var d = allDecks().filter(function (x) { return x.id === pick.id; })[0];
    if (!d) return { id: '', name: '全部棋子', units: null };
    return { id: d.id, name: d.name, units: d.units.slice() };
  }

  /* ============================================================ 选择器 */
  var TAG_COLOR = { '行': '#f0a020', '幻': '#e0483c', '夜': '#4fc06a', '影': '#2f5f9e' };

  function renderPicker(host) {
    if (!host) return;
    host.innerHTML = '';
    var pick = load() || { mode: 'preset', id: (allDecks()[0] || {}).id };
    var customOk = (pick.mode === 'custom') && validate(pick.units || []).ok;

    var head = document.createElement('div');
    head.className = 'deck-head';
    head.innerHTML = '<span class="deck-label">棋子卡组</span>' +
                     '<span class="deck-tip">决定商店能刷出哪些棋子 · 自动保存</span>';
    host.appendChild(head);

    var row = document.createElement('div');
    row.className = 'deck-row';

    function card(opts) {
      var b = document.createElement('button');
      b.className = 'deck-card' + (opts.on ? ' is-on' : '');
      b.style.setProperty('--dc', opts.color || '#e8c85a');
      b.innerHTML =
        '<div class="dc-top">' +
          '<span class="dc-name">' + opts.name + '</span>' +
          (opts.badge ? '<span class="dc-badge">' + opts.badge + '</span>' : '') +
        '</div>' +
        '<div class="dc-sub">' + (opts.sub || '') + '</div>' +
        '<div class="dc-dist">' + (opts.dist || '') + '</div>';
      b.addEventListener('click', opts.onClick);
      return b;
    }

    allDecks().forEach(function (d) {
      row.appendChild(card({
        name: d.name,
        badge: d.tag,
        color: TAG_COLOR[d.tag] || '#e8c85a',
        sub: '核心：' + (d.core || []).join(' + '),
        dist: distOf(d.units),
        on: pick.mode === 'preset' && pick.id === d.id,
        onClick: function () {
          save({ mode: 'preset', id: d.id });
          window.JJK.Audio && JJK.Audio.play('click');
          renderPicker(host);
        }
      }));
    });

    row.appendChild(card({
      name: '全部棋子',
      badge: '111',
      color: '#8b95a7',
      sub: '不限制卡池 · 三星更难',
      dist: '22 / 23 / 23 / 22 / 21',
      on: pick.mode === 'all',
      onClick: function () {
        save({ mode: 'all' });
        renderPicker(host);
      }
    }));

    row.appendChild(card({
      name: customOk ? '自定义卡组' : '自定义…',
      badge: customOk ? '36' : '＋',
      color: '#c084fc',
      sub: customOk ? '核心：自选' : '自己挑 36 张（有规则约束）',
      dist: customOk ? distOf(pick.units) : '',
      on: customOk,
      onClick: function () { openEditor(host); }
    }));

    host.appendChild(row);

    var sum = document.createElement('div');
    sum.className = 'deck-summary';
    var c = chosen();
    if (!c.units) {
      sum.classList.add('is-all');
      sum.textContent = '当前：全部 111 张 · 每档约 22 种，合成三星需要约 165 金';
    } else {
      sum.textContent = '当前：' + c.name + ' · ' + c.units.length + ' 张 · 每档约 7 种，合成三星约 58 金';
    }
    host.appendChild(sum);
  }

  /* ============================================================ 编辑器 */
  function openEditor(host) {
    var root = document.getElementById('modal-root');
    if (!root) return;

    var pick = load() || {};
    var cur = (pick.mode === 'custom' && pick.units) ? pick.units.slice() : (chosen().units || []);
    var sel = {};
    cur.forEach(function (id) { sel[id] = 1; });

    function close() {
      root.classList.remove('is-open');
      root.innerHTML = '';
    }

    root.classList.add('is-open');
    root.innerHTML = '';

    var veil = document.createElement('div');
    veil.className = 'modal-veil';
    veil.addEventListener('click', close);
    root.appendChild(veil);

    var modal = document.createElement('div');
    modal.className = 'modal deck-editor';
    modal.innerHTML =
      '<div class="modal-head">' +
        '<div class="modal-title">组 建 卡 组</div>' +
        '<div class="modal-sub">点棋子加入 / 移出 · 必须满足配额才能保存</div>' +
        '<button class="modal-close" id="de-x">✕</button>' +
      '</div>' +
      '<div class="de-bar"><span id="de-count">0</span> / 36' +
      '<span class="de-hint" id="de-hint"></span></div>' +
      '<div class="de-grid" id="de-grid"></div>' +
      '<div class="modal-foot">' +
        '<button class="btn btn-ghost" id="de-clear">清空</button>' +
        '<button class="btn btn-ghost" id="de-copy">复制</button>' +
        '<button class="btn btn-ghost" id="de-paste">粘贴</button>' +
        '<button class="btn btn-gold" id="de-save">保存并使用</button>' +
      '</div>';
    root.appendChild(modal);

    var grid = modal.querySelector('#de-grid');
    var units = window.JJK.data.units.slice().sort(function (a, b) {
      return (a.cost - b.cost) || (a.name < b.name ? -1 : 1);
    });

    function paint() {
      var list = Object.keys(sel);
      var v = validate(list);
      var cnt = modal.querySelector('#de-count');
      cnt.textContent = list.length;
      cnt.style.color = v.ok ? '#7dffc8' : '#ff8fa2';
      var hint = modal.querySelector('#de-hint');
      hint.textContent = v.ok ? ('✓ ' + v.detail + ' · 可以保存')
                              : v.errors[0] + (v.errors.length > 1 ? ' 等 ' + v.errors.length + ' 条' : '');
      hint.style.color = v.ok ? '#7dffc8' : '#ffb27a';
      var btn = modal.querySelector('#de-save');
      btn.disabled = !v.ok;
      btn.style.opacity = v.ok ? 1 : 0.45;

      grid.innerHTML = '';
      units.forEach(function (u) {
        var chip = document.createElement('button');
        chip.className = 'de-chip' + (sel[u.id] ? ' is-on' : '');
        chip.title = u.name + ' · ' + u.cost + '费 ' + u.element;
        chip.innerHTML = '<img src="assets/cards/' + u.id + '.webp" alt="" loading="lazy">' +
                         '<span class="de-cost">' + u.cost + '</span>';
        chip.addEventListener('click', function () {
          if (sel[u.id]) delete sel[u.id]; else sel[u.id] = 1;
          paint();
        });
        grid.appendChild(chip);
      });
    }
    paint();

    modal.querySelector('#de-x').addEventListener('click', close);
    modal.querySelector('#de-clear').addEventListener('click', function () { sel = {}; paint(); });
    modal.querySelector('#de-save').addEventListener('click', function () {
      var list = Object.keys(sel);
      var v = validate(list);
      if (!v.ok) { alert('卡组不合法：\n' + v.errors.join('\n')); return; }
      save({ mode: 'custom', units: list });
      close();
      if (host) renderPicker(host);
      window.JJK.Audio && JJK.Audio.play('click');
    });
    modal.querySelector('#de-copy').addEventListener('click', function () {
      var txt = JSON.stringify(Object.keys(sel));
      try { navigator.clipboard.writeText(txt); } catch (e) {}
      var h = modal.querySelector('#de-hint');
      h.textContent = '已复制 ' + Object.keys(sel).length + ' 张';
      h.style.color = '#7dffc8';
    });
    modal.querySelector('#de-paste').addEventListener('click', function () {
      var s = prompt('粘贴卡组 JSON：["id1","id2",...]');
      if (!s) return;
      try {
        var arr = JSON.parse(s);
        sel = {};
        arr.forEach(function (id) { if (window.JJK.data.unitById[id]) sel[id] = 1; });
        paint();
      } catch (e) { alert('格式不对'); }
    });
  }

  window.JJK = window.JJK || {};
  window.JJK.Decks = {
    load: load, save: save, chosen: chosen,
    renderPicker: renderPicker, openEditor: openEditor, all: allDecks,
    validate: validate, RULES: RULES
  };
})(window);
