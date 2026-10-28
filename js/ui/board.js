/* =========================================================================
 *  board.js —— 棋盘 / 备战席渲染 + 拖拽交互
 *  交互语言：
 *   · 拖动：原位置留残影，跟随鼠标的是放大克隆体 + 名字牌
 *   · 落点三色：绿=空位 / 紫=替换或互换 / 红=非法（敌方半场）/ 橙=人口已满
 *   · 点击 A → 点击 B：一上一下互换；都在场上只切换选中
 *   · 右键棋子卸下最后一件咒具；Delete 卖掉选中棋子
 * ========================================================================= */
(function (global) {
  'use strict';

  var JJK = global.JJK = global.JJK || {};
  var U = JJK.util, D = JJK.data, W = JJK.Widgets, h = U.h;

  var app = null;
  var boardEl, cellLayer, unitLayer, previewLayer, benchEl, sellEl, ghostEl;
  var previewSig = '';
  var cells = [];         // 32 个 .cell
  var slots = [];         // 9 个 .bench-slot
  var unitEls = {};       // uid -> element（棋盘）
  var benchUnitEls = {};  // uid -> element（备战席）

  var drag = null;        // 拖拽会话
  var focusTimer = null;

  function game() { return app.game; }

  /* ============================================================== 初始化 */
  function init(appRef) {
    app = appRef;
    boardEl = document.getElementById('board');
    cellLayer = document.getElementById('cell-layer');
    unitLayer = document.getElementById('unit-layer');
    previewLayer = document.getElementById('preview-layer');
    benchEl = document.getElementById('bench');
    sellEl = document.getElementById('sell-zone');
    ghostEl = document.getElementById('drag-ghost');

    buildCells();
    buildBench();

    document.addEventListener('pointerdown', onDocPointerDown, true);
    window.addEventListener('pointermove', onPointerMove, { passive: false });
    window.addEventListener('pointerup', onPointerUp);
    window.addEventListener('pointercancel', onPointerUp);
    window.addEventListener('contextmenu', function (e) {
      if (e.target.closest('.unit, .bench-unit')) e.preventDefault();
    });
  }

  function buildCells() {
    U.clear(cellLayer);
    cells = [];
    for (var y = 0; y < 4; y++) {
      for (var x = 0; x < 8; x++) {
        var c = h('div', { class: 'cell' + (x >= 4 ? ' foe' : ''), data: { x: x, y: y } });
        cellLayer.appendChild(c);
        cells.push(c);
      }
    }
    cellLayer.addEventListener('click', function (e) {
      var cell = e.target.closest('.cell');
      if (!cell) return;
      var x = +cell.dataset.x, y = +cell.dataset.y;
      if (x >= 4) return;
      var sel = game().selectedUid;
      if (sel >= 0 && game().phase === 'planning') {
        doPlace(sel, { type: 'cell', x: x, y: y });
      }
    });
  }

  function buildBench() {
    U.clear(benchEl);
    slots = [];
    for (var i = 0; i < 9; i++) {
      var s = h('div', { class: 'bench-slot', data: { index: i, num: String(i + 1) } });
      benchEl.appendChild(s);
      slots.push(s);
    }
  }

  function cellAt(x, y) { return cells[y * 8 + x]; }

  /* ============================================================== 渲染 */
  function render() {
    var g = game();
    if (!g) return;
    if (g.phase === 'battle') {
      unitLayer.hidden = true;
      if (previewLayer) previewLayer.hidden = true;
      return;
    }
    unitLayer.hidden = false;
    if (previewLayer) previewLayer.hidden = false;

    var boardUnits = g.boardUnits();
    var seen = {};

    boardUnits.forEach(function (inst) {
      seen[inst.uid] = true;
      var el = unitEls[inst.uid];
      if (!el) {
        el = createUnitEl(inst, true);
        unitEls[inst.uid] = el;
        unitLayer.appendChild(el);
      }
      updateUnitEl(el, inst);
      el.style.transform = 'translate3d(' + (inst.pos.x * 100) + '%,' + (inst.pos.y * 100) + '%,0)';
      // 用百分比位移，避免依赖 JS 读取格子像素
    });
    Object.keys(unitEls).forEach(function (uid) {
      if (!seen[uid]) {
        var el = unitEls[uid];
        if (el && el.parentNode) el.parentNode.removeChild(el);
        delete unitEls[uid];
      }
    });

    renderPreview();
    renderBench();
  }

  /* 敌方半场的对手情报 */
  function renderPreview() {
    if (!previewLayer) return;
    var g = game();
    var p = (g.phase === 'planning') ? g.opponentPreview() : null;
    if (!p) { U.clear(previewLayer); previewSig = ''; return; }

    var sig = p.units.map(function (u) { return u.id + '@' + u.pos.x + ',' + u.pos.y + '*' + u.star; }).join('|');
    if (sig === previewSig) return;
    previewSig = sig;
    U.clear(previewLayer);

    p.units.forEach(function (u) {
      var el = h('div', {
        class: 'unit pv',
        style: { transform: 'translate3d(' + (u.pos.x * 100) + '%,' + (u.pos.y * 100) + '%,0)' }
      });
      var data = D.unitById[u.id];
      if (data) {
        el.appendChild(W.unitToken(data, u.star || 1, [], { showItems: false, showElement: false }));
        el.addEventListener('mouseenter', function () {
          JJK.Tooltip.showUnitNow(u.id, el, { star: u.star || 1, items: [] });
        });
      } else {
        el.appendChild(W.curseToken(u.name || '咒灵'));
        el.addEventListener('mouseenter', function () {
          JJK.Tooltip.showUnitNow('', el, {});
        });
      }
      el.appendChild(h('div', { class: 'pv-name', text: (data ? data.baseCharacter || data.name : (u.name || '咒灵')) + (u.star > 1 ? ' ★' + u.star : '') }));
      el.addEventListener('mouseleave', function () { JJK.Tooltip.hide(); });
      previewLayer.appendChild(el);
    });
  }

  function renderBench() {
    var g = game();
    var bySlot = {};
    g.benchUnits().forEach(function (inst) { bySlot[inst.bench] = inst; });

    var seen = {};
    for (var i = 0; i < 9; i++) {
      var slot = slots[i];
      var inst = bySlot[i];
      var existing = slot.querySelector('.bench-unit');
      if (!inst) {
        if (existing) existing.parentNode.removeChild(existing);
        continue;
      }
      seen[inst.uid] = true;
      var el = existing;
      if (!el || el.dataset.uid !== String(inst.uid)) {
        if (el) el.parentNode.removeChild(el);
        el = createUnitEl(inst, false);
        slot.appendChild(el);
      }
      el.dataset.uid = String(inst.uid);
      updateUnitEl(el, inst);
    }
    Object.keys(benchUnitEls).forEach(function (k) { delete benchUnitEls[k]; });
  }

  function createUnitEl(inst, isBoard) {
    var u = D.unitById[inst.id];
    var el = h('div', {
      class: (isBoard ? 'unit' : 'bench-unit') + ' ' + W.qualityClass(u.cost) + ' ' + W.elementClass(u.element),
      data: { uid: String(inst.uid) }
    });
    el.appendChild(W.unitToken(u, inst.star, inst.items, { showItems: true }));
    bindUnitEvents(el, inst.uid);
    if (!isBoard) {
      // 备战席元素需要独立定位
      el.style.position = 'absolute';
      el.style.inset = '0';
    }
    return el;
  }

  function updateUnitEl(el, inst) {
    var u = D.unitById[inst.id];
    var token = el.querySelector('.token');
    var key = u.id + '|' + inst.star + '|' + (inst.items || []).join(',');
    if (el.dataset.sig !== key) {
      el.dataset.sig = key;
      var fresh = W.unitToken(u, inst.star, inst.items, { showItems: true });
      if (token) el.replaceChild(fresh, token);
      else el.appendChild(fresh);
    }
    el.classList.toggle('is-selected', game().selectedUid === inst.uid);
    el.classList.toggle('is-linked', !!game().isLinkedUnit(inst.id));
  }

  function bindUnitEvents(el, uid) {
    el.addEventListener('mouseenter', function () {
      var inst = game().unitById(uid);
      if (!inst) return;
      JJK.Tooltip.showUnit(inst.id, el, {
        star: inst.star, items: inst.items, showEquipHint: true
      });
      JJK.Audio.play('hover');
    });
    el.addEventListener('mouseleave', function () { JJK.Tooltip.hide(); });
    el.addEventListener('contextmenu', function (e) {
      e.preventDefault();
      var res = game().unequipLast(uid);
      if (res && res.ok) {
        JJK.Audio.play('equip');
        app.toast('已卸下最后一件咒具', '');
      } else {
        JJK.Audio.play('deny');
        app.toast('这枚棋子没有装备咒具', 'warn');
      }
    });
    el.addEventListener('dblclick', function (e) {
      e.preventDefault();
      var inst = game().unitById(uid);
      if (!inst || game().phase !== 'planning') return;
      if (inst.pos.x >= 0) return;
      var cell = game()._findFreeCell(D.unitById[inst.id].range <= 1);
      if (cell) doPlace(uid, { type: 'cell', x: cell.x, y: cell.y });
    });
  }

  /* ============================================================== 拖拽 */
  function onDocPointerDown(e) {
    if (e.button !== 0) return;
    var el = e.target.closest('.unit, .bench-unit');
    if (!el) return;
    if (!game() || game().phase !== 'planning') return;
    var uid = +el.dataset.uid;
    var inst = game().unitById(uid);
    if (!inst) return;
    // 咒具已就绪：点击即装备
    if (game().pendingItem) {
      e.preventDefault();
      e.stopPropagation();
      var r = game().equipItem(uid, game().pendingItem);
      if (r.ok) {
        JJK.Audio.play(r.crafted ? 'upgrade' : 'equip');
        if (r.crafted) JJK.FX.shake(6);
        app.toast(r.crafted ? '咒具合成成功：' + r.crafted.name : '咒具已装备', 'gold');
      } else {
        JJK.Audio.play('deny');
        if (r.reason === 'full') app.toast('该棋子已带满 3 件咒具', 'warn');
      }
      return;
    }
    drag = {
      uid: uid,
      el: el,
      startX: e.clientX,
      startY: e.clientY,
      moved: false,
      from: inst.pos.x >= 0 ? { type: 'cell', x: inst.pos.x, y: inst.pos.y } : { type: 'bench', index: inst.bench },
      pointerId: e.pointerId
    };
    JJK.Tooltip.hide();
  }

  function onPointerMove(e) {
    if (!drag) return;
    var dx = e.clientX - drag.startX;
    var dy = e.clientY - drag.startY;
    if (!drag.moved && Math.abs(dx) + Math.abs(dy) < 7) return;

    if (!drag.moved) {
      drag.moved = true;
      beginDrag();
    }
    e.preventDefault();
    moveGhost(e.clientX, e.clientY);
    updateDropHints(e.clientX, e.clientY);
  }

  function beginDrag() {
    var inst = game().unitById(drag.uid);
    if (!inst) return;
    var u = D.unitById(inst.id);
    drag.el.classList.add('is-dragging');

    U.clear(ghostEl);
    ghostEl.appendChild(h('div', { class: 'dg-name', text: u.name + (inst.star > 1 ? '  ' + '★'.repeat(inst.star) : '') }));
    ghostEl.appendChild(W.unitToken(u, inst.star, inst.items, { showItems: true }));
    ghostEl.appendChild(h('div', {
      class: 'dg-sub',
      text: game().pendingItem ? '' : (inst.pos.x >= 0 ? '松开以移动 / 互换' : '松开以上场')
    }));
    ghostEl.hidden = false;
    document.body.classList.add('is-dragging');
    JJK.Audio.play('click');
  }

  function moveGhost(x, y) {
    ghostEl.style.transform = 'translate(' + x + 'px,' + y + 'px) translate(-50%, -50%) scale(1.12) rotate(1.5deg)';
  }

  function clearHints() {
    cells.forEach(function (c) { c.classList.remove('dz-ok', 'dz-swap', 'dz-bad', 'dz-cap'); });
    slots.forEach(function (s) { s.classList.remove('dz-ok'); });
    sellEl.classList.remove('is-hot');
  }

  function updateDropHints(x, y) {
    clearHints();
    var g = game();
    if (isOverSell(x, y)) { sellEl.classList.add('is-hot'); return; }

    var b = benchIndexAt(x, y);
    if (b >= 0) {
      slots[b].classList.add('dz-ok');
      return;
    }
    var c = cellFromPoint(x, y);
    if (!c) return;
    var cell = cellAt(c.x, c.y);
    if (!cell) return;
    if (c.x >= 4) { cell.classList.add('dz-bad'); return; }
    var occupant = g.unitAtCell(c.x, c.y);
    if (occupant && occupant.uid !== drag.uid) { cell.classList.add('dz-swap'); return; }
    var inst = g.unitById(drag.uid);
    if (inst && inst.pos.x < 0 && g.boardCount() >= g.level) { cell.classList.add('dz-cap'); return; }
    cell.classList.add('dz-ok');
  }

  function onPointerUp(e) {
    if (!drag) return;
    var d = drag;
    drag = null;
    clearHints();
    ghostEl.hidden = true;
    document.body.classList.remove('is-dragging');
    if (d.el) d.el.classList.remove('is-dragging');

    if (!d.moved) {
      // 点击：选中 / 互换
      handleClick(d.uid);
      return;
    }
    var x = e.clientX, y = e.clientY;

    if (isOverSell(x, y)) { app.requestSell(d.uid); return; }

    var b = benchIndexAt(x, y);
    if (b >= 0) { doPlace(d.uid, { type: 'bench', index: b }); return; }

    var c = cellFromPoint(x, y);
    if (!c) { render(); return; }
    if (c.x >= 4) {
      JJK.Audio.play('deny');
      app.toast('只能放在己方半场（左侧 4 列）', 'warn');
      render();
      return;
    }
    doPlace(d.uid, { type: 'cell', x: c.x, y: c.y });
  }

  function handleClick(uid) {
    var g = game();
    if (g.phase !== 'planning') return;
    var prev = g.selectedUid;
    var inst = g.unitById(uid);
    if (!inst) return;

    if (prev === uid) {
      g.selectedUid = -1;
      JJK.Audio.play('click');
      render();
      app.renderDetail();
      return;
    }
    if (prev >= 0 && prev !== uid) {
      var a = g.unitById(prev);
      if (a) {
        var aBoard = a.pos.x >= 0, bBoard = inst.pos.x >= 0;
        if (!(aBoard && bBoard)) {
          g.swapUnits(prev, uid);
          g.selectedUid = uid;
          JJK.Audio.play('place');
          render();
          app.renderDetail();
          return;
        }
      }
    }
    g.selectedUid = uid;
    JJK.Audio.play('click');
    render();
    app.renderDetail();
  }

  function doPlace(uid, dest) {
    var g = game();
    var prevPos = null;
    var inst = g.unitById(uid);
    if (inst) prevPos = inst.pos.x >= 0 ? { x: inst.pos.x, y: inst.pos.y } : null;
    var res = g.placeUnit(uid, dest);
    if (!res.ok) {
      JJK.Audio.play('deny');
      if (res.reason === 'cap') app.toast('人口已满：拖到场上棋子身上可直接替换', 'warn');
      else if (res.reason === 'territory') app.toast('只能放在己方半场', 'warn');
      render();
      return;
    }
    g.selectedUid = uid;
    JJK.Audio.play('place');
    if (dest.type === 'cell') JJK.FX.burst({ x: dest.x, y: dest.y }, 'rgba(139,92,246,0.8)');
    render();
    app.renderDetail();
  }

  /* ============================================================== 坐标 */
  function cellFromPoint(cx, cy) {
    var r = boardEl.getBoundingClientRect();
    if (cx < r.left || cy < r.top || cx > r.right || cy > r.bottom) return null;
    var x = Math.floor(((cx - r.left) / r.width) * 8);
    var y = Math.floor(((cy - r.top) / r.height) * 4);
    return { x: U.clamp(x, 0, 7), y: U.clamp(y, 0, 3) };
  }

  function benchIndexAt(cx, cy) {
    for (var i = 0; i < slots.length; i++) {
      var r = slots[i].getBoundingClientRect();
      if (cx >= r.left && cx <= r.right && cy >= r.top && cy <= r.bottom) return i;
    }
    return -1;
  }

  function isOverSell(cx, cy) {
    var r = sellEl.getBoundingClientRect();
    return cx >= r.left && cx <= r.right && cy >= r.top && cy <= r.bottom;
  }

  /* ============================================================== 高亮 */
  function focusTrait(traitId, ms) {
    var g = game();
    var ids = [];
    g.boardUnits().forEach(function (inst) {
      if ((D.unitById[inst.id].traits || []).indexOf(traitId) >= 0) ids.push(inst.uid);
    });
    if (focusTimer) clearTimeout(focusTimer);
    Object.keys(unitEls).forEach(function (uid) {
      var el = unitEls[uid];
      if (!el) return;
      if (ids.indexOf(+uid) >= 0) el.classList.add('is-focused');
      else el.classList.remove('is-focused');
    });
    focusTimer = setTimeout(function () {
      Object.keys(unitEls).forEach(function (uid) {
        if (unitEls[uid]) unitEls[uid].classList.remove('is-focused');
      });
    }, ms || 2800);
    return ids.length;
  }

  function getUnitEl(uid) {
    return unitEls[uid] || (benchEl.querySelector('.bench-unit[data-uid="' + uid + '"]'));
  }

  function setBenchSlotHot(index, on) {
    if (slots[index]) slots[index].classList.toggle('dz-ok', on);
  }

  JJK.Board = {
    init: init,
    render: render,
    cellFromPoint: cellFromPoint,
    benchIndexAt: benchIndexAt,
    isOverSell: isOverSell,
    focusTrait: focusTrait,
    getUnitEl: getUnitEl,
    clearHints: clearHints
  };

})(window);
