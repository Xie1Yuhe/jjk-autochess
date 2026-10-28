/* playtest.js —— 像玩家一样把游戏真打几局，抓「不符合预期」的问题
 *
 * 不是单元测试：这里走的是**真实页面 + 真实按钮 + 真实回合流程**，
 * 只断言「玩家视角能不能正常玩下去」和「数值有没有明显发疯」。
 *
 * 输出：document.title = PLAYTEST {json}
 */
(function () {
  var errors = [];
  var warns = [];
  var rounds = [];
  window.addEventListener('error', function (e) {
    errors.push('JS: ' + e.message + ' @' + (e.filename || '').split('/').pop() + ':' + e.lineno);
  });
  window.addEventListener('unhandledrejection', function (e) {
    errors.push('Promise: ' + (e.reason && e.reason.message ? e.reason.message : String(e.reason)));
  });
  var _ce = console.error;
  console.error = function () {
    errors.push('console.error: ' + Array.prototype.join.call(arguments, ' ').slice(0, 200));
    _ce.apply(console, arguments);
  };

  function W(msg) { warns.push(msg); }
  function num(v) { return typeof v === 'number' && isFinite(v); }

  function sleep(ms) { return new Promise(function (r) { setTimeout(r, ms); }); }

  function snapshot(tag) {
    var App = window.JJK && window.JJK.App;
    var g = App && App.game;
    if (!g) return { tag: tag, dead: true };
    var bad = [];
    if (!num(g.gold) || g.gold < 0) bad.push('gold=' + g.gold);
    if (!num(g.hp) || g.hp <= 0) bad.push('hp=' + g.hp);
    if (!num(g.round)) bad.push('round=' + g.round);
    if (g.gold > 200) bad.push('gold 异常膨胀=' + g.gold);
    if (g.level < 1 || g.level > 9) bad.push('level=' + g.level);

    var board = g.boardUnits ? g.boardUnits() : [];
    var bench = g.benchUnits ? g.benchUnits() : [];
    var all = board.concat(bench);
    var dupUid = {}, dup = 0;
    all.forEach(function (u) {
      if (!u) return;
      if (dupUid[u.uid]) dup++;
      dupUid[u.uid] = 1;
    });
    if (dup) bad.push('同一棋子出现 ' + dup + ' 次');
    if (board.length > g.cap) bad.push('上场数 ' + board.length + ' > 人口 ' + g.cap);

    // 状态面板必须和真实状态一致
    var hudGold = document.getElementById('hud-gold');
    if (hudGold && String(g.gold) !== hudGold.textContent.trim()) {
      bad.push('HUD 金币 ' + hudGold.textContent.trim() + ' ≠ 实际 ' + g.gold);
    }

    return {
      tag: tag, phase: g.phase, round: g.round, gold: g.gold, hp: g.hp,
      level: g.level, board: board.length, bench: bench.length, cap: g.cap,
      shop: (g.shop || []).filter(Boolean).length,
      bad: bad
    };
  }

  /** 玩家会做的事：买得起就买、能升级就升级、满了就卖、然后上阵 */
  function actLikePlayer() {
    var App = window.JJK.App, g = App.game;
    // 1) 买经验（前期优先）
    if (g.gold >= 14 && g.level < 8 && g.round < 9) {
      try { g.buyExp(); } catch (e) { errors.push('buyExp: ' + e.message); }
    }
    // 2) 买卡：从便宜到贵
    // 注意：buyFromShop 收的是**商店索引**，不是棋子 id
    var idx = [];
    (g.shop || []).forEach(function (id, i) { if (id) idx.push(i); });
    idx.sort(function (a, b) {
      var da = window.JJK.data.unitById[g.shop[a]], db = window.JJK.data.unitById[g.shop[b]];
      return (da ? da.cost : 9) - (db ? db.cost : 9);
    });
    idx.forEach(function (i) {
      var id = g.shop[i];
      if (!id) return;
      var d = window.JJK.data.unitById[id];
      if (!d) { errors.push('商店出现未知棋子 ' + id); return; }
      if (g.gold - d.cost < 2) return;
      if (g.benchUnits().length >= 9) return;
      try {
        var r = g.buyFromShop(i);
        if (r && r.ok === false && r.reason && r.reason !== 'gold' && r.reason !== 'full') {
          W('买卡被拒: ' + d.name + ' → ' + r.reason);
        }
      } catch (e) { errors.push('buy: ' + d.name + ' ' + e.message); }
    });
    // 3) 上阵（如果 autoDeploy 没把人放上去，手动塞一个，否则打不了）
    try { g.autoDeploy(); } catch (e) { errors.push('autoDeploy: ' + e.message); }
    if (!g.boardUnits().length) {
      var bench = g.benchUnits();
      if (bench.length) {
        try {
          for (var cx = 0; cx < 4 && !g.boardUnits().length; cx++) {
            for (var cy = 0; cy < 2; cy++) {
              if (g.canPlaceAt && g.canPlaceAt(cx, cy)) {
                g.placeUnit(bench[0].uid, cx, cy);
                break;
              }
            }
          }
        } catch (e) { errors.push('placeUnit: ' + e.message); }
      }
      if (!g.boardUnits().length) W('R' + g.round + ' 上了阵但还是空场（bench=' + bench.length + '，gold=' + g.gold + '）');
    }
    // 4) 装备
    if (g.itemsBag && g.itemsBag.length) {
      var board = g.boardUnits();
      for (var i = 0; i < Math.min(2, g.itemsBag.length); i++) {
        var u = board[i % Math.max(1, board.length)];
        if (!u) break;
        try { g.equip ? g.equip(u.uid, g.itemsBag[0]) : null; } catch (e) { errors.push('equip: ' + e.message); }
      }
    }
  }

  async function playOneGame(gameIdx) {
    var App = window.JJK.App;
    // 等主程序 boot 完（虚拟时钟下 rAF/setTimeout 推进很快，固定等一拍最稳）
    if (gameIdx === 0) await sleep(2600);
    try { App.startNewGame(1); } catch (e) { errors.push('startNewGame: ' + e.message); return null; }
    await sleep(120);

    var g = App.game;
    if (!g) { errors.push('startNewGame 后没有 game 对象'); return null; }
    try { App.setSpeed(4); } catch (e) { errors.push('开局后设速度失败: ' + e.message); }

    var startHp = g.hp;
    var guard = 0;
    while (g && g.phase !== 'over' && g.round <= 22 && guard++ < 40) {
      actLikePlayer();
      var s = snapshot('R' + g.round + '-plan');
      rounds.push(s);

      var btn = document.getElementById('btn-battle');
      if (!btn) { errors.push('找不到开始战斗按钮'); break; }
      if (btn.disabled) W('R' + g.round + ' 开始战斗按钮是禁用的');
      try { btn.click(); } catch (e) { errors.push('click battle: ' + e.message); break; }

      // 等战斗结束（速度 4x）
      var wait = 0;
      while (App.game && App.game.phase !== 'planning' && App.game.phase !== 'over' && wait < 260) {
        await sleep(50); wait++;
      }
      if (wait >= 260) { errors.push('R' + g.round + ' 战斗卡住没结束'); break; }
      await sleep(80);
      var after = snapshot('R' + (App.game ? App.game.round : '?') + '-after');
      rounds.push(after);
      if (!App.game || App.game.phase === 'over') break;
    }

    return {
      game: gameIdx,
      reachedRound: g ? g.round : -1,
      hpStart: startHp,
      hpEnd: g ? g.hp : -1,
      over: !g || g.phase === 'over'
    };
  }

  (async function () {
    try {
      // 等主程序挂载好（main.js 是异步 boot 的）
      var App = null, tries = 0;
      while (!App && tries++ < 120) {
        App = window.JJK && window.JJK.App;
        if (!App) await sleep(50);
      }
      if (!App || !App.setSpeed) {
        document.title = 'PLAYTEST ' + JSON.stringify({ fatal: 'App 未就绪', hasJJK: !!window.JJK });
        return;
      }
      // 先在标题页试一下速度按钮（玩家会这么干），再开局
      try { App.setSpeed(2); } catch (e) { errors.push('标题页点速度按钮就崩了: ' + e.message); }
      var games = [];
      for (var i = 0; i < 2; i++) {
        var r = await playOneGame(i);
        if (r) games.push(r);
        await sleep(200);
      }
      var bad = [];
      rounds.forEach(function (s) {
        if (s && s.bad && s.bad.length) bad.push(s.tag + ': ' + s.bad.join('; '));
      });
      var sample = rounds.filter(function (x, i) { return i % 8 === 0; }).slice(0, 6).map(function (x) {
        return x.tag + ' phase=' + x.phase + ' board=' + x.board + ' bench=' + x.bench + ' gold=' + x.gold;
      });
      var out = {
        sample: sample,
        games: games,
        errors: errors.slice(0, 12),
        errCount: errors.length,
        warns: warns.slice(0, 8),
        warnCount: warns.length,
        stateIssues: bad.slice(0, 8),
        stateIssueCount: bad.length,
        roundsPlayed: rounds.length
      };
      document.title = 'PLAYTEST ' + JSON.stringify(out);
      console.log('PLAYTEST', out);
    } catch (e) {
      document.title = 'PLAYTEST ' + JSON.stringify({ fatal: String(e && e.message || e), stack: String(e && e.stack || '').split('\n').slice(0,4), errors: errors.slice(0, 6) });
    }
  })();
})();
