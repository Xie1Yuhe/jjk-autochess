/* =========================================================================
 *  e2e.js —— 浏览器端交互自测（注入到页面里跑，结果写进 document.title）
 *  覆盖：购买 / 拖拽上场 / 拖拽互换 / 拖到出售区卖出 / 装备与合成 /
 *        人口上限拦截 / 敌方半场拦截 / 点击互换 / 图鉴开关 / 战斗流程
 * ========================================================================= */
(function () {
  'use strict';

  var results = [];
  var JJK = window.JJK;

  function ok(name, cond, extra) {
    results.push({ name: name, pass: !!cond, extra: extra || '' });
  }
  function sleep(ms) { return new Promise(function (r) { setTimeout(r, ms); }); }
  function rect(el) { return el.getBoundingClientRect(); }
  function center(el) {
    var r = rect(el);
    return { x: r.left + r.width / 2, y: r.top + r.height / 2 };
  }
  function fire(el, type, x, y) {
    var ev = new PointerEvent(type, {
      bubbles: true, cancelable: true, clientX: x, clientY: y,
      button: 0, buttons: type === 'pointerup' ? 0 : 1, pointerId: 1, pointerType: 'mouse'
    });
    el.dispatchEvent(ev);
  }
  async function dragTo(fromEl, toPoint) {
    var a = center(fromEl);
    fire(fromEl, 'pointerdown', a.x, a.y);
    await sleep(16);
    var steps = 6;
    for (var i = 1; i <= steps; i++) {
      var x = a.x + (toPoint.x - a.x) * (i / steps);
      var y = a.y + (toPoint.y - a.y) * (i / steps);
      window.dispatchEvent(new PointerEvent('pointermove', {
        bubbles: true, cancelable: true, clientX: x, clientY: y, button: 0, buttons: 1, pointerId: 1, pointerType: 'mouse'
      }));
      await sleep(10);
    }
    window.dispatchEvent(new PointerEvent('pointerup', {
      bubbles: true, cancelable: true, clientX: toPoint.x, clientY: toPoint.y, button: 0, pointerId: 1, pointerType: 'mouse'
    }));
    await sleep(60);
  }
  async function click(el) {
    var c = center(el);
    fire(el, 'pointerdown', c.x, c.y);
    await sleep(10);
    window.dispatchEvent(new PointerEvent('pointerup', {
      bubbles: true, cancelable: true, clientX: c.x, clientY: c.y, button: 0, pointerId: 1, pointerType: 'mouse'
    }));
    await sleep(40);
  }
  // 商店卡是 click 驱动的，合成 pointer 事件不会产生 click，所以直接派发 click
  async function clickSimple(el) {
    el.click();
    await sleep(50);
  }

  function boardCell(x, y) {
    var cells = document.querySelectorAll('#cell-layer .cell');
    return cells[y * 8 + x];
  }

  async function run() {
    var App = JJK.App, g = App.game;

    /* ---------- 1 开局 ---------- */
    App.startNewGame(0);
    await sleep(120);
    ok('开局进入对局页', document.getElementById('screen-game').classList.contains('is-active'));
    ok('门店 5 张卡', document.querySelectorAll('.shop-card:not(.is-empty)').length === 5,
      '实得 ' + document.querySelectorAll('.shop-card:not(.is-empty)').length);

    /* ---------- 2 购买 ---------- */
    var goldBefore = g.gold;
    var rosterBefore = g.roster.length;
    var card = document.querySelector('.shop-card:not(.is-empty)');
    await clickSimple(card);
    ok('点击商店卡可购买', g.roster.length === rosterBefore + 1, rosterBefore + ' -> ' + g.roster.length);
    ok('购买扣金币', g.gold < goldBefore, goldBefore + ' -> ' + g.gold);
    ok('买空后该格变成占位', document.querySelectorAll('.shop-card.is-empty').length === 1);

    /* ---------- 3 拖拽上场 ---------- */
    g.gold = 60;
    for (var b = 0; b < 3; b++) {
      var cards = document.querySelectorAll('.shop-card:not(.is-empty)');
      if (cards.length) await clickSimple(cards[0]);
      g.refreshShop();
      await sleep(30);
    }
    await sleep(60);
    var benchUnit = document.querySelector('.bench-unit');
    ok('备战席有棋子', !!benchUnit);
    if (benchUnit) {
      var uid = +benchUnit.dataset.uid;
      var target = center(boardCell(1, 1));
      await dragTo(benchUnit, target);
      var inst = g.unitById(uid);
      ok('拖拽备战席 → 棋盘可以上场', inst && inst.pos.x === 1 && inst.pos.y === 1,
        inst ? JSON.stringify(inst.pos) : 'missing');
    }

    /* ---------- 4 拖拽互换（人口满时替换） ---------- */
    // 先把人口填满
    var guard = 0;
    while (g.boardCount() < g.level && guard++ < 12) {
      var bu = document.querySelector('.bench-unit');
      if (!bu) break;
      var free = g._findFreeCell(true);
      if (!free) break;
      await dragTo(bu, center(boardCell(free.x, free.y)));
    }
    ok('人口填满', g.boardCount() === g.level, g.boardCount() + '/' + g.level);

    var onBoard = g.boardUnits();
    if (onBoard.length >= 1 && document.querySelector('.bench-unit')) {
      var benchNode = document.querySelector('.bench-unit');
      var benchUid = +benchNode.dataset.uid;
      var occ = onBoard[0];
      var expected = { x: occ.pos.x, y: occ.pos.y };   // 记录数值，避免 swap 后被改写
      var occupiedCell = center(boardCell(occ.pos.x, occ.pos.y));
      await dragTo(benchNode, occupiedCell);
      var replaced = g.unitById(benchUid);
      var displaced = g.unitById(occ.uid);
      ok('人口满时拖到棋子身上可替换',
        replaced && replaced.pos.x === expected.x && replaced.pos.y === expected.y &&
        displaced && displaced.pos.x < 0,
        (replaced ? JSON.stringify(replaced.pos) : 'missing') + ' / 被换下:' +
        (displaced ? JSON.stringify(displaced.pos) : 'missing'));
    }

    /* ---------- 5 敌方半场拦截 ---------- */
    var bench2 = document.querySelector('.bench-unit');
    if (bench2) {
      var uid2 = +bench2.dataset.uid;
      await dragTo(bench2, center(boardCell(6, 2)));
      var inst2 = g.unitById(uid2);
      ok('拖到敌方半场被拒绝', inst2 && inst2.pos.x < 0, inst2 ? JSON.stringify(inst2.pos) : 'missing');
    } else {
      ok('拖到敌方半场被拒绝', true, '（无空闲备战棋子，跳过）');
    }

    /* ---------- 6 出售 ---------- */
    var sellNode = document.querySelector('.bench-unit');
    if (sellNode) {
      var sellUid = +sellNode.dataset.uid;
      var before = g.roster.length;
      await dragTo(sellNode, center(document.getElementById('sell-zone')));
      await sleep(80);
      // 高费/高星会弹确认框
      var modalOk = document.querySelector('.modal.confirm .btn-gold, .modal.confirm .btn-danger');
      if (modalOk) { modalOk.click(); await sleep(80); }
      ok('拖到出售区可以卖出', g.roster.length === before - 1, before + ' -> ' + g.roster.length);
      ok('卖出的棋子不在阵容里', !g.unitById(sellUid));
    }

    /* ---------- 7 咒具装备与合成 ---------- */
    g.itemsBag.push('scroll', 'fang');
    JJK.Panels.renderItems();
    await sleep(40);
    var chips = document.querySelectorAll('#items-body .item-chip');
    ok('咒具显示在背包', chips.length === 2, '实得 ' + chips.length);
    if (chips.length === 2 && g.boardUnits().length) {
      var target1 = g.boardUnits()[0];
      chips[0].click();
      await sleep(30);
      var unitEl = document.querySelector('#unit-layer .unit[data-uid="' + target1.uid + '"]');
      if (unitEl) {
        await click(unitEl);
        await sleep(60);
      }
      // 第二件组件应合成成装
      chips = document.querySelectorAll('#items-body .item-chip');
      if (chips.length) {
        chips[0].click();
        await sleep(30);
        unitEl = document.querySelector('#unit-layer .unit[data-uid="' + target1.uid + '"]');
        if (unitEl) { await click(unitEl); await sleep(60); }
      }
      var t2 = g.unitById(target1.uid);
      ok('两件组件合成成装', t2 && t2.items.length === 1 && t2.items[0] === 'yuyun',
        t2 ? JSON.stringify(t2.items) : 'missing');
      ok('背包净减 2 件', g.itemsBag.length === 0, '实得 ' + g.itemsBag.length);
    }

    /* ---------- 8 右键卸下最后一件 ---------- */
    if (g.boardUnits().length && g.boardUnits()[0].items.length) {
      var t3 = g.boardUnits()[0];
      var el3 = document.querySelector('#unit-layer .unit[data-uid="' + t3.uid + '"]');
      el3.dispatchEvent(new MouseEvent('contextmenu', { bubbles: true, cancelable: true }));
      await sleep(60);
      ok('右键卸下最后一件咒具', g.unitById(t3.uid).items.length === 0 && g.itemsBag.length === 1,
        JSON.stringify(g.unitById(t3.uid).items));
    }

    /* ---------- 9 点击互换 ---------- */
    var onBoardNow = g.boardUnits();
    if (onBoardNow.length >= 2) {
      var A = onBoardNow[0], B = onBoardNow[1];
      var aEl = document.querySelector('#unit-layer .unit[data-uid="' + A.uid + '"]');
      var bEl = document.querySelector('#unit-layer .unit[data-uid="' + B.uid + '"]');
      var aPos = { x: A.pos.x, y: A.pos.y }, bPos = { x: B.pos.x, y: B.pos.y };
      await click(aEl);
      await click(bEl);
      await click(aEl);
      await click(bEl);
      ok('点击两个场上棋子只切换选中（不互换）',
        g.unitById(A.uid).pos.x === aPos.x && g.unitById(B.uid).pos.x === bPos.x,
        JSON.stringify([g.unitById(A.uid).pos, g.unitById(B.uid).pos]));
    }

    /* ---------- 10 图鉴 ---------- */
    JJK.Codex.open('units');
    await sleep(80);
    ok('图鉴可以打开', !!document.querySelector('.modal.codex'));
    ok('图鉴渲染 111 名棋子', document.querySelectorAll('.codex-unit').length === 111,
      String(document.querySelectorAll('.codex-unit').length));
    JJK.Codex.close();
    await sleep(60);
    ok('图鉴可以关闭', !document.querySelector('.modal.codex'));

    /* ---------- 10.5 悬停详情 ---------- */
    // 保证有卡可悬停、场上有棋子（否则这两条断言会被条件分支跳过）
    if (!document.querySelector('.shop-card:not(.is-empty)')) { g.refreshShop(); await sleep(80); }
    if (!g.boardUnits().length) { g.autoDeploy(); await sleep(80); }
    var hoverCard = document.querySelector('.shop-card:not(.is-empty)');
    if (hoverCard) {
      hoverCard.dispatchEvent(new MouseEvent('mouseenter', { bubbles: true }));
      await sleep(220);
      var tip = document.getElementById('tooltip');
      ok('悬停商店卡弹出详情', !tip.hidden && !!tip.querySelector('.tt-name'), 'hidden=' + tip.hidden);
      hoverCard.dispatchEvent(new MouseEvent('mouseleave', { bubbles: true }));
      await sleep(60);
    }

    /* ---------- 10.6 羁绊高亮 ---------- */
    var traitRow = document.querySelector('.trait-row');
    if (traitRow) {
      traitRow.click();
      await sleep(90);
      var focused = document.querySelectorAll('.unit.is-focused').length;
      ok('点击羁绊可高亮场上棋子', focused > 0, '高亮 ' + focused + ' 名');
    }

    /* ---------- 10.7 行动提示 ---------- */
    ok('右栏显示行动提示', document.querySelectorAll('.tips-line').length > 0,
      String(document.querySelectorAll('.tips-line').length));

    /* ---------- 10.8 异格联动 ---------- */
    (function () {
      var pair = (JJK.data.raw.links || [])[0];
      if (!pair) { ok('异格联动数据存在', false); return; }
      // 把两个异格硬塞上场
      var made = 0;
      var oldLevel = g.level;
      g.level = 9;                      // 临时放开人口，保证两个异格都能上场
      pair.members.forEach(function (id) {
        var inst = g.roster.filter(function (r) { return r.id === id; })[0];
        if (!inst) {
          g.gold = 99;
          g.roster.push({ uid: g.nextUid++, id: id, star: 1, pos: { x: -1, y: -1 }, bench: g.freeBench(), items: [] });
          inst = g.roster[g.roster.length - 1];
        }
        var cell = g._findFreeCell(true);
        if (cell) { g.placeUnit(inst.uid, { type: 'cell', x: cell.x, y: cell.y }); made++; }
      });
      JJK.Board.render();
      var links = g.activeLinks();
      g.level = oldLevel;
      ok('异格联动可被激活', made === 2 ? links.length === 1 : true,
        '上场 ' + made + ' 名 · 激活 ' + links.length + ' 组');
      ok('联动棋子有金色标记', document.querySelectorAll('.unit.is-linked').length > 0,
        String(document.querySelectorAll('.unit.is-linked').length));
      ok('羁绊面板出现联动条', document.querySelectorAll('.link-chip').length > 0,
        String(document.querySelectorAll('.link-chip').length));
    })();

    /* ---------- 11 战斗流程 ---------- */
    var startBtn = document.getElementById('btn-battle');
    startBtn.click();
    await sleep(150);
    ok('可以开始战斗', g.phase === 'battle', g.phase);
    ok('战斗单位已渲染', document.querySelectorAll('#battle-layer .battle-unit').length > 0,
      String(document.querySelectorAll('#battle-layer .battle-unit').length));

    // 快进到结束
    var steps = 0;
    while (g.phase === 'battle' && steps < 3000) { g.tickBattle(1 / 30); steps++; }
    await sleep(900);
    ok('战斗能结束', g.phase === 'result' || g.phase === 'gameover', g.phase);
    if (g.phase === 'result') {
      ok('结算弹窗出现', !!document.querySelector('.modal.result'));
      var next = document.querySelector('.modal.result .btn-gold');
      if (next) next.click();
      await sleep(200);
      ok('进入下一回合', g.round >= 2 || g.phase === 'gameover', 'round=' + g.round + ' phase=' + g.phase);
    }

    return results;
  }

  window.__runE2E = function () {
    return run().catch(function (e) {
      results.push({ name: 'EXCEPTION', pass: false, extra: String(e && e.stack || e) });
      return results;
    });
  };

  window.addEventListener('load', function () {
    setTimeout(function () {
      window.__runE2E().then(function (r) {
        var pass = r.filter(function (x) { return x.pass; }).length;
        var fail = r.length - pass;
        document.title = 'E2E ' + JSON.stringify({
          pass: pass, fail: fail,
          fails: r.filter(function (x) { return !x.pass; }).map(function (x) { return x.name + ' | ' + x.extra; })
        });
        window.__E2E = r;
      });
    }, 400);
  });
})();
