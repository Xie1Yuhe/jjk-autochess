/* =========================================================================
 *  screens.js —— 标题页 / 回合结算 / 终局 / 设置 / 通用确认框
 * ========================================================================= */
(function (global) {
  'use strict';

  var JJK = global.JJK = global.JJK || {};
  var U = JJK.util, D = JJK.data, W = JJK.Widgets, h = U.h;

  var app = null;
  var root = null;
  var modalOpen = false;

  var DIFF_DESC = [
    '简单：对手起步资金只有 6 金，搜卡也更保守，适合先熟悉羁绊与节奏。',
    '普通：对手经济与你相当，会按回合节奏补强阵容，是最标准的体验。',
    '困难：对手起步 14 金、每回合买得更多，强度曲线也更陡，请务必规划好利息。'
  ];

  function init(appRef) {
    app = appRef;
    root = document.getElementById('modal-root');
    buildTitleBg();
    buildTitleMarquee();
    if (JJK.Decks) JJK.Decks.renderPicker(document.getElementById('deck-picker'));
    syncTitleStats();
    wireTitle();
  }

  /* ============================================================== 标题 */
  /**
   * 标题页统计：棋子数、角色数、异格数、羁绊、咒具、联动…一律从数据现算。
   * HTML 里用 data-stat="xxx" 占位，这里统一填充，加卡改羁绊都不用手改 HTML。
   */
  function syncTitleStats() {
    var units = D.units || [];
    var bases = {};
    units.forEach(function (u) { bases[u.baseCharacter] = 1; });
    var baseCount = Object.keys(bases).length;
    // 「异格」= 同一角色除第一张之外的卡
    var variants = Math.max(0, units.length - baseCount);
    var traitCount = (D.raw.traits || []).length;
    var tierCount = (D.raw.traits || []).reduce(function (n, t) {
      return n + ((t.tiers && t.tiers.length) || 0);
    }, 0);
    var stats = {
      units: units.length,
      bases: baseCount,
      variants: variants,
      traits: traitCount,
      tiers: tierCount,
      items: (D.raw.items || []).length,
      links: (D.raw.links || []).length,
      ults: units.filter(function (u) { return u.ult && u.ult.combat; }).length,
      diffs: 3
    };
    var nodes = document.querySelectorAll('[data-stat]');
    for (var i = 0; i < nodes.length; i++) {
      var k = nodes[i].getAttribute('data-stat');
      if (stats[k] !== undefined) nodes[i].textContent = String(stats[k]);
    }
    return stats;
  }

  /** 标题页背景：一张虚化的卡面当底纹 */
  function buildTitleBg() {
    var blur = document.getElementById('tb-blur');
    if (!blur) return;
    var back = D.unitById['640936'];
    if (back) blur.style.backgroundImage = 'url("' + back.card + '")';
  }

  /**
   * 标题页右侧：全部 111 张卡分两列上下滚动。
   * 左列往上、右列往下，速度略有差异，避免看起来像同一张图。
   */
  function buildTitleMarquee() {
    var host = document.getElementById('tb-fan');
    if (!host) return;
    var all = (D.units || []).filter(function (u) { return u.card; });
    if (!all.length) return;
    // 按费用排一下，滚动时品质层次更清楚
    all.sort(function (a, b) { return (a.cost - b.cost) || (a.id < b.id ? 1 : -1); });

    var nCols = 3;
    var per = Math.ceil(all.length / nCols);
    var cols = [];
    for (var ci = 0; ci < nCols; ci++) cols.push(all.slice(ci * per, (ci + 1) * per));

    host.innerHTML = '';
    host.classList.add('is-marquee');

    cols.forEach(function (list, ci) {
      var col = h('div', { class: 'tbm-col' + (ci % 2 ? ' is-down' : '') });
      var track = h('div', { class: 'tbm-track' });
      // 复制一份接在后面，做出无缝循环
      list.concat(list).forEach(function (u) {
        var card = h('div', { class: 'tbm-card' });
        card.appendChild(h('img', { src: u.card, alt: u.name, draggable: 'false' }));
        var cost = h('div', { class: 'tbm-cost', text: String(u.cost) });
        cost.style.background = u.rarityColor || '#8b95a7';
        card.appendChild(cost);
        var em = D.elemMeta(u.element);
        var el2 = h('div', { class: 'tbm-elem', text: em.glyph });
        el2.style.background = em.color;
        card.appendChild(el2);
        card.addEventListener('mouseenter', function () {
          JJK.Tooltip.showUnit(u.id, card, { star: 1, items: [] });
        });
        card.addEventListener('mouseleave', function () { JJK.Tooltip.hide(); });
        track.appendChild(card);
      });
      col.style.setProperty('--dur', (70 + ci * 14) + 's');
      col.appendChild(track);
      host.appendChild(col);
    });
  }

  function wireTitle() {
    var diffWrap = document.getElementById('title-diff');
    var desc = document.getElementById('diff-desc');
    var current = 1;

    function setDiff(d) {
      current = d;
      U.qsa('.diff-opt', diffWrap).forEach(function (b) {
        b.classList.toggle('is-on', +b.dataset.diff === d);
      });
      desc.textContent = DIFF_DESC[d];
      JJK.Audio.play('click');
    }
    diffWrap.addEventListener('click', function (e) {
      var b = e.target.closest('.diff-opt');
      if (b) setDiff(+b.dataset.diff);
    });

    document.getElementById('btn-start-game').addEventListener('click', function () {
      closeModal();
      app.startNewGame(current);
    });
    document.getElementById('btn-continue').addEventListener('click', function () {
      closeModal();
      app.continueGame();
    });
    document.getElementById('btn-title-codex').addEventListener('click', function () {
      JJK.Codex.open('units');
    });
    document.getElementById('btn-title-help').addEventListener('click', function () {
      JJK.Codex.open('rules');
    });
  }

  function showTitle() {
    document.getElementById('screen-title').classList.add('is-active');
    document.getElementById('screen-game').classList.remove('is-active');
    var btn = document.getElementById('btn-continue');
    if (btn) btn.hidden = !(app.game && app.game.hasSave());
    JJK.Audio.stopAmbient();
    if (JJK.Audio.isEnabled()) JJK.Audio.startAmbient();
  }

  function showGame() {
    document.getElementById('screen-title').classList.remove('is-active');
    document.getElementById('screen-game').classList.add('is-active');
    if (app && app.markReflow) app.markReflow();
  }

  /* ============================================================== 通用 */
  function openModal(node) {
    U.clear(root);
    root.classList.add('is-open');
    var veil = h('div', { class: 'modal-veil' });
    veil.addEventListener('click', function () {
      if (node.dataset.dismissible !== 'false') closeModal();
    });
    root.appendChild(veil);
    root.appendChild(node);
    modalOpen = true;
    return node;
  }

  function closeModal() {
    modalOpen = false;
    root.classList.remove('is-open');
    U.clear(root);
  }

  function closeBtn(onClick) {
    var b = h('button', { class: 'modal-close', text: '✕' });
    b.addEventListener('click', onClick || closeModal);
    return b;
  }

  /* ============================================================== 确认 */
  function confirm(opts) {
    var modal = h('div', { class: 'modal confirm' });
    var head = h('div', { class: 'modal-head' });
    head.appendChild(h('div', { class: 'modal-title', text: opts.title || '确认' }));
    head.appendChild(closeBtn(function () { closeModal(); if (opts.onCancel) opts.onCancel(); }));
    modal.appendChild(head);
    var body = h('div', { class: 'modal-body' });
    var txt = h('div', { class: 'confirm-text' });
    txt.innerHTML = opts.text || '';
    body.appendChild(txt);
    modal.appendChild(body);
    var foot = h('div', { class: 'modal-foot' });
    var cancel = h('button', { class: 'btn btn-ghost', text: opts.cancelText || '取消' });
    cancel.addEventListener('click', function () {
      closeModal();
      if (opts.onCancel) opts.onCancel();
    });
    var ok = h('button', { class: 'btn ' + (opts.danger ? 'btn-danger' : 'btn-gold'), text: opts.okText || '确定' });
    ok.addEventListener('click', function () {
      closeModal();
      if (opts.onOk) opts.onOk();
    });
    foot.appendChild(cancel);
    foot.appendChild(ok);
    modal.appendChild(foot);
    openModal(modal);
    JJK.Audio.play('click');
    return modal;
  }

  /* ============================================================== 结算 */
  function showResult(res) {
    if (!res) return;
    var won = res.won;
    res.myLeft = res.myLeft || [];
    res.foeLeft = res.foeLeft || [];
    var modal = h('div', { class: 'modal result' });
    modal.dataset.dismissible = 'false';

    var hero = h('div', { class: 'result-hero' + (won ? '' : ' lose') });
    hero.appendChild(h('div', { class: 'rh-glow' }));
    hero.appendChild(h('div', { class: 'rh-verdict', text: won ? '胜 利' : '败 北' }));
    hero.appendChild(h('div', {
      class: 'rh-sub',
      text: (res.kind === 'pve' ? 'PvE · ' + res.enemyName : '对战 · ' + res.enemyName) + ' · 用时 ' + res.duration.toFixed(1) + 's'
    }));
    modal.appendChild(hero);

    var grid = h('div', { class: 'result-grid' });
    grid.appendChild(h('div', { class: 'result-cell surv' }, [
      h('div', { class: 'rc-label', text: '我方存活' }),
      h('div', { class: 'rc-value', text: String(res.myLeft.length) })
    ]));
    grid.appendChild(h('div', { class: 'result-cell dmg' }, [
      h('div', { class: 'rc-label', text: won ? '造成伤害' : '受到伤害' }),
      h('div', { class: 'rc-value', text: String(res.dmg) })
    ]));
    grid.appendChild(h('div', { class: 'result-cell inc' }, [
      h('div', { class: 'rc-label', text: '本回合收入' }),
      h('div', { class: 'rc-value', text: '+' + ((res.income ? res.income.total : 0)) })
    ]));
    modal.appendChild(grid);

    // ---- 战斗总结：逐单位 伤害 / 承伤 / 治疗 ----
    var stats = (res.stats || []).slice();
    if (stats.length) {
      var mine = stats.filter(function (r) { return r.team === 0; });
      var foes = stats.filter(function (r) { return r.team !== 0; });
      mine.sort(function (a, b) { return b.dealt - a.dealt; });
      foes.sort(function (a, b) { return b.dealt - a.dealt; });
      var maxV = 1;
      stats.forEach(function (r) {
        maxV = Math.max(maxV, r.dealt, r.taken, r.heal);
      });

      var wrap = h('div', { class: 'bsum' });
      wrap.appendChild(h('div', { class: 'bsum-title', text: '战 斗 总 结' }));

      function side(list, isFoe) {
        var col = h('div', { class: 'bsum-col' + (isFoe ? ' foe' : '') });
        col.appendChild(h('div', { class: 'bsum-head', text: isFoe ? '敌 方' : '我 方' }));
        var totals = { dealt: 0, taken: 0, heal: 0 };
        list.forEach(function (r) {
          totals.dealt += r.dealt; totals.taken += r.taken; totals.heal += r.heal;
        });
        var trow = h('div', { class: 'bsum-total' }, [
          h('span', { text: '合计' }),
          h('b', { text: String(totals.dealt) }),
          h('span', { class: 'bs-dim', text: '伤' }),
          h('b', { text: String(totals.taken) }),
          h('span', { class: 'bs-dim', text: '承' }),
          h('b', { text: String(totals.heal) }),
          h('span', { class: 'bs-dim', text: '疗' })
        ]);
        col.appendChild(trow);

        list.forEach(function (r, idx) {
          var row = h('div', { class: 'bsum-row' + (r.alive ? '' : ' is-dead') });
          row.appendChild(h('div', { class: 'bsum-rank', text: String(idx + 1) }));
          // 只显示角色名，异格前缀放进 title，避免窄栏被截断
          var shortName = String(r.name || '').replace(/^\[[^\]]*\]\s*/, '');
          row.appendChild(h('div', { class: 'bsum-nm', text: shortName, title: r.name }));
          ['dealt', 'taken', 'heal'].forEach(function (k) {
            var v = r[k];
            var cell = h('div', { class: 'bsum-v ' + k });
            var bar = h('i', { });
            bar.style.width = Math.max(2, (v / maxV) * 100) + '%';
            cell.appendChild(bar);
            cell.appendChild(h('span', { text: v ? String(v) : '—' }));
            row.appendChild(cell);
          });
          col.appendChild(row);
        });
        return col;
      }

      var cols = h('div', { class: 'bsum-cols' });
      cols.appendChild(side(mine, false));
      cols.appendChild(side(foes, true));
      wrap.appendChild(cols);
      wrap.appendChild(h('div', { class: 'bsum-legend' }, [
        h('span', { class: 'lg d', text: '伤害' }),
        h('span', { class: 'lg t', text: '承伤' }),
        h('span', { class: 'lg h', text: '治疗' }),
        h('span', { class: 'bs-dim', text: '灰掉的表示已阵亡 · 按伤害降序' })
      ]));
      modal.appendChild(wrap);
    }

    var detail = h('div', { class: 'result-detail' });
    var inc = res.income || { base: 5, interest: 0, streak: 0, pve: 0, total: 0 };
    detail.appendChild(h('div', { class: 'rd-row' }, [
      h('span', { class: 'rd-k', text: '收入拆解' }),
      h('span', {
        class: 'rd-v',
        html: '基础 <b>5</b> + 利息 <b>' + inc.interest + '</b> + 连势 <b>' + inc.streak + '</b>' +
          (inc.pve ? ' + PvE <b>' + inc.pve + '</b>' : '')
      })
    ]));
    if (res.rewards && res.rewards.length) {
      detail.appendChild(h('div', { class: 'rd-row' }, [
        h('span', { class: 'rd-k', text: 'PvE 掉落' }),
        h('span', { class: 'rd-v', text: res.rewards.join('、') + '（各 1 件）' })
      ]));
    }
    detail.appendChild(h('div', { class: 'rd-row' }, [
      h('span', { class: 'rd-k', text: won ? '敌方存活' : '敌方存活' }),
      h('span', {
        class: 'rd-v',
        text: res.foeLeft.length ? res.foeLeft.slice(0, 6).join('、') + (res.foeLeft.length > 6 ? ' 等' : '') : '无'
      })
    ]));
    if (app.game) {
      detail.appendChild(h('div', { class: 'rd-row' }, [
        h('span', { class: 'rd-k', text: '当前状态' }),
        h('span', {
          class: 'rd-v',
          html: '生命 <b>' + app.game.hp + '</b> · 金币 <b>' + app.game.gold + '</b> · 等级 <b>' + app.game.level + '</b>' +
            (app.game.battleKind === 'ai' ? ' · 对手生命 <b>' + app.game.ai.hp + '</b>' : '')
        })
      ]));
    }
    modal.appendChild(detail);

    var foot = h('div', { class: 'modal-foot' });
    foot.style.justifyContent = 'center';
    var next = h('button', { class: 'btn btn-gold btn-lg', text: '进 入 第 ' + (app.game.round + 1) + ' 回 合' });
    next.addEventListener('click', function () {
      closeModal();
      app.continueRound();
    });
    foot.appendChild(next);
    modal.appendChild(foot);

    openModal(modal);
    if (won) JJK.Audio.play('victory'); else JJK.Audio.play('defeat');
  }

  /* ============================================================== 终局 */
  function showGameOver(info) {
    var modal = h('div', { class: 'modal gameover' });
    modal.dataset.dismissible = 'false';
    var win = info.win;

    var hero = h('div', { class: 'go-hero' });
    hero.appendChild(h('div', { class: 'go-rank' + (win ? '' : ' lose'), text: '第 ' + info.rank + ' 名' }));
    hero.appendChild(h('div', {
      class: 'go-title',
      text: win ? '你 是 最 强 的 咒 术 师' : '你 的 咒 力 耗 尽 了'
    }));
    hero.appendChild(h('div', {
      class: 'go-sub',
      text: '存活 ' + info.round + ' 回合 · 等级 ' + info.level + ' · 剩余金币 ' + info.gold +
        ' · 难度 ' + ['简单', '普通', '困难'][info.difficulty]
    }));
    modal.appendChild(hero);

    var comps = h('div', { class: 'go-comps' });
    (info.comp || []).forEach(function (name) {
      var u = D.units.filter(function (x) { return x.name === name; })[0];
      var chip = h('span', { class: 'go-comp' });
      if (u) chip.appendChild(h('img', { src: u.icon, alt: name }));
      chip.appendChild(h('span', { text: name }));
      comps.appendChild(chip);
    });
    modal.appendChild(comps);

    var grid = h('div', { class: 'result-grid' });
    grid.appendChild(h('div', { class: 'result-cell' }, [
      h('div', { class: 'rc-label', text: '胜 / 负' }),
      h('div', { class: 'rc-value', text: info.stats.wins + ' / ' + info.stats.losses })
    ]));
    grid.appendChild(h('div', { class: 'result-cell' }, [
      h('div', { class: 'rc-label', text: '击倒棋子' }),
      h('div', { class: 'rc-value', text: String(info.stats.kills) })
    ]));
    grid.appendChild(h('div', { class: 'result-cell' }, [
      h('div', { class: 'rc-label', text: '买棋 / 刷新' }),
      h('div', { class: 'rc-value', text: info.stats.unitsBought + ' / ' + info.stats.rerolls })
    ]));
    modal.appendChild(grid);

    var foot = h('div', { class: 'modal-foot' });
    foot.style.justifyContent = 'center';
    var again = h('button', { class: 'btn btn-gold btn-lg', text: '再 来 一 局' });
    again.addEventListener('click', function () {
      closeModal();
      app.startNewGame(info.difficulty);
    });
    var title = h('button', { class: 'btn btn-ghost', text: '回到标题' });
    title.addEventListener('click', function () {
      closeModal();
      app.goTitle();
    });
    foot.appendChild(title);
    foot.appendChild(again);
    modal.appendChild(foot);

    openModal(modal);
    app.game.clearSave();
    if (win) JJK.Audio.play('victory'); else JJK.Audio.play('defeat');
  }

  /* ============================================================== 设置 */
  // 展开/收起棋盘（购买阶段商店会占住中间，点这个临时看棋盘）
  function bindBoardToggle() {
    var btn = document.getElementById('btn-board-toggle');
    if (!btn) return;
    btn.addEventListener('click', function () {
      var on = document.body.classList.toggle('board-expanded');
      var t = btn.querySelector('.bt-text');
      if (t) t.textContent = on ? '收起棋盘' : '展开棋盘';
      JJK.Audio.play('click');
    });
  }

  function openSettings() {
    var modal = h('div', { class: 'modal settings' });
    var head = h('div', { class: 'modal-head' });
    head.appendChild(h('div', { class: 'modal-title', text: '设 置' }));
    head.appendChild(closeBtn());
    modal.appendChild(head);

    var body = h('div', { class: 'modal-body' });

    function row(label, hint, ctrl) {
      var r = h('div', { class: 'setting-row' });
      var l = h('div', null, [
        h('div', { class: 'sr-label', text: label }),
        hint ? h('div', { class: 'sr-hint', text: hint }) : null
      ]);
      r.appendChild(l);
      var c = h('div', { class: 'sr-ctrl' });
      c.appendChild(ctrl);
      r.appendChild(c);
      return r;
    }

    // 音效
    var sw = h('div', { class: 'switch' + (JJK.Audio.isEnabled() ? ' is-on' : '') });
    sw.addEventListener('click', function () {
      var on = !JJK.Audio.isEnabled();
      JJK.Audio.setEnabled(on);
      sw.classList.toggle('is-on', on);
      JJK.Audio.play('click');
    });
    body.appendChild(row('音效与氛围音', 'WebAudio 实时合成，无需下载', sw));

    // 音量
    var range = h('input', { type: 'range', min: '0', max: '100', value: String(Math.round(JJK.Audio.getVolume() * 100)) });
    range.addEventListener('input', function () {
      JJK.Audio.setVolume(+range.value / 100);
    });
    body.appendChild(row('音量', '', range));

    // 战斗速度
    var seg = h('div', { class: 'seg' });
    [1, 2, 4].forEach(function (sp) {
      var b = h('button', {
        class: (app.game && app.game.battleSpeed === sp) ? 'is-on' : '',
        text: sp + 'x'
      });
      b.addEventListener('click', function () {
        app.setSpeed(sp);
        U.qsa('button', seg).forEach(function (x) { x.classList.remove('is-on'); });
        b.classList.add('is-on');
        JJK.Audio.play('click');
      });
      seg.appendChild(b);
    });
    body.appendChild(row('战斗速度', '按 HUD 右上角也能切换', seg));

    // 存档
    var saveState = app.game && app.game.hasSave();
    var saveBtn = h('button', { class: 'btn btn-sm btn-ghost', text: '清除存档' });
    saveBtn.addEventListener('click', function () {
      confirm({
        title: '清除存档',
        text: '确定要<b>删除本地存档</b>吗？此操作不可撤销。',
        danger: true,
        okText: '删除',
        onOk: function () {
          app.game.clearSave();
          var c = document.getElementById('btn-continue');
          if (c) c.hidden = true;
          app.toast('存档已清除', 'warn');
          openSettings();
        }
      });
    });
    // 必杀奥义图开关
    var ultOn = localStorage.getItem('jjk_ultcut') !== '0';
    var ultSw = h('div', { class: 'switch' + (ultOn ? ' is-on' : '') });
    ultSw.addEventListener('click', function () {
      var on = !ultSw.classList.contains('is-on');
      ultSw.classList.toggle('is-on', on);
      localStorage.setItem('jjk_ultcut', on ? '1' : '0');
      JJK.Audio.play('click');
    });
    body.appendChild(row('必杀奥义图', '放必杀时横贯全屏的角色立绘演出；关掉可以加快节奏',
      ultSw));

    // 领域语音播报开关（浏览器语音合成，不使用任何动画原声）
    var vOn = JJK.Audio.isVoiceOn ? JJK.Audio.isVoiceOn() : true;
    var vSw = h('div', { class: 'switch' + (vOn ? ' is-on' : '') });
    vSw.addEventListener('click', function () {
      var on = !vSw.classList.contains('is-on');
      vSw.classList.toggle('is-on', on);
      if (JJK.Audio.setVoice) JJK.Audio.setVoice(on);
      if (on && JJK.Audio.announceDomain) JJK.Audio.announceDomain('無量空処');
      JJK.Audio.play('click');
    });
    body.appendChild(row('领域展开播报',
      '用系统语音朗读「領域展開·领域名」。不引用任何动画原声（版权原因）',
      vSw));

    body.appendChild(row('本地存档', saveState ? '当前有一份进行中的对局' : '暂无存档', saveBtn));

    modal.appendChild(body);

    var foot = h('div', { class: 'modal-foot' });
    foot.style.justifyContent = 'space-between';
    var restart = h('button', { class: 'btn btn-danger btn-sm', text: '放弃本局' });
    restart.addEventListener('click', function () {
      confirm({
        title: '放弃本局',
        text: '当前对局进度会丢失，确定回到标题吗？',
        danger: true,
        okText: '放弃',
        onOk: function () {
          if (app.game) app.game.clearSave();
          app.goTitle();
        }
      });
    });
    var back = h('button', { class: 'btn btn-gold', text: '完成' });
    back.addEventListener('click', function () { closeModal(); });
    foot.appendChild(restart);
    foot.appendChild(back);
    modal.appendChild(foot);

    openModal(modal);
    JJK.Audio.play('click');
  }

  JJK.Screens = {
    init: init,
    showTitle: showTitle,
    showGame: showGame,
    showResult: showResult,
    showGameOver: showGameOver,
    openSettings: openSettings,
    confirm: confirm,
    openModal: openModal,
    closeModal: closeModal,
    isModalOpen: function () { return modalOpen; }
  };

})(window);
