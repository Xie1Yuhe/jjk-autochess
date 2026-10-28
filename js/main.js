/* =========================================================================
 *  main.js —— 启动与总装：模块初始化 / 事件接线 / 主循环 / 快捷键 / 自适应布局
 * ========================================================================= */
(function (global) {
  'use strict';

  var JJK = global.JJK = global.JJK || {};
  var U = JJK.util, D = JJK.data, h = U.h;

  var App = {
    game: null,
    inGame: false,
    toastSeq: 0
  };

  /* ============================================================== 启动 */
  function init() {
    if (!D || !D.units || !D.units.length) {
      document.body.innerHTML = '<div style="padding:60px;font:16px sans-serif;color:#eee">' +
        '数据加载失败：请确认 data/game-data.js 存在。</div>';
      return;
    }

    JJK.FX.init();
    if (JJK.Particles) JJK.Particles.init(document.getElementById('board-particles'));
    JJK.Tooltip.init();
    App.game = new JJK.Game();

    JJK.Board.init(App);
    JJK.Shop.init(App);
    JJK.Panels.init(App);
    JJK.BattleView.init();
    JJK.Codex.init(App);
    JJK.Screens.init(App);

    bindBus();
    bindButtons();
    bindKeys();
    bindResize();

    JJK.Screens.showTitle();
    document.getElementById('btn-sound').classList.toggle('is-on', JJK.Audio.isEnabled());

    fitLayout();
    U.addTicker(loop);
  }

  /* ============================================================== 总线 */
  function bindBus() {
    var g = App.game;

    // 阶段 → body 类：驱动「购买时商店上浮 / 战斗时商店收起」的布局
    function applyPhaseClass() {
      var ph = App.game ? App.game.phase : '';
      var body = document.body;
      body.classList.toggle('phase-buy', ph === 'planning' || ph === 'idle');
      body.classList.toggle('phase-battle', ph === 'battle' || ph === 'result');
      syncDrawer();
      if (App.refit) App.refit();
      // BGM：准备阶段与战斗阶段各一首
      if (typeof JJK.Audio.startBgm === 'function') {
        if (ph === 'battle' || ph === 'result') JJK.Audio.startBgm('battle');
        else if (ph === 'planning' || ph === 'idle') JJK.Audio.startBgm('prep');
      }
    }
    // ---------- 商店抽屉 ----------
    function syncDrawer() {
      var g2 = App.game;
      var goldEl = document.getElementById('dh-gold');
      if (goldEl && g2) goldEl.textContent = String(g2.gold);
      var btn = document.getElementById('btn-drawer');
      if (btn) {
        var closed = document.body.classList.contains('drawer-closed')
                  || document.body.classList.contains('phase-battle');
        var lab = btn.querySelector('.dh-label');
        if (lab) lab.textContent = closed ? '展开' : '收起';
      }
    }
    App.syncDrawer = syncDrawer;

    function bindDrawer() {
      var btn = document.getElementById('btn-drawer');
      if (btn) {
        btn.addEventListener('click', function () {
          document.body.classList.toggle('drawer-closed');
          syncDrawer();
          if (App.refit) App.refit();
          JJK.Audio.play('click');
        });
      }
      syncDrawer();
    }
    bindDrawer();

    App.applyPhaseClass = applyPhaseClass;
    // 过渡结束后重算棋盘尺寸（动画中间态量出来会偏小）
    App.refit = function () {
      setTimeout(function () { try { fitLayout(); JJK.Board.render(); } catch (e) {} }, 360);
      setTimeout(function () { try { fitLayout(); JJK.Board.render(); } catch (e) {} }, 640);
    };
    g.bus.on('phase', applyPhaseClass);
    g.bus.on('battle:start', function () { setTimeout(applyPhaseClass, 0); });
    g.bus.on('round:start', function () { setTimeout(applyPhaseClass, 0); });

    // ---------- 彩蛋：无限式神 ----------
    g.bus.on('easterEgg', function (payload) {
      var bd = document.body;
      bd.classList.add('egg-on');
      var flash = document.createElement('div'); flash.className = 'egg-flash';
      var ring  = document.createElement('div'); ring.className  = 'egg-ring';
      var title = document.createElement('div'); title.className = 'egg-title';
      title.textContent = '∞  无 限 式 神  ·  魔 虚 罗';
      bd.appendChild(flash); bd.appendChild(ring); bd.appendChild(title);
      if (JJK.FX && JJK.FX.banner) {
        JJK.FX.banner('无限式神 · 魔虚罗',
          payload && payload.why === 'trio' ? '三个伏黑惠，唤来了不可控之物'
                                            : '伏黑惠与宿傩，跨过了那条线',
          3200, '#c084fc');
      }
      if (JJK.Audio && JJK.Audio.play) { try { JJK.Audio.play('domain'); } catch (e) {} }
      setTimeout(function () {
        bd.classList.remove('egg-on');
        [flash, ring, title].forEach(function (el) { if (el.parentNode) el.parentNode.removeChild(el); });
      }, 2800);
    });

    g.bus.on('change', function (part) {
      if (!App.inGame) return;
      if (part === 'phase' || part === 'all') applyPhaseClass();
      switch (part) {
        case 'all':
          renderAll();
          break;
        case 'gold':
          JJK.Panels.renderHud();
          JJK.Shop.refreshAffordability();
          if (App.syncDrawer) App.syncDrawer();
          break;
        case 'hp':
          JJK.Panels.renderHud();
          break;
        case 'level':
        case 'exp':
          JJK.Panels.renderHud();
          JJK.Panels.renderTraits();
          break;
        case 'shop':
          JJK.Shop.invalidate();
          JJK.Shop.render();
          JJK.Panels.renderHud();
          break;
        case 'roster':
          JJK.Board.render();
          JJK.Panels.renderTraits();
          JJK.Panels.renderHud();
          break;
        case 'items':
          JJK.Panels.renderItems();
          break;
        case 'log':
          JJK.Panels.renderLog();
          break;
        case 'phase':
          JJK.Panels.renderHud();
          JJK.Board.render();
          break;
        case 'speed':
          updateSpeedLabel();
          break;
        default:
          renderAll();
      }
    });

    g.bus.on('battle:start', function (meta) {
      document.getElementById('screen-game').classList.add('is-battle');
      JJK.Screens.closeModal();
      JJK.Board.render();
      JJK.BattleView.start(App.game.battle);
      JJK.Panels.renderCombat(App.game.battle);
      JJK.Panels.renderHud();
      JJK.FX.banner('战 斗 开 始', '第 ' + g.round + ' 回合 · ' + (meta.kind === 'pve' ? 'PvE · ' + meta.enemyName : '对手 ' + meta.enemyName), 1300);
      JJK.Audio.play('start');
      JJK.FX.shake(5);
    });

    g.bus.on('battle:events', function (evs) {
      JJK.BattleView.onEvents(evs);
    });

    g.bus.on('battle:end', function (res) {
      JJK.Panels.renderHud();
    });

    g.bus.on('round:result', function (res) {
      document.getElementById('screen-game').classList.remove('is-battle');
      if (App.silent) {
        JJK.BattleView.stop();
        JJK.Board.render();
        JJK.Panels.renderCombat(null);
        return;
      }
      setTimeout(function () {
        JJK.BattleView.stop();
        JJK.Board.render();
        JJK.Panels.renderCombat(null);
        JJK.Panels.renderHud();
        JJK.Screens.showResult(res);
        App.save();
      }, 620);
    });

    g.bus.on('game:over', function (info) {
      setTimeout(function () {
        JJK.BattleView.stop();
        JJK.Board.render();
        JJK.Panels.renderCombat(null);
        JJK.Screens.showGameOver(info);
      }, 900);
    });

    g.bus.on('upgrade', function (e) {
      var el = JJK.Board.getUnitEl(e.uid);
      if (el) JJK.FX.starBurst(el, e.star);
      JJK.Audio.play('upgrade');
      App.toast('升星！' + D.unitById[e.unitId].name + ' → ' + e.star + ' 星', 'gold');
    });

    g.bus.on('hp:lost', function () {
      JJK.FX.hpFlash();
      JJK.FX.shake(8);
    });

    g.bus.on('crafted', function (e) {
      var el = JJK.Board.getUnitEl(e.uid);
      if (el) JJK.FX.starBurst(el, 2);
    });
  }

  /* ============================================================== 按钮 */
  function bindButtons() {
    var g = App.game;

    document.getElementById('btn-refresh').addEventListener('click', function () {
      var r = g.refreshShop();
      if (r.ok) { JJK.Audio.play('buy'); renderAll(); }
      else JJK.Audio.play('deny');
    });

    document.getElementById('btn-lock').addEventListener('click', function () {
      g.toggleLock();
      JJK.Audio.play('click');
      JJK.Shop.invalidate();
      JJK.Shop.render();
      JJK.Panels.renderHud();
    });

    document.getElementById('btn-exp').addEventListener('click', function () {
      var r = g.buyExp();
      if (r.ok) JJK.Audio.play('upgrade');
      else JJK.Audio.play('deny');
      JJK.Panels.renderHud();
    });

    document.getElementById('btn-sort').addEventListener('click', function () {
      g.sortBench();
      JJK.Audio.play('click');
      JJK.Board.render();
    });

    document.getElementById('btn-auto').addEventListener('click', function () {
      if (g.phase !== 'planning') { JJK.Audio.play('deny'); return; }
      var r = g.autoDeploy();
      JJK.Audio.play(r.added ? 'place' : 'deny');
      App.toast(r.added ? '自动上阵 ' + r.added + ' 名棋子' : '没有可上阵的棋子', r.added ? '' : 'warn');
      JJK.Board.render();
      JJK.Panels.renderTraits();
      JJK.Panels.renderHud();
    });

    document.getElementById('btn-battle').addEventListener('click', function () {
      if (g.phase === 'planning') startBattle();
      else if (g.phase === 'result') App.continueRound();
    });

    document.getElementById('btn-speed').addEventListener('click', function () {
      var next = g.battleSpeed === 1 ? 2 : (g.battleSpeed === 2 ? 4 : 1);
      App.setSpeed(next);
    });

    document.getElementById('btn-sound').addEventListener('click', function () {
      var on = !JJK.Audio.isEnabled();
      JJK.Audio.setEnabled(on);
      if (on) { JJK.Audio.unlock(); JJK.Audio.startAmbient(); JJK.Audio.play('click'); }
      document.getElementById('btn-sound').classList.toggle('is-on', on);
      App.toast(on ? '音效已开启' : '音效已关闭', '');
    });

    document.getElementById('btn-codex').addEventListener('click', function () {
      JJK.Codex.open('units');
    });

    /* 战局日志：默认收起，点「日」或按 T 展开（不占棋盘空间） */
    (function wireLogDrawer() {
      var dock = document.getElementById('log-dock');
      var btn = document.getElementById('btn-log');
      var head = document.getElementById('log-head');
      var close = document.getElementById('log-close');
      if (!dock) return;
      function toggle(force) {
        var open = force === undefined ? !dock.classList.contains('is-open') : force;
        dock.classList.toggle('is-open', open);
        if (btn) btn.classList.toggle('is-on', open);
        if (open) {
          var s = document.getElementById('log-stream');
          if (s) s.scrollTop = s.scrollHeight;
        }
      }
      JJK.__toggleLog = toggle;
      if (btn) btn.addEventListener('click', function () { toggle(); });
      if (head) head.addEventListener('click', function (e) {
        if (e.target === close) return;
        toggle();
      });
      if (close) close.addEventListener('click', function () { toggle(false); });
      document.addEventListener('keydown', function (e) {
        if (e.key === 't' || e.key === 'T') {
          if (document.activeElement && /input|textarea/i.test(document.activeElement.tagName)) return;
          if (!App.inGame) return;
          toggle();
        }
      });
    })();

    document.getElementById('btn-menu').addEventListener('click', function () {
      if (!App.inGame) return;
      JJK.Screens.openSettings();
    });

    // 点击空白处取消咒具选择
    document.addEventListener('click', function (e) {
      var g2 = App.game;
      if (!g2 || !g2.pendingItem) return;
      if (e.target.closest('.item-chip, .item-chip *, .unit, .bench-unit, .item-chip .ic-count')) return;
      if (e.target.closest('.tt-items')) return;
      g2.pendingItem = '';
      JJK.Panels.renderItems();
    });
  }

  function startBattle() {
    var g = App.game;
    if (g.phase !== 'planning') return;
    var r = g.beginBattle();
    if (!r.ok) {
      JJK.Audio.play('deny');
      if (r.reason === 'empty') App.toast('至少要放一名棋子上场', 'warn');
      return;
    }
  }

  /* ============================================================== 快捷键 */
  function bindKeys() {
    document.addEventListener('keydown', function (e) {
      var tag = (e.target.tagName || '').toUpperCase();
      if (tag === 'INPUT' || tag === 'TEXTAREA') {
        if (e.key === 'Escape') e.target.blur();
        return;
      }
      var g = App.game;
      if (!g) return;

      if (e.key === 'Escape') {
        if (JJK.Codex.isOpen() || JJK.Screens.isModalOpen()) {
          JJK.Codex.close();
          JJK.Screens.closeModal();
        } else if (g.pendingItem) {
          g.pendingItem = '';
          JJK.Panels.renderItems();
        } else if (g.selectedUid >= 0) {
          g.selectedUid = -1;
          JJK.Board.render();
          JJK.Panels.renderItems();
        }
        return;
      }

      if (!App.inGame) return;
      if (JJK.Codex.isOpen() || JJK.Screens.isModalOpen()) return;

      switch (e.key) {
        case ' ':
          e.preventDefault();
          if (g.phase === 'planning') startBattle();
          else if (g.phase === 'result') App.continueRound();
          break;
        case 'r': case 'R':
          document.getElementById('btn-refresh').click();
          break;
        case 'l': case 'L':
          document.getElementById('btn-lock').click();
          break;
        case 'f': case 'F':
          document.getElementById('btn-exp').click();
          break;
        case 'b': case 'B':
          // 展开 / 收起商店抽屉
          {
            var bt = document.getElementById('btn-drawer');
            if (bt) bt.click();
          }
          break;
        case 'c': case 'C':
          JJK.Codex.open('units');
          break;
        case 'Delete': case 'Backspace':
          if (g.selectedUid >= 0) {
            e.preventDefault();
            App.requestSell(g.selectedUid);
          }
          break;
        default:
          if (e.key >= '1' && e.key <= '9') {
            var idx = +e.key - 1;
            var inst = g.unitAtBench(idx);
            if (inst) {
              g.selectedUid = inst.uid;
              JJK.Board.render();
              JJK.Panels.renderItems();
              JJK.Audio.play('click');
            }
          }
      }
    });
  }

  /* ============================================================== 布局 */
  function bindResize() {
    var t = null;
    var kick = function () {
      if (t) clearTimeout(t);
      // 抽屉动画期间尺寸会连续变化，等稳定 140ms 再重算一次
      t = setTimeout(function () {
        fitLayout();
        JJK.Board.render();
      }, 140);
    };
    window.addEventListener('resize', kick);

    // 商店/日志高度变化会挤压舞台，必须跟着重新量一次
    if (global.ResizeObserver) {
      var stage = document.querySelector('.stage');
      if (stage) {
        var ro = new ResizeObserver(function () { kick(); });
        ro.observe(stage);
        var cl2 = document.querySelector('.col-left');
        if (cl2) ro.observe(cl2);
        var bd2 = document.getElementById('shop-dock');
        if (bd2) ro.observe(bd2);
      }
    }
  }

  /* ---- 棋盘尺寸平滑插值：避免抽屉动画期间 --cell 一格一格跳 ---- */
  var cellAnim = { cur: 0, target: 0, raf: 0 };
  function applyCell(v) {
    document.documentElement.style.setProperty('--cell', v.toFixed(2) + 'px');
    var slot = Math.max(46, (8 * v - 152) / 9);
    document.documentElement.style.setProperty('--slot', slot.toFixed(2) + 'px');
  }
  function tweenCell(target) {
    target = Math.max(44, Math.min(210, target));
    // 首帧直接落位，避免从 0 长出来
    if (cellAnim.cur <= 0 || Math.abs(target - cellAnim.cur) < 0.7) {
      cellAnim.cur = target;
      cellAnim.target = target;
      applyCell(target);
      try { JJK.FX.measure(); } catch (e) {}
      return;
    }
    cellAnim.target = target;
    if (cellAnim.raf) return;
    var step = function () {
      var diff = cellAnim.target - cellAnim.cur;
      if (Math.abs(diff) < 0.5) {
        cellAnim.cur = cellAnim.target;
        applyCell(cellAnim.cur);
        cellAnim.raf = 0;
        try { JJK.FX.measure(); } catch (e) {}
        return;
      }
      cellAnim.cur += diff * 0.30;     // 指数逼近，约 0.25s 收敛
      applyCell(cellAnim.cur);
      cellAnim.raf = setTimeout(step, 16);
    };
    cellAnim.raf = setTimeout(step, 16);
  }

  function fitLayout() {
    var stage = document.querySelector('.stage');
    var colLeft = document.querySelector('.col-left');
    if (!stage || !colLeft) return;
    // 三带布局：用 stage 高度减去 intel / 备战席 / 开始按钮的**实测**高度
    var H = stage.clientHeight;
    var overhead = 0;
    ['#intel', '.bench-row', '#start-dock'].forEach(function (sel) {
      var el = document.querySelector(sel);
      if (el && el.offsetHeight) overhead += el.offsetHeight + 8;
    });
    var W = colLeft.clientWidth;
    // 竖直预算：4 行棋盘 + 备战席(≈0.78 cell) + 两段间距 + 棋盘外框
    // 之前留得太紧，备战席实际会压到棋盘上，所以常数从 38 提到 66
    var byH = (H - overhead) / 4.35;   // 4 行棋盘 + 上下留白
    var byW = W / 8;
    var cell = Math.min(byH, byW, 210);
    cell = Math.max(44, cell);
    var slot = Math.max(46, (8 * cell - 152) / 9);
    tweenCell(cell);
    if (global.__JJK_DEBUG) {
      document.title = 'MEASURE ' + JSON.stringify({
        H: H, W: W, cell: cell, slot: slot,
        stage: stage.getBoundingClientRect().height,
        hud: document.querySelector('.hud').getBoundingClientRect().height,
        shop: document.querySelector('.shop-dock').getBoundingClientRect().height,
        log: document.querySelector('.log-dock').getBoundingClientRect().height,
        board: document.getElementById('board').getBoundingClientRect().width,
        shake: document.getElementById('shake-wrap').getBoundingClientRect().height,
        screen: document.getElementById('screen-game').getBoundingClientRect().height,
        app: document.getElementById('app').getBoundingClientRect().height,
        children: Array.prototype.map.call(document.getElementById('shake-wrap').children,
          function (c) { return c.className.split(' ')[0] + ':' + Math.round(c.getBoundingClientRect().height) + '@' + Math.round(c.getBoundingClientRect().top); })
      });
    }
  }

  App.markReflow = function () {
    requestAnimationFrame(function () {
      fitLayout();
      JJK.Board.render();
      JJK.Shop.refreshAffordability();
    });
  };

  /* ============================================================== 渲染 */
  function renderAll() {
    if (App.applyPhaseClass) App.applyPhaseClass();
    JJK.Panels.renderHud();
    JJK.Panels.renderTraits();
    JJK.Panels.renderItems();
    JJK.Panels.renderIntel();
    JJK.Panels.renderLog(true);
    JJK.Board.render();
    JJK.Shop.invalidate();
    JJK.Shop.render();
    fitLayout();
  }

  App.renderDetail = function () { JJK.Panels.renderItems(); };

  /* ============================================================== 流程 */
  App.startNewGame = function (difficulty) {
    // 修复：标题页首次开局时 App.game 还是 null，直接 .clearSave() 会抛错
    if (!App.game) App.game = new JJK.Game();
    App.game.clearSave();
    var deck = (JJK.Decks && JJK.Decks.chosen) ? JJK.Decks.chosen() : null;
    App.game.newGame(difficulty, false, deck);
    App.inGame = true;
    JJK.Screens.showGame();
    renderAll();
    JJK.Panels.renderLog(true);
    App.toast('难度：' + ['简单', '普通', '困难'][difficulty] + ' · 前 3 回合是 PvE', 'gold');
    if (JJK.Audio.isEnabled()) { JJK.Audio.unlock(); JJK.Audio.startAmbient(); }
    App.save();
  };

  App.continueGame = function () {
    if (!App.game.hasSave()) { App.toast('没有找到存档', 'warn'); return; }
    if (!App.game.load()) { App.toast('存档读取失败', 'warn'); return; }
    App.inGame = true;
    JJK.Screens.showGame();
    renderAll();
    JJK.Panels.renderLog(true);
    App.toast('已继续：第 ' + App.game.round + ' 回合', 'gold');
  };

  App.goTitle = function () {
    App.game.save();
    App.inGame = false;
    JJK.BattleView.stop();
    JJK.Screens.closeModal();
    JJK.Codex.close();
    JJK.Screens.showTitle();
  };

  App.continueRound = function () {
    var g = App.game;
    if (g.phase !== 'result') return;
    JJK.Screens.closeModal();
    g.continueAfterResult();
    renderAll();
    JJK.Panels.renderLog(true);
    App.save();
  };

  App.setSpeed = function (sp) {
    // 修复：标题页 / 尚未开局时 App.game 为 null，点速度按钮会直接抛错
    if (!App.game) return;
    App.game.setSpeed(sp);
    updateSpeedLabel();
  };

  function updateSpeedLabel() {
    var g = App.game;
    if (!g) return;
    document.getElementById('btn-speed').textContent = g.battleSpeed + 'x';
    document.getElementById('btn-speed').classList.toggle('is-on', g.battleSpeed > 1);
  }

  App.requestSell = function (uid) {
    var g = App.game;
    if (g.phase !== 'planning') { JJK.Audio.play('deny'); return; }
    var info = g.sellInfo(uid);
    if (!info) return;
    var doSell = function () {
      var r = g.sellUnit(uid);
      if (r.ok) {
        JJK.Audio.play('sell');
        App.toast('卖出 ' + info.unit.name + '，回收 ' + r.refund + ' 金', '');
        JJK.Board.render();
        JJK.Panels.renderTraits();
        JJK.Panels.renderItems();
        JJK.Panels.renderHud();
      }
    };
    if (info.needsConfirm) {
      JJK.Screens.confirm({
        title: '确认出售',
        text: '出售「<b>' + info.unit.name + '</b>」' + (info.star > 1 ? '（' + info.star + ' 星）' : '') +
          '？<br>将返还 <b>' + info.refund + '</b> 金' +
          (info.unit ? '，棋子上的咒具会退回背包。' : '。'),
        danger: true,
        okText: '出售',
        onOk: doSell
      });
    } else {
      doSell();
    }
  };

  App.toast = function (msg, kind) {
    var root = document.getElementById('toast-root');
    if (!root) return;
    var el = h('div', { class: 'toast ' + (kind || ''), text: msg });
    root.appendChild(el);
    setTimeout(function () {
      if (el.parentNode) el.parentNode.removeChild(el);
    }, 2400);
    // 最多同时 4 条
    while (root.children.length > 4) root.removeChild(root.firstChild);
  };

  App.save = function () {
    if (!App.inGame || !App.game) return;
    if (App.game.phase === 'gameover') return;
    App.game.save();
  };

  /* ============================================================== 主循环 */
  var combatTick = 0;
  var layoutCheck = 0;
  var hitstopLeft = 0;

  // 顿帧：冻结模拟一小段时间，命中越重停得越久（调研：轻 33-50ms / 重 83-133ms / 暴击 133-200ms）
  App.hitstop = function (ms) {
    if (U.reduceMotion) return;
    hitstopLeft = Math.max(hitstopLeft, Math.min(0.18, ms / 1000));
    JJK.FX.hitstopFlash(0.8);
  };
  var lastFit = { h: 0, w: 0 };
  function loop(dt) {
    if (!App.inGame) return;
    var g = App.game;

    // 兜底自愈：浏览器改了可视区但没派发 resize 时也能重新排版
    layoutCheck += dt;
    if (layoutCheck > 0.4) {
      layoutCheck = 0;
      var stage = document.querySelector('.stage');
      if (stage) {
        var h = stage.clientHeight, w = stage.clientWidth;
        if (Math.abs(h - lastFit.h) > 4 || Math.abs(w - lastFit.w) > 4) {
          lastFit.h = h; lastFit.w = w;
          fitLayout();
        }
      }
    }

    if (g.phase === 'battle' && g.battle) {
      if (hitstopLeft > 0) {
        // 顿帧期间只消耗时间，不推进模拟 —— 视觉上就是"卡住一下"
        hitstopLeft -= dt;
        return;
      }
      g.tickBattle(dt);
      JJK.BattleView.sync(g.battle);
      combatTick += dt;
      if (combatTick > 0.1) { combatTick = 0; JJK.Panels.renderCombat(g.battle); }
    }
  }

  // 自动保存
  setInterval(function () {
    if (App.inGame && App.game && App.game.phase === 'planning') App.save();
  }, 20000);

  /* ============================================================== 开发开关 */
  // ?dev=deploy 直接进入对局并自动铺场；?dev=battle 直接开一场战斗
  // 方便截图验收，也不影响正常入口（不带参数时行为完全不变）。
  function devBoot() {
    var q = new URLSearchParams(global.location.search);
    var mode = q.get('dev');
    if (q.get('measure')) global.__JJK_DEBUG = true;
    if (!mode) return;
    App.startNewGame(+(q.get('d') || 1));
    var g = App.game;
    g.gold = 70;
    for (var round = 0; round < 3; round++) {
      for (var i = 0; i < 5; i++) {
        if (g.shop[i]) g.buyFromShop(i);
      }
      g.refreshShop();
    }
    g.gold = 46;
    g.autoDeploy();
    g.itemsBag.push('scroll', 'fang', 'crystal', 'charm', 'fragment', 'ward');
    g.addLog('（开发模式：已自动铺场并补给咒具）', 'system');
    renderAll();
    JJK.Panels.renderLog(true);
    if (mode === 'battle') {
      setTimeout(function () {
        startBattle();
        // &t=秒 可以把战斗快进到指定时刻，方便截图验收
        var ff = parseFloat(q.get('t') || '0');
        if (ff > 0 && g.battle) {
          var steps = Math.floor(ff * 30);
          for (var s = 0; s < steps; s++) g.tickBattle(1 / 30);
          JJK.BattleView.sync(g.battle);
          JJK.Panels.renderCombat(g.battle);
          var fx = document.getElementById('board-fx');
          if (fx) U.clear(fx);
          for (var k = 0; k < 3; k++) {
            g.tickBattle(1 / 30);
          }
          JJK.BattleView.sync(g.battle);
        }
      }, 260);
    }
    if (mode === 'late' || mode === 'late-battle') {
      // 快速推进到中期，用来看"满人口 + 满羁绊"的真实观感
      App.silent = true;
      var target = Math.max(2, Math.min(20, +(q.get('r') || 8)));
      var guardN = 0;
      while (g.round < target && g.phase !== 'gameover' && guardN++ < 40) {
        for (var bi = 0; bi < 5; bi++) if (g.shop[bi]) g.buyFromShop(bi);
        if (g.gold > 18 && g.level < 9) g.buyExp();
        g.autoDeploy();
        if (g.boardCount() === 0) { g.startRound(); continue; }
        g.beginBattle();
        var st = 0;
        while (g.phase === 'battle' && st++ < 4000) g.tickBattle(1 / 30);
        if (g.phase === 'result') g.continueAfterResult();
      }
      App.silent = false;
      App.game.selectedUid = -1;
      renderAll();
      JJK.Panels.renderLog(true);
      if (mode === 'late-battle') {
        setTimeout(function () {
          startBattle();
          var ff2 = parseFloat(q.get('t') || '0');
          if (ff2 > 0 && g.battle) {
            for (var ss = 0; ss < Math.floor(ff2 * 30); ss++) g.tickBattle(1 / 30);
            JJK.BattleView.sync(g.battle);
            var fx2 = document.getElementById('board-fx');
            if (fx2) U.clear(fx2);
            for (var kk = 0; kk < 4; kk++) g.tickBattle(1 / 30);
            JJK.BattleView.sync(g.battle);
            JJK.Panels.renderCombat(g.battle);
          }
        }, 200);
      }
    }
    if (mode === 'link') {
      setTimeout(function () {
        g.level = 9;
        g.gold = 60;
        var pairs = [['607979', '721094'], ['661932', '606026'], ['607988', '644233']];
        pairs.forEach(function (p) {
          p.forEach(function (id) {
            if (!g.roster.filter(function (r) { return r.id === id; })[0]) {
              g.roster.push({ uid: g.nextUid++, id: id, star: 2, pos: { x: -1, y: -1 }, bench: g.freeBench(), items: [] });
            }
          });
        });
        // 只把第一组放上场，另外两组放备战席，方便看"激活 vs 未激活"
        ['607979', '721094'].forEach(function (id, i) {
          var inst = g.roster.filter(function (r) { return r.id === id; })[0];
          if (inst) g.placeUnit(inst.uid, { type: 'cell', x: 1 + i, y: 1 });
        });
        renderAll();
        setTimeout(function () {
          var chip = document.querySelector('.link-chip');
          if (chip) JJK.Tooltip.showLink(JJK.data.raw.links[0], chip);
        }, 300);
      }, 400);
    }
    if (mode === 'banner') {
      setTimeout(function () {
        JJK.Panels.showTraitBanner({ id: '东京校', color: '#4bc6e8', level: 3, count: 4, info: { name: '东京校' } });
        JJK.Panels.floatDelta(document.getElementById('chip-gold'), '12', 1);
        setTimeout(function () { JJK.Panels.showLevelUp(6); }, 700);
      }, 600);
    }
    if (mode === 'hover') {
      setTimeout(function () {
        var cards = document.querySelectorAll('.shop-card:not(.is-empty)');
        if (cards[1]) { cards[1].classList.add('force-hover'); }
        if (cards[0]) {
          cards[0].classList.add('is-active');
          JJK.Tooltip.showUnitNow(g.shop[0], cards[0], { star: 1, items: [], showEquipHint: true });
        }
        var traitRow = document.querySelector('.trait-row');
        if (traitRow) JJK.Panels.showTraitBanner({ id: '东京校', color: '#4bc6e8', level: 3, count: 4, info: { name: '东京校' } });
      }, 500);
    }
    if (mode === 'codex') setTimeout(function () { JJK.Codex.open('units'); }, 300);
    if (mode === 'codex-traits') setTimeout(function () { JJK.Codex.open('traits'); }, 300);
    if (mode === 'codex-items') setTimeout(function () { JJK.Codex.open('items'); }, 300);
    if (mode === 'codex-rules') setTimeout(function () { JJK.Codex.open('rules'); }, 300);
    if (mode === 'settings') setTimeout(function () { JJK.Screens.openSettings(); }, 300);
    if (mode === 'tooltip') {
      setTimeout(function () {
        var el = document.querySelector('.unit');
        if (el && g.boardUnits().length) {
          JJK.Tooltip.showUnitNow(g.boardUnits()[0].id, el, { star: 2, items: ['yuyun', 'ao'], showEquipHint: true });
        }
      }, 400);
    }
    if (mode === 'result') {
      setTimeout(function () {
        JJK.Screens.showResult({
          won: true, dmg: 14, myLeft: ['结木海斗', '熊猫', '三轮霞'], foeLeft: [],
          survivors: 3, kind: 'ai', duration: 21.4, enemyName: '东京校 · 体术阵',
          income: { base: 5, interest: 4, streak: 2, pve: 0, total: 11 }, rewards: []
        });
      }, 400);
    }
    if (mode === 'gameover') {
      setTimeout(function () {
        JJK.Screens.showGameOver({
          win: false, rank: 2, round: 14, level: 7, gold: 12, hp: 0, difficulty: 1,
          comp: ['结木海斗', '熊猫', '三轮霞', '禅院真希', '伏黑惠'],
          stats: { wins: 6, losses: 8, kills: 41, unitsBought: 29, rerolls: 11 }
        });
      }, 400);
    }
  }

  JJK.App = App;

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () { init(); devBoot(); });
  } else {
    init();
    devBoot();
  }

})(window);

  // 首屏就绪后收起 loading
  (function hideBoot() {
    var el = document.getElementById('boot');
    if (!el) return;
    setTimeout(function () {
      el.classList.add('hide');
      setTimeout(function () { if (el.parentNode) el.parentNode.removeChild(el); }, 450);
    }, 260);
  })();
