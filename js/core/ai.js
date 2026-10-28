/* =========================================================================
 *  ai.js —— 脚本化对手（移植自 ai_opponent.gd）
 *  真实经营金币：储蓄 → 转型 → 冲刺 三阶段；三套阵容蓝图；三档难度。
 *  难度只影响 AI 的经济与搜卡力度，不改棋子数值。
 * ========================================================================= */
(function (global) {
  'use strict';

  var JJK = global.JJK = global.JJK || {};
  var D = JJK.data;

  var AI_EXP_TABLE = [0, 2, 6, 10, 20, 36, 56, 80, 100, 140];
  var COMPONENTS = ['scroll', 'charm', 'fang', 'crystal', 'fragment', 'ward'];

  function AI(difficulty) {
    this.level_diff = Math.max(0, Math.min(2, difficulty || 0));
    this.gold = [6, 16, 28][this.level_diff];
    this.level = 2;
    this.exp = 0;
    this.hp = 100;
    this.streak = 0;
    this.owned = {};       // unitId -> 张数
    this.stars = {};       // unitId -> 星级
    this.rounds = 0;
    this.phase = 0;        // 0 蓄力 / 1 转型 / 2 冲刺
    this.logLines = [];
    this.items = [];

    var plans = D.plans || [];
    this.plan = plans.length ? plans[Math.floor(Math.random() * plans.length)] : { name: '无名阵', phase_build: [] };
    // 蓝图按费用升序，低价棋子先成型
    this.build = this.plan.phase_build.slice().sort(function (a, b) {
      return (D.unitById[a] ? D.unitById[a].cost : 1) - (D.unitById[b] ? D.unitById[b].cost : 1);
    });
    // 本局 AI 的卡组（36 张）——决定它能买到什么
    this.deck = this._makeDeck();
    this.deckSet = {};
    for (var di = 0; di < this.deck.length; di++) this.deckSet[this.deck[di]] = 1;
  }

  /* 蓝图里出现最多的两条羁绊，用来给随机卡组定主题 */
  AI.prototype._planTraits = function () {
    var cnt = {};
    for (var i = 0; i < this.build.length; i++) {
      var d = D.unitById[this.build[i]];
      if (!d) continue;
      (d.traits || []).forEach(function (t) { cnt[t] = (cnt[t] || 0) + 1; });
    }
    return Object.keys(cnt).sort(function (a, b) { return cnt[b] - cnt[a]; }).slice(0, 2);
  };

  /* 生成本局卡组：预设 / 随机（带主题偏置） */
  AI.prototype._makeDeck = function () {
    var QUOTA = { 1: 8, 2: 8, 3: 8, 4: 8, 5: 4 };
    var raw = (D.raw && D.raw.decks && D.raw.decks.decks) || [];
    if (raw.length && Math.random() < 0.45) {
      var d0 = raw[Math.floor(Math.random() * raw.length)];
      this.deckSource = d0.name;
      return d0.units.slice();
    }
    var theme = this._planTraits();
    this.deckSource = '随机卡组（' + theme.map(function (t) {
      var tr = D.traitById[t];
      return tr ? tr.name : t;
    }).join(' / ') + '）';
    var byCost = {};
    D.units.forEach(function (u) {
      if (!byCost[u.cost]) byCost[u.cost] = [];
      byCost[u.cost].push(u);
    });
    var charCount = {}, out = [];
    for (var c = 1; c <= 5; c++) {
      var pool = (byCost[c] || []).slice();
      pool.sort(function (a, b) {
        var sa = (a.traits || []).filter(function (t) { return theme.indexOf(t) >= 0; }).length;
        var sb = (b.traits || []).filter(function (t) { return theme.indexOf(t) >= 0; }).length;
        if (sb !== sa) return sb - sa;
        return Math.random() - 0.5;
      });
      var need = QUOTA[c];
      for (var i = 0; i < pool.length && need > 0; i++) {
        var u = pool[i];
        if ((charCount[u.baseCharacter] || 0) >= 2) continue;
        charCount[u.baseCharacter] = (charCount[u.baseCharacter] || 0) + 1;
        out.push(u.id);
        need -= 1;
      }
    }
    return out;
  };

  /* 是否属于本局卡组 */
  AI.prototype.inDeck = function (uid) { return !!this.deckSet[uid]; };

  AI.prototype.note = function (msg) { this.logLines.push('[对手] ' + msg); };
  AI.prototype.drainLog = function () { var l = this.logLines; this.logLines = []; return l; };

  AI.prototype.beginRound = function (playerResult, playerUnits) {
    this.rounds += 1;
    if (playerUnits && playerUnits.length) this.scout(playerUnits);

    // 收入：基础 5 + 利息（上限 5）+ 连胜/连败
    var interest = Math.min(5, Math.floor(this.gold / 10));
    var bonus = 0;
    if (playerResult > 0) this.streak = Math.max(1, this.streak + 1);
    else if (playerResult < 0) this.streak = Math.min(-1, this.streak - 1);
    var s = Math.abs(this.streak);
    if (s >= 5) bonus = 3; else if (s >= 3) bonus = 2; else if (s >= 1) bonus = 1;

    this.gold += 6 + interest + bonus;   // 与玩家同口径
    this.exp += 2;
    this._checkLevel();
    if (this.rounds <= 4) this.gold += 4;      // 前期 PvE 收益（与玩家同口径）

    if (this.rounds === 6 || this.rounds === 11) {
      for (var i = 0; i < 2; i++) {
        this.items.push(COMPONENTS[Math.floor(Math.random() * COMPONENTS.length)]);
      }
      this.note('获得 2 件咒具组件（共 ' + this.items.length + ' 件）');
    }

    this.phase = this.rounds <= 5 ? 0 : (this.rounds <= 10 ? 1 : 2);
    this._act();
  };

  AI.prototype._act = function () {
    var diff = this.level_diff;
    var targetLevel = this.phase === 0 ? 5 : (this.phase === 1 ? 7 : 8);

    // —— 升级：留底线金币 ——
    var reserve = this.phase === 0 ? [14, 8, 4][diff] : (this.phase === 1 ? 4 : 0);
    var lvGain = 0;
    var lvCap = (this.phase === 2 ? 2 : 1) + Math.floor(this.gold / 30);
    while (this.level < 9 && this.level < targetLevel && this.gold >= 4 &&
           this.gold - 4 >= reserve && lvGain < lvCap) {
      this.gold -= 4;
      this.exp += 4;
      lvGain += 1;
      this._checkLevel();
    }

    // —— 购买：先补满人口，再给已有棋子补同名 ——
    var ownedCount = this._ownedCount();
    var bought = 0;
    var buyCap = (this.phase < 2 ? 2 : 3) + diff;
    for (var i = 0; i < this.build.length; i++) {
      var uid = this.build[i];
      if (ownedCount >= this.level || bought >= buyCap) break;
      var d = D.unitById[uid];
      if (!d) continue;
      if (!this.inDeck(uid)) continue;          // 卡组外的棋子不买
      if ((this.owned[uid] || 0) > 0) continue;
      var keep = this.phase === 0 ? 6 : (this.phase === 1 ? 3 : 0);
      if (this.gold - d.cost < keep) continue;
      this.gold -= d.cost;
      this.owned[uid] = (this.owned[uid] || 0) + 1;
      ownedCount += 1;
      bought += 1;
      this._refreshStar(uid);
    }

    // —— 冲星：给已有低价棋子补同名 ——
    var dup = 0;
    var dupCap = 2 + Math.floor(this.gold / 8) + diff;
    for (var j = 0; j < this.build.length; j++) {
      var u2 = this.build[j];
      if (dup >= dupCap) break;
      if ((this.owned[u2] || 0) <= 0 || (this.owned[u2] || 0) >= 9) continue;
      var d2 = D.unitById[u2];
      if (!d2 || d2.cost > 3) continue;
      var keep2 = this.phase < 2 ? 2 : 0;
      if (this.gold - d2.cost < keep2) continue;
      this.gold -= d2.cost;
      this.owned[u2] = (this.owned[u2] || 0) + 1;
      dup += 1;
      this._refreshStar(u2);
    }

    // —— 重搜（冲刺期频繁） ——
    var rolls = 0;
    if (this.phase === 2) rolls = 3 + diff;
    else if (this.phase === 1 && this.gold > 45) rolls = 1;

    for (var k = 0; k < rolls; k++) {
      if (this.gold < 1) break;
      this.gold -= 1;
      // 从自己的 36 张卡组里抽，优先补「已有棋子」和「能升星」的
      var self = this;
      var pool = this.deck.filter(function (x) {
        var dd = D.unitById[x];
        return dd && dd.cost <= (self.phase === 2 ? 5 : 4);
      });
      if (!pool.length) continue;
      var weighted = [];
      for (var wi = 0; wi < pool.length; wi++) {
        var wid = pool[wi];
        var n = this.owned[wid] || 0;
        var w = 1;
        if (n > 0) w += 3;                       // 已拥有：优先补齐
        if (n === 1 || n === 2) w += 3;          // 差一张就升星
        if (n >= 9) w = 0;                       // 已满星
        // —— 针对玩家阵容的应对 ——
        var rd = this.read;
        if (rd) {
          var wd = D.unitById[wid];
          if (rd.elemHeavy && rd.counterElem && wd && wd.element === rd.counterElem) w += 4;
          if (rd.magicHeavy && wd && (wd.mods || {}).mres) w += 3;
          if (rd.physHeavy && wd && (wd.mods || {}).armor) w += 3;
          if (rd.magicHeavy && wd && (wd.mods || {}).dodge) w += 2;
        }
        for (var wj = 0; wj < w; wj++) weighted.push(wid);
      }
      if (!weighted.length) continue;
      var pickId = weighted[Math.floor(Math.random() * weighted.length)];
      if ((this.owned[pickId] || 0) < 9) {
        this.owned[pickId] = (this.owned[pickId] || 0) + 1;
        this._refreshStar(pickId);
      }
    }

    if (this.phase === 0 && bought === 0) this.note('蓄力期：金币 ' + this.gold + '，保留利息不出手');
    else if (this.phase === 1 && bought > 0) this.note('转型期：购入 ' + bought + ' 名棋子，转向「' + this.plan.name + '」');
    else if (this.phase === 2 && rolls > 0) this.note('冲刺期：连续搜卡 ' + rolls + ' 次，孤注一掷');
  };

  /* ---------------------------------------------------- 侦察 ----------- */
  // 四属性克制链：行克幻 · 幻克夜 · 夜克影 · 影克行
  var ELEM_BEATS = { '行': '幻', '幻': '夜', '夜': '影', '影': '行' };

  AI.prototype.scout = function (units) {
    var phys = 0, spell = 0, melee = 0, ranged = 0;
    var elem = {};
    var carry = null;
    for (var i = 0; i < units.length; i++) {
      var u = units[i];
      var d = D.unitById[u.id] || u;
      if (!d) continue;
      if ((d.dmg || '') === '体术') phys += 1; else spell += 1;
      if ((d.range || 1) <= 1) melee += 1; else ranged += 1;
      var e = d.element;
      if (e) elem[e] = (elem[e] || 0) + 1;
      if (!carry || (d.cost || 0) > (D.unitById[carry.id] ? D.unitById[carry.id].cost : 0)) {
        carry = { id: u.id, x: (u.pos && u.pos.x) || 0, y: (u.pos && u.pos.y) || 0 };
      }
    }
    // 玩家主力属性
    var topElem = null, topN = 0;
    for (var k in elem) if (elem[k] > topN) { topN = elem[k]; topElem = k; }
    // 用来反制玩家主力的属性：找 beats X == topElem 的那个
    var counterElem = null;
    for (var ce in ELEM_BEATS) if (ELEM_BEATS[ce] === topElem) counterElem = ce;

    var r = {
      phys: phys, spell: spell, total: Math.max(1, units.length),
      melee: melee, ranged: ranged,
      topElem: topElem, topElemN: topN, counterElem: counterElem,
      carry: carry
    };
    // 只有在倾向明显时才「承认」这是威胁，避免每回合都改主意
    r.magicHeavy = (spell / r.total) >= 0.6;
    r.physHeavy = (phys / r.total) >= 0.6;
    r.elemHeavy = topN >= Math.max(2, Math.ceil(r.total * 0.5));
    this.read = r;

    var bits = [];
    if (r.magicHeavy) bits.push('术式偏多');
    if (r.physHeavy) bits.push('体术偏多');
    if (r.elemHeavy && counterElem) bits.push('主打「' + topElem + '」，用「' + counterElem + '」反制');
    if (bits.length) this.note('侦察：' + bits.join('，'));
    return r;
  };

  AI.prototype._checkLevel = function () {
    while (this.level < 9 && this.exp >= AI_EXP_TABLE[this.level]) {
      this.exp -= AI_EXP_TABLE[this.level];
      this.level += 1;
      this.note('人口提升到 ' + this.level);
    }
  };

  AI.prototype._refreshStar = function (uid) {
    var c = this.owned[uid] || 0;
    var s = this.stars[uid] || 1;
    var maxStar = this.rounds >= 10 ? 3 : 2;    // 与玩家节奏对齐：10 回合后才允许 3 星
    while (s < maxStar && c >= 3 * Math.pow(3, s - 1)) s += 1;
    this.stars[uid] = s;
  };

  AI.prototype._ownedCount = function () {
    var n = 0;
    for (var k in this.owned) if (this.owned.hasOwnProperty(k)) n += 1;
    return n;
  };

  /* ---------------------------------------------------- 摆位 ----------- */
  // 近战在前两列（4、5），远程在后两列（6、7）；同一格不会被两个单位占用
  AI.prototype.boardUnits = function () {
    var D2 = D;
    var list = [];
    // 遍历「所有已拥有」而不是固定蓝图——否则重搜买到的棋子永远不上场
    for (var uid in this.owned) {
      if (!this.owned.hasOwnProperty(uid)) continue;
      if ((this.owned[uid] || 0) <= 0) continue;
      if (!D.unitById[uid]) continue;
      list.push({ id: uid, star: this.stars[uid] || 1 });
    }
    list.sort(function (a, b) {
      return (D2.unitById[b.id] ? D2.unitById[b.id].cost : 1) - (D2.unitById[a.id] ? D2.unitById[a.id].cost : 1);
    });
    while (list.length > this.level) list.pop();

    var taken = {};
    var jit;
    var meleeAligned = false;
    var meleeSlot = 0, rangedSlot = 0;
    var out = [];
    for (var j = 0; j < list.length; j++) {
      var e = list[j];
      var d = D.unitById[e.id];
      if (!d) continue;
      var melee = (d.range || 1) <= 1;
      var pos = null;
      var slot = melee ? meleeSlot : rangedSlot;
      // 每局给一个固定的小偏移，让摆位有变化但不至于乱
      if (jit === undefined) jit = Math.floor(Math.random() * 2);
      // 侦察到玩家主力后，近战优先贴着它那一行站
      var read = this.read;
      if (read && read.carry && melee && !meleeAligned) {
        var ty = Math.max(0, Math.min(3, read.carry.y));
        if (!taken[(4 + (jit % 2)) + ',' + ty]) {
          pos = { x: 4 + (jit % 2), y: ty };
          meleeAligned = (read.carry.y === ty);
        }
      }
      for (var tries = 0; tries < 8 && !pos; tries++) {
        if (melee) {
          var mx = 4 + ((slot + jit) % 2), my = Math.floor(slot / 2) % 4;
          if (!taken[mx + ',' + my]) pos = { x: mx, y: my };
          else slot = meleeSlot + tries + 1;
        } else {
          var rx = 6 + (slot % 2), ry = Math.floor(slot / 2) % 4;
          if (!taken[rx + ',' + ry]) pos = { x: rx, y: ry };
          else slot = rangedSlot + tries + 1;
        }
      }
      if (!pos) {
        // 兜底：任意空格
        outer:
        for (var x = 4; x < 8; x++) {
          for (var y = 0; y < 4; y++) {
            if (!taken[x + ',' + y]) { pos = { x: x, y: y }; break outer; }
          }
        }
      }
      if (!pos) continue;
      taken[pos.x + ',' + pos.y] = true;
      if (melee) meleeSlot += 1; else rangedSlot += 1;
      out.push({ id: e.id, star: e.star, pos: pos, items: [] });
    }

    // 咒具组件平摊：每人最多 2 件
    var idx = 0;
    for (var k = 0; k < this.items.length; k++) {
      if (!out.length) break;
      var target = out[idx % out.length];
      if (target.items.length < 2) target.items.push(this.items[k]);
      idx += 1;
    }
    return out;
  };

  /* ---------------------------------------------------- 强度曲线 ------- */
  // 随回合缓慢变强，并在「AI 自己落后」时小幅追赶（橡皮筋）。
  // 关键：追赶只在 AI 落后时生效 —— 玩家落后时不再叠加惩罚，
  // 否则一旦掉血就会被越滚越大，形成无法翻盘的一边倒。
  AI.prototype.powerScale = function (round, overrideHp) {
    var off = [-0.45, 0.38, 0.28][this.level_diff];
    var cap = [0.55, 1.02, 1.18][this.level_diff];
    var lo = [0.30, 0.44, 0.44][this.level_diff];
    var base = Math.max(lo, Math.min(cap, 0.52 + 0.020 * round + off));
    var hp = overrideHp === undefined ? this.hp : overrideHp;
    var behind = Math.max(0, Math.min(1, (100 - hp) / 80));
    return Math.max(1.0, Math.min(cap + 0.10, base + behind * 0.12));
  };

  AI.prototype.takeDamage = function (n) { this.hp = Math.max(0, this.hp - n); };

  JJK.AI = AI;

})(window);
