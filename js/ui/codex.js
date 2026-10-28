/* =========================================================================
 *  codex.js —— 图鉴 / 规则（棋子全表 / 羁绊全表 / 咒具 / 玩法）
 * ========================================================================= */
(function (global) {
  'use strict';

  var JJK = global.JJK = global.JJK || {};
  var U = JJK.util, D = JJK.data, W = JJK.Widgets, h = U.h;

  var app = null;
  var root = null;
  var isOpen = false;
  var tab = 'units';
  var costFilter = 0;
  var elemFilter = '';
  var query = '';
  var pickId = null;

  function init(appRef) {
    app = appRef;
    root = document.getElementById('modal-root');
  }

  function open(initialTab) {
    if (initialTab) tab = initialTab;
    isOpen = true;
    render();
    JJK.Audio.play('click');
  }

  function close() {
    isOpen = false;
    pickId = null;
    root.classList.remove('is-open');
    U.clear(root);
  }

  function render() {
    root.classList.add('is-open');
    U.clear(root);

    var veil = h('div', { class: 'modal-veil' });
    veil.addEventListener('click', close);
    root.appendChild(veil);

    var modal = h('div', { class: 'modal codex' });

    /* 头部 */
    var head = h('div', { class: 'modal-head codex-head' });
    head.appendChild(h('div', { class: 'modal-title', text: '图 鉴' }));
    head.appendChild(h('div', { class: 'modal-sub', text: '共 ' + D.units.length + ' 名棋子 · ' + D.traits.length + ' 条羁绊 · ' + D.items.length + ' 件咒具' }));

    var tabs = h('div', { class: 'codex-tabs' });
    [['units', '棋子'], ['traits', '羁绊'], ['items', '咒具'], ['rules', '玩法']].forEach(function (t) {
      var b = h('button', { class: 'codex-tab' + (tab === t[0] ? ' is-on' : ''), text: t[1] });
      b.addEventListener('click', function () {
        tab = t[0];
        pickId = null;
        render();
        JJK.Audio.play('click');
      });
      tabs.appendChild(b);
    });
    head.appendChild(tabs);

    if (tab === 'units') {
      var search = h('div', { class: 'codex-search' });
      var input = h('input', { placeholder: '搜索名称 / 羁绊…', value: query });
      input.addEventListener('input', function () {
        query = input.value.trim();
        renderUnitsBody();
      });
      search.appendChild(h('span', { text: '搜', style: 'font-size:11px;color:var(--text-faint)' }));
      search.appendChild(input);
      head.appendChild(search);
    }

    var closeBtn = h('button', { class: 'modal-close', text: '✕' });
    closeBtn.addEventListener('click', close);
    head.appendChild(closeBtn);
    modal.appendChild(head);

    /* 主体 */
    var body = h('div', { class: 'codex-body', id: 'codex-body' });
    modal.appendChild(body);

    root.appendChild(modal);
    if (tab === 'units') renderUnitsBody();
    else if (tab === 'traits') renderTraitsBody();
    else if (tab === 'items') renderItemsBody();
    else renderRulesBody();
  }

  /* ------------------------------------------------------------ 棋子 */
  function filteredUnits() {
    var list = D.units.slice();
    if (costFilter) list = list.filter(function (u) { return u.cost === costFilter; });
    if (elemFilter) list = list.filter(function (u) { return u.element === elemFilter; });
    if (query) {
      var q = query.toLowerCase();
      list = list.filter(function (u) {
        if (u.name.toLowerCase().indexOf(q) >= 0) return true;
        if ((u.title || '').toLowerCase().indexOf(q) >= 0) return true;
        return (u.traits || []).some(function (t) {
          var info = D.traitById[t];
          return (t.toLowerCase().indexOf(q) >= 0) || (info && info.name.indexOf(q) >= 0);
        });
      });
    }
    list.sort(function (a, b) {
      if (a.cost !== b.cost) return a.cost - b.cost;
      return a.name < b.name ? -1 : 1;
    });
    return list;
  }

  function renderUnitsBody() {
    var body = document.getElementById('codex-body');
    if (!body) return;
    U.clear(body);

    var filters = h('div', { class: 'codex-filters' });
    [[0, '全部'], [1, '1 费'], [2, '2 费'], [3, '3 费'], [4, '4 费'], [5, '5 费']].forEach(function (f) {
      var b = h('button', {
        class: 'codex-filter' + (costFilter === f[0] ? ' is-on' : ''),
        text: f[1]
      });
      b.addEventListener('click', function () {
        costFilter = f[0];
        renderUnitsBody();
        JJK.Audio.play('click');
      });
      filters.appendChild(b);
    });
    // 第二排：按四特性筛选
    var ef = h('div', { class: 'codex-filters', style: 'margin-top:6px' });
    [["", "全部特性"], ["行", "行"], ["幻", "幻"], ["夜", "夜"], ["影", "影"]].forEach(function (f) {
      var em = f[0] ? D.elemMeta(f[0]) : null;
      var b = h('button', {
        class: 'codex-filter' + (elemFilter === f[0] ? ' is-on' : ''),
        text: f[1]
      });
      if (em) b.style.setProperty('--tc', em.color);
      b.addEventListener('click', function () {
        elemFilter = f[0];
        renderUnitsBody();
        JJK.Audio.play('click');
      });
      ef.appendChild(b);
    });
    body.appendChild(ef);

    var count = filteredUnits().length;
    filters.appendChild(h('span', {
      style: 'margin-left:auto;font-size:11px;color:var(--text-faint);align-self:center',
      text: count + ' 名'
    }));
    body.appendChild(filters);

    var grid = h('div', { class: 'codex-grid' });
    filteredUnits().forEach(function (u) {
      var q = D.qualityOf(u.cost);
      var card = h('div', {
        class: 'codex-unit ' + W.qualityClass(u.cost),
        style: '--qc:' + q.color + ';--qg:' + q.glow + ';'
      });
      card.appendChild(h('img', { class: 'cu-art', src: u.card, alt: u.name, loading: 'lazy' }));
      card.appendChild(h('div', { class: 'cu-scrim' }));
      card.appendChild(h('div', {
        class: 'cu-rank',
        text: u.rarity || q.key,
        style: 'background:' + (u.rarityColor || q.color)
      }));
      card.appendChild(h('div', { class: 'cu-cost', text: String(u.cost) }));
      if (u.element) {
        var em = D.elemMeta(u.element);
        card.appendChild(h('div', {
          class: 'cu-elem',
          text: em.glyph,
          title: '特性：' + u.element,
          style: { '--ec': em.color, '--eg': em.glow }
        }));
      }
      var foot = h('div', { class: 'cu-foot' });
      if (u.variant) foot.appendChild(h('div', { class: 'cu-variant', text: '【' + u.variant + '】' }));
      foot.appendChild(h('div', { class: 'cu-name', text: u.baseCharacter || u.name }));
      var tr = h('div', { class: 'cu-traits' });
      (u.traits || []).forEach(function (t) { tr.appendChild(W.traitChip(t, false)); });
      foot.appendChild(tr);
      card.appendChild(foot);
      card.addEventListener('click', function () {
        pickId = u.id;
        renderUnitDetail(u.id);
        JJK.Audio.play('click');
      });
      card.addEventListener('mouseenter', function () {
        JJK.Tooltip.showUnit(u.id, card, { star: 1, items: [] });
      });
      card.addEventListener('mouseleave', function () { JJK.Tooltip.hide(); });
      grid.appendChild(card);
    });
    body.appendChild(grid);

    if (pickId) renderUnitDetail(pickId);
  }

  function renderUnitDetail(id) {
    var body = document.getElementById('codex-body');
    if (!body) return;
    var old = body.querySelector('.codex-detail');
    if (old) old.parentNode.removeChild(old);
    var drawer = h('div', { class: 'codex-detail' });
    var closeBtn = h('button', { class: 'modal-close', text: '✕' });
    closeBtn.style.cssText = 'position:absolute;right:12px;top:12px;z-index:3';
    closeBtn.addEventListener('click', function () {
      pickId = null;
      var d = body.querySelector('.codex-detail');
      if (d) d.parentNode.removeChild(d);
    });
    var node = JJK.Tooltip.unitNode(id, { star: 1, items: [] });
    if (node) drawer.appendChild(node);
    drawer.appendChild(closeBtn);

    // 同名异格
    var forms = (D.altForms()[D.unitById[id].name] || []).filter(function (u) { return u.id !== id; });
    if (forms.length) {
      drawer.appendChild(h('div', { class: 'gold-line', text: '同名异格' }));
      var wrap = h('div', { style: 'display:flex;gap:6px;flex-wrap:wrap;margin-top:8px' });
      forms.forEach(function (u) {
        var q = D.qualityOf(u.cost);
        var chip = h('button', {
          class: 'btn btn-xs ' + W.qualityClass(u.cost),
          style: 'border-color:' + q.color + '66;color:' + q.color,
          text: u.name + ' ' + u.cost + '费'
        });
        chip.addEventListener('click', function () {
          pickId = u.id;
          renderUnitDetail(u.id);
        });
        wrap.appendChild(chip);
      });
      drawer.appendChild(wrap);
    }
    body.appendChild(drawer);
  }

  /* ------------------------------------------------------------ 羁绊 */
  function renderTraitsBody() {
    var body = document.getElementById('codex-body');
    if (!body) return;
    U.clear(body);

    var counts = {};
    if (app && app.game) {
      app.game.boardUnits().forEach(function (inst) {
        (D.unitById[inst.id].traits || []).forEach(function (t) { counts[t] = (counts[t] || 0) + 1; });
      });
    }

    var wrap = h('div', { class: 'codex-traits' });
    D.traitTypes().forEach(function (t) {
      var color = D.traitColor(t.id);
      var cnt = counts[t.id] || 0;
      var level = 0;
      (t.tiers || []).forEach(function (tier, i) { if (cnt >= tier.count) level = i + 1; });

      var box = h('div', { class: 'codex-trait', style: '--tc:' + color });
      var head = h('div', { class: 'ct-head' });
      head.appendChild(h('span', { class: 'ct-glyph', text: t.glyph || t.name[0] }));
      head.appendChild(h('span', { class: 'ct-name', text: t.name }));
      head.appendChild(h('span', {
        class: 'ct-kind',
        text: ({ element: '元素', class: '职业', faction: '阵营' })[t.type] || ''
      }));
      head.appendChild(h('span', {
        class: 'ct-count',
        text: '场上 ' + cnt + ' 名' + (level ? ' · 已激活 ' + level + ' 档' : '')
      }));
      box.appendChild(head);

      var tiers = h('div', { class: 'ct-tiers' });
      (t.tiers || []).forEach(function (tier) {
        var on = cnt >= tier.count;
        tiers.appendChild(h('div', { class: 'ct-tier' + (on ? ' on' : '') }, [
          h('span', { class: 'n', text: tier.count + ' 人' }),
          h('span', { text: tier.text })
        ]));
      });
      box.appendChild(tiers);

      var members = D.units.filter(function (u) { return (u.traits || []).indexOf(t.id) >= 0; });
      var mw = h('div', { style: 'display:flex;gap:4px;flex-wrap:wrap;margin-top:8px' });
      members.forEach(function (u) {
        var q = D.qualityOf(u.cost);
        mw.appendChild(h('span', {
          class: 'chip',
          style: '--tc:' + q.color,
          text: u.cost + '费 ' + u.name
        }));
      });
      box.appendChild(mw);

      wrap.appendChild(box);
    });
    body.appendChild(wrap);
  }

  /* ------------------------------------------------------------ 咒具 */
  function renderItemsBody() {
    var body = document.getElementById('codex-body');
    if (!body) return;
    U.clear(body);
    var grid = h('div', { class: 'codex-items' });
    D.items.forEach(function (it) {
      var meta = D.itemMeta(it.id);
      var box = h('div', { class: 'codex-item' });
      var chip = W.itemChip(it.id);
      chip.style.cursor = 'default';
      box.appendChild(chip);
      var txt = h('div', { style: 'flex:1;min-width:0' });
      txt.appendChild(h('div', { class: 'ci-name', text: it.name }));
      txt.appendChild(h('div', {
        class: 'ci-kind',
        text: it.kind === 'complete' ? '成装' : '组件'
      }));
      txt.appendChild(h('div', { class: 'ci-text', text: it.text }));
      if (it.recipe) {
        txt.appendChild(h('div', {
          class: 'ci-recipe',
          text: '配方：' + it.recipe.map(function (r) { return D.itemById[r].name; }).join(' + ')
        }));
      }
      box.appendChild(txt);
      box.addEventListener('mouseenter', function () { JJK.Tooltip.showItem(it.id, box); });
      box.addEventListener('mouseleave', function () { JJK.Tooltip.hide(); });
      grid.appendChild(box);
    });
    body.appendChild(grid);

    body.appendChild(h('div', { class: 'gold-line', text: '规则', style: 'margin:20px 0 10px' }));
    body.appendChild(h('div', {
      class: 'tt-note',
      style: 'font-size:12px;line-height:1.9;color:var(--text-1)',
      html: '每名棋子最多携带 <b style="color:var(--gold)">3 件</b>咒具；' +
        '把两件组件装上同一枚棋子会自动合成成装（背包净减 2 件）。<br>' +
        '咒具可以随时卸下退回背包（右键棋子卸最后一件，或在右下角装备槽里点掉）。'
    }));
  }

  /* ------------------------------------------------------------ 规则 */
  function renderRulesBody() {
    var body = document.getElementById('codex-body');
    if (!body) return;
    U.clear(body);
    var g = app && app.game ? app.game : null;
    var wrap = h('div', { class: 'codex-rules' });

    wrap.innerHTML = [
      '<h3>一局怎么打</h3>',
      '<ul>',
      '<li>前 <b>3 回合</b>是 PvE 咒灵，击败可获得 <b>咒具组件</b>与额外金币，用来建立初始阵容。</li>',
      '<li>第 4 回合起对阵 AI 对手，双方各 100 生命。</li>',
      '<li>输掉回合时按<b>敌方存活人数</b>扣血：伤害 = 2 + 存活数 × 2 + 回合数 / 3。</li>',
      '<li>任意一方生命归零即结束。</li>',
      '</ul>',
      '<h3>经济</h3>',
      '<ul>',
      '<li>每回合收入 = 基础 <b>5</b> + 利息（每 10 金 +1，上限 <b>5</b>）+ 连胜/连败奖励（1/3/5 连 → +1/+2/+3）。</li>',
      '<li>刷新商店 <b>2 金</b>；买经验 <b>4 金 = 4 经验</b>；锁定商店免费。</li>',
      '<li>卖出返还 = 费用 × 星级倍率（1★ ×1 / 2★ ×3 / 3★ ×9）。</li>',
      '</ul>',
      '<h3>等级与商店概率</h3>',
      '<table><thead><tr><th>等级</th><th>1费</th><th>2费</th><th>3费</th><th>4费</th><th>5费</th></tr></thead><tbody>',
      '<tr><td>2</td><td>100</td><td>0</td><td>0</td><td>0</td><td>0</td></tr>',
      '<tr><td>3</td><td>75</td><td>25</td><td>0</td><td>0</td><td>0</td></tr>',
      '<tr><td>4</td><td>55</td><td>30</td><td>15</td><td>0</td><td>0</td></tr>',
      '<tr><td>5</td><td>45</td><td>33</td><td>20</td><td>2</td><td>0</td></tr>',
      '<tr><td>6</td><td>35</td><td>35</td><td>25</td><td>5</td><td>0</td></tr>',
      '<tr><td>7</td><td>22</td><td>30</td><td>30</td><td>15</td><td>3</td></tr>',
      '<tr><td>8</td><td>15</td><td>25</td><td>30</td><td>25</td><td>5</td></tr>',
      '<tr><td>9</td><td>10</td><td>15</td><td>25</td><td>30</td><td>20</td></tr>',
      '</tbody></table>',
      '<h3>升星与棋盘</h3>',
      '<ul>',
      '<li>同名 <b>3 张 1★</b> 自动合成 2★，<b>3 张 2★</b> 合成 3★（属性约为 1★ 的 1.75× / 3× 生命）。</li>',
      '<li>棋盘 8×4，你只能放在<b>左侧 4 列</b>；人口上限 = 等级。</li>',
      '<li>人口满时把棋子<b>拖到场上棋子身上</b>可以直接替换，不会被拦。</li>',
      '</ul>',
      '<h3>操作</h3>',
      '<table><tbody>',
      '<tr><td><span class="kbd">拖动</span></td><td>备战席 ↔ 棋盘；拖到右下角红框出售</td></tr>',
      '<tr><td><span class="kbd">点击 A</span> → <span class="kbd">点击 B</span></td><td>一上一下互换；都在场上则只切换选中</td></tr>',
      '<tr><td><span class="kbd">双击</span></td><td>备战席棋子自动上场</td></tr>',
      '<tr><td><span class="kbd">右键</span> 棋子</td><td>卸下最后一件咒具</td></tr>',
      '<tr><td><span class="kbd">Delete</span></td><td>卖掉选中的棋子</td></tr>',
      '<tr><td><span class="kbd">R</span> / <span class="kbd">L</span> / <span class="kbd">F</span></td><td>刷新 / 锁定 / 买经验</td></tr>',
      '<tr><td><span class="kbd">空格</span></td><td>开始战斗 / 进入下一回合</td></tr>',
      '<tr><td><span class="kbd">1-9</span></td><td>选中备战席第 N 格</td></tr>',
      '<tr><td><span class="kbd">Esc</span></td><td>关闭弹窗 / 取消选择</td></tr>',
      '</tbody></table>',
      '<h3>战斗</h3>',
      '<ul>',
      '<li>自动战斗：按攻速出手，射程内打最近敌人，否则向最近敌人移动。</li>',
      '<li>咒力满 → 释放技能；10 条羁绊共 28 个档位都会真实改变战斗行为。</li>',
      '<li><b>30 秒</b>进入加时（双方持续掉血），<b>45 秒</b>强制按存活人数判定。</li>',
      '</ul>'
    ].join('');

    if (g && g.difficulty !== undefined) {
      var diffNote = h('div', {
        class: 'tt-note',
        style: 'margin-top:12px;color:var(--text-faint)',
        text: '当前难度：' + ['简单', '普通', '困难'][g.difficulty] +
          '（难度只影响 AI 的经济与搜卡力度，不改棋子数值）'
      });
      wrap.appendChild(diffNote);
    }
    body.appendChild(wrap);
  }

  JJK.Codex = {
    init: init,
    open: open,
    close: close,
    isOpen: function () { return isOpen; }
  };

})(window);
