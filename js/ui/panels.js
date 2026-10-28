/* =========================================================================
 *  panels.js —— HUD 数值 / 羁绊面板 / 咒具背包 / 选中棋子的装备槽 / 日志 / 情报
 * ========================================================================= */
(function (global) {
  'use strict';

  var JJK = global.JJK = global.JJK || {};
  var U = JJK.util, D = JJK.data, W = JJK.Widgets, h = U.h;

  var app = null;
  var el = {};
  var prev = { gold: 6, hp: 100, level: 2, round: 0, streak: 0 };
  var traitPrevLevel = {};
  var logCount = 0;

  function game() { return app.game; }

  function init(appRef) {
    app = appRef;
    el.chips = document.getElementById('hud-chips');
    el.round = document.getElementById('v-round');
    el.roundKind = document.getElementById('v-round-kind');
    el.gold = document.getElementById('v-gold');
    el.interest = document.getElementById('v-interest');
    el.hp = document.getElementById('v-hp');
    el.level = document.getElementById('v-level');
    el.exp = document.getElementById('v-exp');
    el.expbar = document.getElementById('v-expbar');
    el.streak = document.getElementById('v-streak');
    el.chipGold = document.getElementById('chip-gold');
    el.chipHp = document.getElementById('chip-hp');
    el.chipLevel = document.getElementById('chip-level');
    el.chipRound = document.getElementById('chip-round');
    el.chipStreak = document.getElementById('chip-streak');

    el.traitsBody = document.getElementById('traits-body');
    el.traitSub = document.getElementById('trait-sub');
    el.itemsBody = document.getElementById('items-body');
    el.itemsSub = document.getElementById('items-sub');
    el.logStream = document.getElementById('log-stream');
    el.intelTag = document.getElementById('intel-tag');
    el.intelName = document.getElementById('intel-name');
    el.intelList = document.getElementById('intel-list');
    el.intelScale = document.getElementById('intel-scale');
    el.battleSub = document.getElementById('battle-sub');
    el.cdMine = document.getElementById('cd-mine');
    el.cdFoe = document.getElementById('cd-foe');
    el.cdMineN = document.getElementById('cd-mine-n');
    el.cdFoeN = document.getElementById('cd-foe-n');
    el.cdTime = document.getElementById('cd-time');
    el.lockLabel = document.getElementById('lock-label');
    el.traitsTips = document.getElementById('traits-tips');
  }

  /* ============================================================== HUD */
  function bump(chip, dir) {
    if (!chip) return;
    chip.classList.remove('is-bump', 'is-up', 'is-down');
    void chip.offsetWidth;
    chip.classList.add('is-bump');
    if (dir > 0) chip.classList.add('is-up');
    else if (dir < 0) chip.classList.add('is-down');
    setTimeout(function () {
      chip.classList.remove('is-bump', 'is-up', 'is-down');
    }, 620);
  }

  function renderHud() {
    var g = game();
    if (!g) return;

    if (prev.round !== g.round) {
      el.round.textContent = String(g.round);
      el.roundKind.textContent = g.round <= 3 ? 'PvE' : '对手';
      bump(el.chipRound, 0);
      prev.round = g.round;
    }

    if (prev.gold !== g.gold) {
      var dGold = g.gold - prev.gold;
      el.gold.textContent = String(g.gold);
      bump(el.chipGold, dGold);
      if (dGold !== 0) floatDelta(el.chipGold, String(Math.abs(dGold)), dGold);
      prev.gold = g.gold;
    }
    el.roundKind.textContent = g.round <= 3 ? 'PvE' : '对手';
    var interest = Math.min(5, Math.floor(g.gold / 10));
    el.interest.textContent = '利息 +' + interest + (g.shopLocked ? ' · 锁' : '');

    if (prev.hp !== g.hp) {
      el.hp.textContent = String(g.hp);
      bump(el.chipHp, g.hp - prev.hp);
      prev.hp = g.hp;
    }

    if (prev.level !== g.level) {
      el.level.textContent = String(g.level);
      bump(el.chipLevel, g.level - prev.level);
      if (g.level > prev.level && prev.level > 0) showLevelUp(g.level);
      prev.level = g.level;
    }
    var need = g.nextExp();
    el.exp.textContent = g.level >= 9 ? 'MAX' : (g.exp + '/' + need);
    el.expbar.style.width = g.level >= 9 ? '100%' : Math.min(100, (g.exp / Math.max(1, need)) * 100) + '%';

    var streak = g.winStreak || -g.loseStreak;
    var txt = '—';
    if (g.winStreak >= 1) txt = g.winStreak + ' 连胜';
    else if (g.loseStreak >= 1) txt = g.loseStreak + ' 连败';
    el.streak.textContent = txt;
    el.streak.style.color = g.winStreak >= 1 ? '#7dffc8' : (g.loseStreak >= 1 ? '#ff8fa2' : 'var(--text-dim)');
    prev.streak = streak;

    el.lockLabel.textContent = g.shopLocked ? '解除锁定' : '锁定商店';
    document.getElementById('btn-lock').classList.toggle('btn-violet', g.shopLocked);

    var isPve = g.battleKind === 'pve';
    var startBtn = document.getElementById('btn-battle');
    startBtn.disabled = (g.phase !== 'planning' && g.phase !== 'result');
    var mainLabel = '开 始 战 斗';
    var subLabel = '第 ' + g.round + ' 回合 · ' + (isPve ? 'PvE 咒灵' : '对手 ' + g.ai.plan.name);
    if (g.phase === 'battle') {
      mainLabel = '战 斗 中';
      subLabel = '第 ' + g.round + ' 回合 · 交战中';
    } else if (g.phase === 'result') {
      mainLabel = '继 续 前 进';
      subLabel = '第 ' + (g.round + 1) + ' 回合';
    }
    startBtn.innerHTML = mainLabel + '<span class="bs-sub">' + subLabel + '</span>';
    el.battleSub = startBtn.querySelector('.bs-sub');
  }

  /* ============================================================== 羁绊 */
  function renderTraits() {
    var g = game();
    var list = g.traitSummary();
    var boardCount = g.boardCount();
    el.traitSub.textContent = '上场 ' + boardCount + ' / ' + g.level;


    // 清掉空状态占位（reconcile 只回收带 key 的节点）
    var emptyNode = el.traitsBody.querySelector('.traits-empty');
    if (list.length && emptyNode) emptyNode.parentNode.removeChild(emptyNode);

    if (!list.length) {
      U.clear(el.traitsBody);
      el.traitsBody.appendChild(h('div', {
        class: 'traits-empty',
        text: '把棋子拖上场，羁绊会自动统计'
      }));
      renderLinkStrip();
      renderTips();
      return;
    }

    W.reconcile(el.traitsBody, list, function (row) { return row.id; },
      function (row) {
        var node = h('div', { class: 'trait-row', data: { trait: row.id } });
        node.style.setProperty('--tc', row.color);
        var glyph = h('span', { class: 'tr-glyph' });
        glyph.style.setProperty('--tc', row.color);
        if (JJK.Icons) glyph.appendChild(JJK.Icons.trait(row.id));
        else glyph.textContent = row.info.glyph || row.info.name[0];
        node.appendChild(glyph);
        node.appendChild(h('span', { class: 'tr-name', text: row.info.name }));
        var bar = h('span', { class: 'tr-bar' });
        bar.appendChild(h('i'));
        node.appendChild(bar);
        node.appendChild(h('span', { class: 'tr-count' }));

        node.addEventListener('mouseenter', function () {
          var g2 = game();
          var st = g2.traitSummary().filter(function (r) { return r.id === row.id; })[0];
          JJK.Tooltip.showTrait(row.id, st ? st.count : row.count, node);
        });
        node.addEventListener('mouseleave', function () { JJK.Tooltip.hide(); });
        node.addEventListener('click', function () {
          var n = JJK.Board.focusTrait(row.id, 2800);
          JJK.Audio.play('click');
          app.toast('高亮场上 ' + n + ' 名「' + row.info.name + '」棋子', '');
        });
        return node;
      },
      function (node, row) {
        node.style.setProperty('--tc', row.color);
        var isNear = row.level > 0 && row.next && (row.next.count - row.count === 1);
        var wasLevel = traitPrevLevel[row.id] === undefined ? row.level : traitPrevLevel[row.id];
        node.classList.toggle('is-on', row.level > 0);
        node.classList.toggle('is-near', !!isNear);
        if (row.level > wasLevel) {
          node.classList.remove('is-flash');
          void node.offsetWidth;
          node.classList.add('is-flash');
          JJK.Audio.play('trait');
          // 关键：动画结束后必须摘掉 class。
          // 否则浏览器在“动画被暂停/prefers-reduced-motion”时会把元素永久停在 0% 帧。
          (function (n) {
            setTimeout(function () { n.classList.remove('is-flash'); }, 1050);
          })(node);
          if (row.level > 0) showTraitBanner(row);
        }
        traitPrevLevel[row.id] = row.level;
        var bar = node.querySelector('.tr-bar > i');
        if (bar) bar.style.width = Math.round(row.progress * 100) + '%';
        var cnt = node.querySelector('.tr-count');
        cnt.innerHTML = '';
        cnt.appendChild(h('b', { text: String(row.count) }));
        cnt.appendChild(document.createTextNode('/' + row.topNeed));
        var nm = node.querySelector('.tr-name');
        if (nm) nm.textContent = row.info.name + (row.level > 0 ? ' ' + row.level : '');
      });
    renderLinkStrip();
    renderTips();
  }

  /* ---------------------------------------------------- 异格联动条 --- */
  // 必须在 reconcile 之后执行：reconcile 用 insertBefore 插行，会把先插入的条推到末尾
  function renderLinkStrip() {
    var body = el.traitsBody;
    if (!body) return;
    var old = body.querySelector('.link-strip');
    if (old) old.parentNode.removeChild(old);
    var links = game().activeLinks();
    if (!links.length) return;
    var strip = h('div', { class: 'link-strip' });
    links.forEach(function (L) {
      var chip = h('div', { class: 'link-chip', style: '--lc:' + L.color });
      chip.appendChild(h('span', { class: 'lk-name', text: L.name }));
      chip.appendChild(h('span', { class: 'lk-tag', text: L.short }));
      chip.title = L.desc;
      chip.addEventListener('mouseenter', function () { JJK.Tooltip.showLink(L, chip); });
      chip.addEventListener('mouseleave', function () { JJK.Tooltip.hide(); });
      strip.appendChild(chip);
    });
    body.insertBefore(strip, body.firstChild);
  }

  /* ============================================================== 提示 */
  // 把"下一步该干嘛"直接说给玩家听 —— 这是网页版相比 EXE 版最重要的体验补强
  function collectTips() {
    var g = game();
    var tips = [];
    if (g.phase !== 'planning') return tips;

    var board = g.boardCount();
    if (board < g.level) {
      tips.push({ k: 'act', t: '还有 ' + (g.level - board) + ' 个人口空着，把备战席棋子拖上场' });
    } else if (g.benchUnits().length && board >= g.level) {
      tips.push({ k: 'act', t: '人口已满：把棋子拖到场上棋子身上可直接替换' });
    }

    // 差一名就激活的羁绊
    g.traitSummary().forEach(function (row) {
      if (row.next && row.next.count - row.count === 1) {
        tips.push({ k: 'trait', t: '再上 1 名「' + row.info.name + '」即可激活第 ' + (row.level + 1) + ' 档' });
      }
    });

    // 再买一张就升星
    var byId = {};
    g.roster.forEach(function (r) { (byId[r.id] = byId[r.id] || []).push(r); });
    Object.keys(byId).forEach(function (id) {
      var list = byId[id];
      if (list.length === 2 && list.every(function (r) { return r.star === 1; })) {
        tips.push({ k: 'star', t: '再买 1 张「' + D.unitById[id].name + '」就能升 2 星' });
      }
    });

    if (g.itemsBag.length && !g.pendingItem) {
      tips.push({ k: 'item', t: '有 ' + g.itemsBag.length + ' 件咒具没装，点咒具再点棋子即可装备' });
    }
    if (g.gold >= 50) {
      tips.push({ k: 'gold', t: '金币已吃满 5 利息，可以升级人口或搜卡' });
    } else if (g.gold < 10 && g.round > 3) {
      tips.push({ k: 'gold', t: '金币偏少，先攒到 20 以上吃利息更稳' });
    }
    if (g.level < 9 && g.gold >= 4 && g.round > 4 && g.boardCount() >= g.level) {
      tips.push({ k: 'level', t: '人口满了，花 4 金买经验才能再上人' });
    }
    return tips.slice(0, 2);
  }

  function renderTips() {
    if (!el.traitsTips) return;
    U.clear(el.traitsTips);
    var tips = collectTips();
    if (!tips.length) return;
    var head = h('div', { class: 'tips-head', text: '提 示' });
    el.traitsTips.appendChild(head);
    tips.forEach(function (tip) {
      el.traitsTips.appendChild(h('div', {
        class: 'tips-line tips-' + tip.k,
        text: tip.t
      }));
    });
  }

  /* ============================================================== 咒具 */
  function renderItems() {
    var g = game();
    U.clear(el.itemsBody);

    // 选中棋子的装备槽
    var sel = g.selectedUid >= 0 ? g.unitById(g.selectedUid) : null;
    if (sel) {
      var su = D.unitById[sel.id];
      var block = h('div', { class: 'equip-block' });
      var head = h('div', { class: 'eq-title' }, [
        h('img', { src: su.icon, alt: su.name }),
        h('span', { text: su.name + ' 的咒具' })
      ]);
      block.appendChild(head);
      var slotsRow = h('div', { class: 'equip-slots' });
      for (var i = 0; i < 3; i++) {
        if (sel.items[i]) {
          var chip = W.itemChip(sel.items[i]);
          chip.addEventListener('click', function (e) {
            var itemId = e.currentTarget.dataset.item;
            var r = game().unequip(sel.uid, itemId);
            if (r.ok) { JJK.Audio.play('equip'); app.toast('已卸下咒具', ''); }
          });
          chip.addEventListener('mouseenter', function (e) {
            JJK.Tooltip.showItem(e.currentTarget.dataset.item, e.currentTarget);
          });
          chip.addEventListener('mouseleave', function () { JJK.Tooltip.hide(); });
          slotsRow.appendChild(chip);
        } else {
          slotsRow.appendChild(h('div', { class: 'eq-empty', text: '+' }));
        }
      }
      block.appendChild(slotsRow);
      el.itemsBody.appendChild(block);
      el.itemsSub.textContent = sel.items.length + ' / 3 已装备';
    } else {
      el.itemsSub.textContent = g.itemsBag.length ? '点选后点棋子装备' : '击败 PvE 可获得组件';
    }

    // 背包
    if (!g.itemsBag.length && !sel) {
      el.itemsBody.appendChild(h('div', {
        class: 'items-empty',
        html: '暂无咒具组件<br>PvE 前 3 回合击败咒灵即可掉落'
      }));
      return;
    }
    if (!g.itemsBag.length) return;

    var bagWrap = h('div', { class: 'bag-block' });
    if (sel) bagWrap.appendChild(h('div', { class: 'bag-title', text: '背包 · 点选后再点棋子装备' }));

    // 相同咒具合并计数
    var counts = {};
    g.itemsBag.forEach(function (id) { counts[id] = (counts[id] || 0) + 1; });
    Object.keys(counts).forEach(function (id) {
      var chip = W.itemChip(id, { count: counts[id] > 1 ? counts[id] : 0, armed: g.pendingItem === id });
      chip.addEventListener('click', function (e) {
        e.stopPropagation();
        if (game().pendingItem === id) {
          game().pendingItem = '';
          JJK.Audio.play('click');
          app.toast('已取消选择', '');
        } else {
          game().selectItem(id);
          JJK.Audio.play('click');
          app.toast('已选择「' + D.itemById[id].name + '」，点击棋子装备', 'gold');
        }
        renderItems();
      });
      chip.addEventListener('mouseenter', function (e) {
        JJK.Tooltip.showItem(id, e.currentTarget);
      });
      chip.addEventListener('mouseleave', function () { JJK.Tooltip.hide(); });
      bagWrap.appendChild(chip);
    });
    el.itemsBody.appendChild(bagWrap);
    renderTips();
  }

  /* ============================================================== 日志 */
  function logLine(entry) {
    return h('div', { class: 'log-line ' + entry.kind }, [
      h('span', { class: 'll-round', text: entry.round ? 'R' + entry.round : '' }),
      h('span', { class: 'll-text', text: entry.text })
    ]);
  }

  function renderLog(force) {
    var g = game();
    var log = g.log;
    if (!force && log.length === logCount) return;
    var isAppend = log.length > logCount && logCount > 0;
    if (!isAppend || force) {
      U.clear(el.logStream);
      var start = Math.max(0, log.length - 40);
      for (var i = start; i < log.length; i++) el.logStream.appendChild(logLine(log[i]));
    } else {
      for (var j = logCount; j < log.length; j++) el.logStream.appendChild(logLine(log[j]));
      while (el.logStream.children.length > 40) el.logStream.removeChild(el.logStream.firstChild);
    }
    logCount = log.length;
    el.logStream.scrollTop = 0;
  }

  /* ============================================================== 情报 */
  function renderIntel() {
    var g = game();
    var p = g.opponentPreview();
    if (!p) {
      el.intelName.textContent = '——';
      U.clear(el.intelList);
      return;
    }
    el.intelTag.textContent = p.kind === 'pve' ? 'PvE 波次' : '对手';
    el.intelTag.classList.toggle('pve', p.kind === 'pve');
    var hpTxt = p.kind === 'ai' ? ('· 生命 ' + g.ai.hp + '/100') : '';
    el.intelName.textContent = p.name + ' ' + hpTxt;
    U.clear(el.intelList);
    p.units.forEach(function (u) {
      var chip = h('span', { class: 'intel-unit' });
      if (u.icon) chip.appendChild(h('img', { src: u.icon, alt: u.name }));
      chip.appendChild(h('span', { text: u.name + (u.star > 1 ? ' ★' + u.star : '') }));
      el.intelList.appendChild(chip);
    });
    if (p.kind === 'ai' && p.scale) {
      el.intelScale.textContent = '强度 ×' + p.scale.toFixed(2);
    } else {
      el.intelScale.textContent = '';
    }
  }

  /* ============================================================== 战斗坞 */
  function renderCombat(sim) {
    if (!sim) {
      el.cdMineN.textContent = '0';
      el.cdFoeN.textContent = '0';
      el.cdTime.textContent = '0.0s';
      U.clear(el.cdMine); U.clear(el.cdFoe);
      return;
    }
    var mine = sim.aliveUnits(0).length;
    var foe = sim.aliveUnits(1).length;
    el.cdMineN.textContent = String(mine);
    el.cdFoeN.textContent = String(foe);
    el.cdTime.textContent = sim.time.toFixed(1) + 's' + (sim.overtime ? ' 加时' : '');
    el.cdTime.style.color = sim.overtime ? '#ff8fa2' : '';
    renderPips(el.cdMine, mine, 9, false);
    renderPips(el.cdFoe, foe, 9, true);
  }

  function renderPips(container, n, total, foe) {
    if (container.children.length !== total) {
      U.clear(container);
      for (var i = 0; i < total; i++) container.appendChild(h('span', { class: 'cd-pip' + (foe ? ' foe' : '') }));
    }
    for (var j = 0; j < total; j++) {
      container.children[j].classList.toggle('on', j < n);
    }
  }

  /* ====================================================== 变强感知 ==== */
  // 羁绊激活横幅：告诉玩家"你刚刚变强了"
  function showTraitBanner(row) {
    var old = document.querySelector('.trait-activate');
    if (old && old.parentNode) old.parentNode.removeChild(old);
    var el = h('div', { class: 'trait-activate', style: '--tc:' + row.color });
    var icon = h('span', { class: 'ta-icon' });
    if (JJK.Icons) icon.appendChild(JJK.Icons.trait(row.id));
    el.appendChild(icon);
    var txt = h('div', { class: 'ta-text' });
    txt.appendChild(h('div', { class: 'ta-name', text: row.info.name + ' 激 活' }));
    txt.appendChild(h('div', { class: 'ta-tier', text: '第 ' + row.level + ' 档 · 场上 ' + row.count + ' 名' }));
    el.appendChild(txt);
    document.body.appendChild(el);
    setTimeout(function () { if (el.parentNode) el.parentNode.removeChild(el); }, 2200);
    // 触发一次左右震屏，强化"变强"的体感
    JJK.FX.shake(4);
  }

  // 数值变化时在锚点旁飘一个小数字
  function floatDelta(anchorEl, text, dir) {
    if (!anchorEl) return;
    var r = anchorEl.getBoundingClientRect();
    var el = h('div', {
      class: 'float-delta ' + (dir > 0 ? 'up' : 'down'),
      text: (dir > 0 ? '+' : '') + text,
      style: { left: (r.left + r.width / 2) + 'px', top: (r.top - 4) + 'px' }
    });
    document.body.appendChild(el);
    setTimeout(function () { if (el.parentNode) el.parentNode.removeChild(el); }, 1000);
  }

  // 升级横幅
  function showLevelUp(level) {
    var old = document.querySelector('.levelup-banner');
    if (old && old.parentNode) old.parentNode.removeChild(old);
    var el = h('div', { class: 'levelup-banner' }, [
      h('div', { class: 'lb-main', text: '人 口 提 升' }),
      h('div', { class: 'lb-sub', text: 'LEVEL ' + level + ' · 可上场 ' + level + ' 名' })
    ]);
    document.body.appendChild(el);
    setTimeout(function () { if (el.parentNode) el.parentNode.removeChild(el); }, 1900);
    JJK.Audio.play('levelup');
    JJK.FX.shake(6);
  }

  JJK.Panels = {
    showLevelUp: showLevelUp,
    floatDelta: floatDelta,
    showTraitBanner: showTraitBanner,
    init: init,
    renderHud: renderHud,
    renderTraits: renderTraits,
    renderItems: renderItems,
    renderLog: renderLog,
    renderIntel: renderIntel,
    renderCombat: renderCombat,
    renderTips: renderTips
  };

})(window);
