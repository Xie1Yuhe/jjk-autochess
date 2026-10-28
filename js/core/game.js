/* =========================================================================
 *  game.js —— 局内状态机（移植自 Godot 版 main.gd 的业务逻辑，不含绘制）
 *
 *  负责：经济 / 商店池 / 买经验 / 升星合成 / 棋盘与备战席 / 咒具 / 回合流程 /
 *        战斗驱动 / AI 对手 / 结算 / 存档。
 *  与 UI 的契约：改状态 → bus.emit('change', 局部标签)；战斗事件单独走 'battle:events'。
 * ========================================================================= */
(function (global) {
  'use strict';

  var JJK = global.JJK = global.JJK || {};
  var U = JJK.util;
  var D = JJK.data;

  var SHOP_SIZE = 5;
  var BENCH_SIZE = 9;
  var MAX_LEVEL = 9;
  var EXP_TABLE = [0, 2, 6, 10, 16, 26, 38, 52, 70, 92];
  var ODDS = {
    2: [100, 0, 0, 0, 0],
    3: [75, 25, 0, 0, 0],
    4: [55, 30, 15, 0, 0],
    5: [45, 33, 20, 2, 0],
    6: [35, 35, 25, 5, 0],
    7: [22, 30, 30, 15, 3],
    8: [15, 25, 30, 25, 5],
    9: [10, 15, 25, 30, 20]
  };
  // 卡池张数：参考 TFT Set18（30/25/18/10/9）。原来 4/5 费只有 8/6 张，
  // 而 3 星需要 9 张 —— 物理上不可能，这里修正。
  var POOL_SIZE = { 1: 30, 2: 25, 3: 18, 4: 12, 5: 10 };
  // 出售倍率按星级：1★=1×, 2★=3×, 3★=9×（下标就是星级）
  // 修正：原实现是 [1,1,3,9] + star-1，导致 2★ 只按 1× 返还。
  var SELL_MULT = [0, 1, 3, 9];

  // 连势查表（对齐 TFT:Gold）：3–4 连 +1；5 连 +2；6 连以上 +3；1–2 连没有奖励
  Game.STREAK_BONUS = function (streak) {
    var s = Math.max(0, streak | 0);
    return s >= 6 ? 3 : (s >= 5 ? 2 : (s >= 3 ? 1 : 0));
  };   // 按星级返还倍率
  var PVE_ROUNDS = 3;
  var COMPONENTS = ['scroll', 'charm', 'fang', 'crystal', 'fragment', 'ward'];

  var GRID_W = JJK.BATTLE.GRID_W;
  var GRID_H = JJK.BATTLE.GRID_H;

  function Game() {
    this.bus = new U.Bus();
    this.reset(1);
  }

  /* ======================================================== 生命周期 ==== */
  Game.prototype.reset = function (difficulty) {
    this.difficulty = difficulty === undefined ? 1 : difficulty;
    // 简单难度多给 3 金起步：AI 已压到下限，靠经济补偿更有效
    this.gold = 6 + (this.difficulty === 0 ? 3 : 0);
    this.itemShop = [];            // 商店里的咒具（3 格）
    this.itemPrice = 3;            // 单件咒具售价
    this.level = 2;
    this.exp = 0;
    this.hp = this.difficulty === 0 ? 130 : (this.difficulty === 1 ? 100 : 100);
    this.round = 0;
    this.winStreak = 0;
    this.loseStreak = 0;
    this.phase = 'idle';          // idle / planning / battle / result / gameover
    this.shop = [];
    this.shopLocked = false;
    this.pool = {};
    this.roster = [];
    this.nextUid = 1;
    this.itemsBag = [];
    this.pendingItem = '';
    this.selectedUid = -1;
    this.battleSpeed = 1;
    this.log = [];
    this.stats = { wins: 0, losses: 0, kills: 0, goldSpent: 0, rerolls: 0, unitsBought: 0 };
    this.battle = null;
    this.battleKind = 'pve';
    this.battleEndTimer = 0;
    this.battleElapsed = 0;
    this.lastResult = null;
    this.aiLastResult = 0;
    this.ai = new JJK.AI(this.difficulty);
    this._initPool();
    this.lastHp = this.hp;
    this.lastGold = this.gold;
  };

  Game.prototype._initPool = function () {
    this.pool = {};
    // 卡组模式：池子里只放本局卡组的棋子（默认全部 111 张）
    var allow = null;
    if (this.deckUnits && this.deckUnits.length) {
      allow = {};
      for (var k = 0; k < this.deckUnits.length; k++) allow[this.deckUnits[k]] = 1;
    }
    for (var i = 0; i < D.units.length; i++) {
      var u = D.units[i];
      if (allow && !allow[u.id]) continue;
      this.pool[u.id] = POOL_SIZE[u.cost] || 10;
    }
  };
  // 供抽卡时筛选用
  Game.prototype.inDeck = function (id) {
    if (!this.deckUnits || !this.deckUnits.length) return true;
    return this.deckUnits.indexOf(id) >= 0;
  };

  Game.prototype.newGame = function (difficulty, silent, deck) {
    this.deckId = (deck && deck.id) || '';
    this.deckName = (deck && deck.name) || '全部棋子';
    this.deckUnits = (deck && deck.units && deck.units.length) ? deck.units.slice() : null;
    this.reset(difficulty);
    this.phase = 'planning';
    if (!silent) {
      this.addLog('新局面开始 · 难度：' + ['简单', '普通', '困难'][this.difficulty], 'system');
      this.addLog('前 3 回合是 PvE 咒灵，用来建立初始阵容并掉落咒具组件。', 'info');
    }
    this.startRound();
  };

  /* ======================================================== 日志 ======== */
  Game.prototype.addLog = function (text, kind) {
    this.log.push({ text: text, kind: kind || 'info', round: this.round, time: Date.now() });
    if (this.log.length > 260) this.log.splice(0, this.log.length - 260);
    this.bus.emit('change', 'log');
  };

  /* ======================================================== 商店 ======== */
  Game.prototype._pickUnit = function (dup) {
    var odds = ODDS[Math.max(2, Math.min(9, this.level))] || ODDS[2];
    var roll = Math.floor(Math.random() * 100);
    var acc = 0, tier = 1;
    for (var i = 0; i < 5; i++) {
      acc += odds[i];
      if (roll < acc) { tier = i + 1; break; }
    }
    var cands = [];
    for (var a = 0; a < D.units.length; a++) {
      var u = D.units[a];
      if (u.cost === tier && (this.pool[u.id] || 0) > 0 && (dup[u.id] || 0) < 2) cands.push(u.id);
    }
    if (!cands.length) {
      for (var b = 0; b < D.units.length; b++) {
        var v = D.units[b];
        if ((this.pool[v.id] || 0) > 0 && (dup[v.id] || 0) < 2) cands.push(v.id);
      }
    }
    if (!cands.length) {
      for (var c = 0; c < D.units.length; c++) {
        var w = D.units[c];
        if ((this.pool[w.id] || 0) > 0) cands.push(w.id);
      }
    }
    if (!cands.length) return '';
    return cands[Math.floor(Math.random() * cands.length)];
  };

  Game.prototype.rollShop = function () {
    this.shop = [];
    var dup = {};
    for (var i = 0; i < SHOP_SIZE; i++) {
      var id = this._pickUnit(dup);
      dup[id] = (dup[id] || 0) + 1;
      this.shop.push(id);
    }
    this.bus.emit('change', 'shop');
  };

  Game.prototype.buyFromShop = function (index) {
    if (this.phase !== 'planning') return { ok: false, reason: '现在不能购买' };
    if (index < 0 || index >= this.shop.length) return { ok: false };
    var id = this.shop[index];
    if (!id) return { ok: false };
    var d = D.unitById[id];
    if (this.gold < d.cost) {
      this.addLog('金币不足（还差 ' + (d.cost - this.gold) + ' 金），无法购买「' + d.name + '」。', 'warn');
      return { ok: false, reason: 'gold' };
    }
    if (this.freeBench() < 0 && !this._canMergeIntoExisting(id)) {
      this.addLog('备战席已满，先上场或卖掉棋子。', 'warn');
      return { ok: false, reason: 'bench' };
    }
    this.gold -= d.cost;
    this.stats.goldSpent += d.cost;
    this.stats.unitsBought += 1;
    this.pool[id] = Math.max(0, (this.pool[id] || 0) - 1);
    this.shop[index] = '';
    this._addUnit(id);
    this.addLog('购入「' + d.name + '」（' + d.cost + ' 金）', 'shop');
    this.bus.emit('change', 'shop');
    this.bus.emit('change', 'gold');
    this.bus.emit('change', 'roster');
    return { ok: true, unit: d };
  };

  Game.prototype._canMergeIntoExisting = function (id) {
    var n = 0;
    for (var i = 0; i < this.roster.length; i++) {
      if (this.roster[i].id === id && this.roster[i].star === 1) n += 1;
    }
    return n >= 2;
  };

  Game.prototype.rollCost = 2;
  Game.prototype.refreshShop = function () {
    this.rollItemShop();
    if (this.phase !== 'planning') return { ok: false };
    if (this.gold < 1) {
      this.addLog('刷新需要 1 金。', 'warn');
      return { ok: false, reason: 'gold' };
    }
    this.gold -= 1;
    this.stats.goldSpent += 1;
    this.stats.rerolls += 1;
    this.rollShop();
    this.shopLocked = false;
    this.bus.emit('change', 'gold');
    this.bus.emit('change', 'shop');
    return { ok: true };
  };

  Game.prototype.toggleLock = function () {
    this.shopLocked = !this.shopLocked;
    this.addLog(this.shopLocked ? '商店已锁定，下回合不自动刷新。' : '商店已解锁。', 'system');
    this.bus.emit('change', 'shop');
    return this.shopLocked;
  };

  /* ======================================================== 经验 ======== */
  Game.prototype.nextExp = function () {
    if (this.level >= MAX_LEVEL) return 0;
    return EXP_TABLE[this.level];
  };

  Game.prototype.buyExp = function () {
    if (this.phase !== 'planning') return { ok: false };
    if (this.level >= MAX_LEVEL) {
      this.addLog('已经是 9 级，无需再买经验。', 'warn');
      return { ok: false };
    }
    if (this.gold < 4) {
      this.addLog('买经验需要 4 金。', 'warn');
      return { ok: false, reason: 'gold' };
    }
    this.gold -= 4;
    this.stats.goldSpent += 4;
    this.exp += 4;
    this._checkLevel();
    this.bus.emit('change', 'gold');
    this.bus.emit('change', 'exp');
    return { ok: true };
  };

  Game.prototype._checkLevel = function () {
    while (this.level < MAX_LEVEL && this.exp >= this.nextExp()) {
      this.exp -= this.nextExp();
      this.level += 1;
      this.addLog('人口上限提升到 ' + this.level + ' 级。', 'levelup');
      this.bus.emit('change', 'level');
    }
  };

  /* ======================================================== 棋子 ======== */
  Game.prototype.freeBench = function () {
    var used = {};
    for (var i = 0; i < this.roster.length; i++) {
      if (this.roster[i].bench >= 0) used[this.roster[i].bench] = true;
    }
    for (var b = 0; b < BENCH_SIZE; b++) if (!used[b]) return b;
    return -1;
  };

  Game.prototype._addUnit = function (id) {
    var inst = {
      uid: this.nextUid++,
      id: id,
      star: 1,
      pos: { x: -1, y: -1 },
      bench: this.freeBench(),
      items: []
    };
    this.roster.push(inst);
    var merged = this._tryCombine(id);
    // 合成后若仍然无处安放，退回金币并从池里换回
    if (inst.bench < 0 && inst.pos.x < 0 && merged.indexOf(inst) < 0) {
      var nb = this.freeBench();
      if (nb >= 0) inst.bench = nb;
      else {
        var idx = this.roster.indexOf(inst);
        if (idx >= 0) this.roster.splice(idx, 1);
        this.pool[id] = (this.pool[id] || 0) + 1;
        this.gold += D.unitById[id].cost;
      }
    }
    return inst;
  };

  // 返回被保留（升级主体）的实例数组，便于 UI 播升星动画
  Game.prototype._tryCombine = function (id) {
    var keeps = [];
    if (!id) return keeps;
    for (var star = 1; star <= 2; star++) {
      /* eslint-disable no-constant-condition */
      while (true) {
        var list = [];
        for (var i = 0; i < this.roster.length; i++) {
          var r = this.roster[i];
          if (r.id === id && r.star === star) list.push(r);
        }
        if (list.length < 3) break;
        // 优先保留棋盘上的那一张，合成后站位不变
        var keep = list[0];
        for (var k = 0; k < list.length; k++) {
          if (list[k].pos.x >= 0) { keep = list[k]; break; }
        }
        var removed = 0;
        for (var j = 0; j < list.length && removed < 2; j++) {
          if (list[j] === keep) continue;
          var idx = this.roster.indexOf(list[j]);
          if (idx >= 0) this.roster.splice(idx, 1);
          removed += 1;
        }
        keep.star = star + 1;
        keep.justUpgraded = star + 1;
        keeps.push(keep);
        this.addLog('★ 三张同名合成！「' + D.unitById[id].name + '」升到 ' + (star + 1) + ' 星。', 'upgrade');
        this.bus.emit('upgrade', { uid: keep.uid, star: keep.star, unitId: id });
      }
    }
    return keeps;
  };

  Game.prototype.unitById = function (uid) {
    for (var i = 0; i < this.roster.length; i++) if (this.roster[i].uid === uid) return this.roster[i];
    return null;
  };

  Game.prototype.unitAtCell = function (x, y) {
    for (var i = 0; i < this.roster.length; i++) {
      var r = this.roster[i];
      if (r.pos.x === x && r.pos.y === y) return r;
    }
    return null;
  };

  Game.prototype.unitAtBench = function (index) {
    for (var i = 0; i < this.roster.length; i++) {
      var r = this.roster[i];
      if (r.bench === index && r.pos.x < 0) return r;
    }
    return null;
  };

  Game.prototype.boardCount = function () {
    var n = 0;
    for (var i = 0; i < this.roster.length; i++) if (this.roster[i].pos.x >= 0) n += 1;
    return n;
  };

  Game.prototype.boardUnits = function () {
    var out = [];
    for (var i = 0; i < this.roster.length; i++) if (this.roster[i].pos.x >= 0) out.push(this.roster[i]);
    return out;
  };

  Game.prototype.benchUnits = function () {
    var out = [];
    for (var i = 0; i < this.roster.length; i++) if (this.roster[i].pos.x < 0) out.push(this.roster[i]);
    out.sort(function (a, b) { return a.bench - b.bench; });
    return out;
  };

  Game.prototype.canPlaceAt = function (x, y) {
    return x >= 0 && y >= 0 && x < 4 && y < GRID_H;
  };

  /* 拖拽/点击落子。dest = {type:'cell', x, y} | {type:'bench', index} */
  Game.prototype.placeUnit = function (uid, dest) {
    if (this.phase !== 'planning') return { ok: false, reason: 'phase' };
    var inst = this.unitById(uid);
    if (!inst) return { ok: false };

    if (dest.type === 'cell') {
      if (!this.canPlaceAt(dest.x, dest.y)) {
        return { ok: false, reason: 'territory' };
      }
      var onBoard = inst.pos.x >= 0;
      var other = this.unitAtCell(dest.x, dest.y);
      if (!onBoard && this.boardCount() >= this.level && !other) {
        this.addLog('人口已满（' + this.boardCount() + '/' + this.level + '）：把棋子拖到场上棋子身上可以直接替换。', 'warn');
        return { ok: false, reason: 'cap' };
      }
      if (other && other.uid !== uid) {
        if (onBoard) {
          other.pos = { x: inst.pos.x, y: inst.pos.y };
        } else {
          other.pos = { x: -1, y: -1 };
          other.bench = inst.bench;
        }
      }
      inst.pos = { x: dest.x, y: dest.y };
      inst.bench = -1;
      this.bus.emit('change', 'roster');
      return { ok: true };
    }

    if (dest.type === 'bench') {
      var o2 = this.unitAtBench(dest.index);
      if (o2 && o2.uid !== uid) {
        if (inst.pos.x >= 0) {
          o2.pos = { x: inst.pos.x, y: inst.pos.y };
          o2.bench = -1;
        } else {
          o2.bench = inst.bench;
        }
      }
      inst.pos = { x: -1, y: -1 };
      inst.bench = dest.index;
      this.bus.emit('change', 'roster');
      return { ok: true };
    }
    return { ok: false };
  };

  Game.prototype.swapUnits = function (uidA, uidB) {
    if (this.phase !== 'planning') return { ok: false };
    var a = this.unitById(uidA), b = this.unitById(uidB);
    if (!a || !b) return { ok: false };
    var pa = a.pos, ba = a.bench;
    a.pos = b.pos; a.bench = b.bench;
    b.pos = pa; b.bench = ba;
    this.bus.emit('change', 'roster');
    return { ok: true };
  };

  // 出售返还 = 费用 × 星级倍率 − 折旧
  // 折旧规则（对齐 TFT）：**1 费 1 星**不折旧，其余少返 1 金，最低 1 金。
  Game.prototype._refundOf = function (inst) {
    var d = D.unitById[inst.id];
    var base = d.cost * SELL_MULT[Math.max(1, Math.min(3, inst.star))];
    var depreciate = !(d.cost === 1 && inst.star === 1);
    return Math.max(1, base - (depreciate ? 1 : 0));
  };

  Game.prototype.sellInfo = function (uid) {
    var inst = this.unitById(uid);
    if (!inst) return null;
    var d = D.unitById[inst.id];
    var refund = this._refundOf(inst);
    return {
      unit: d, star: inst.star, refund: refund,
      needsConfirm: inst.star >= 2 || d.cost >= 4
    };
  };

  Game.prototype.sellUnit = function (uid) {
    if (this.phase !== 'planning') return { ok: false };
    var inst = this.unitById(uid);
    if (!inst) return { ok: false };
    var d = D.unitById[inst.id];
    var refund = this._refundOf(inst);
    this.gold += refund;
    this.pool[inst.id] = (this.pool[inst.id] || 0) + 1;
    for (var i = 0; i < inst.items.length; i++) this.itemsBag.push(inst.items[i]);
    var idx = this.roster.indexOf(inst);
    if (idx >= 0) this.roster.splice(idx, 1);
    if (this.selectedUid === uid) this.selectedUid = -1;
    this.addLog('卖出「' + d.name + '」(' + inst.star + '★)，回收 ' + refund + ' 金。', 'sell');
    this.bus.emit('change', 'gold');
    this.bus.emit('change', 'roster');
    this.bus.emit('change', 'items');
    return { ok: true, refund: refund };
  };

  // 整理备战席：按费用降序 + 同名相邻 + 空格补位
  Game.prototype.sortBench = function () {
    var bench = this.benchUnits();
    bench.sort(function (a, b) {
      var da = D.unitById[a.id], db = D.unitById[b.id];
      if (da.cost !== db.cost) return db.cost - da.cost;
      if (a.id !== b.id) return a.id < b.id ? -1 : 1;
      return b.star - a.star;
    });
    for (var i = 0; i < bench.length; i++) bench[i].bench = i;
    this.addLog('备战席已整理：高费在前、同名相邻。', 'system');
    this.bus.emit('change', 'roster');
    return true;
  };

  // 一键上阵：按费用从高到低填满人口（近战放前排、远程放后排）
  Game.prototype.autoDeploy = function () {
    if (this.phase !== 'planning') return { ok: false };
    var bench = this.benchUnits();
    bench.sort(function (a, b) {
      var da = D.unitById[a.id], db = D.unitById[b.id];
      if (da.cost !== db.cost) return db.cost - da.cost;
      return b.star - a.star;
    });
    var added = 0;
    for (var i = 0; i < bench.length; i++) {
      if (this.boardCount() >= this.level) break;
      var inst = bench[i];
      var d = D.unitById[inst.id];
      var cell = this._findFreeCell(d.range <= 1);
      if (!cell) break;
      inst.pos = cell;
      inst.bench = -1;
      added += 1;
    }
    if (added) this.addLog('自动上阵 ' + added + ' 名棋子。', 'system');
    this.bus.emit('change', 'roster');
    return { ok: true, added: added };
  };

  Game.prototype._findFreeCell = function (melee) {
    var cols = melee ? [2, 1, 0, 3] : [0, 1, 2, 3];
    for (var c = 0; c < cols.length; c++) {
      for (var y = 0; y < GRID_H; y++) {
        if (!this.unitAtCell(cols[c], y)) return { x: cols[c], y: y };
      }
    }
    return null;
  };

  /* ======================================================== 咒具 ======== */
  /* ---------------------------------------------------- 咒具商店 ------ */
  // 注意：不要用 COMPONENTS 这个名字，上面 PvE 掉落逻辑已经在用它
  var SHOP_COMPONENTS = null;
  function components() {
    if (SHOP_COMPONENTS) return SHOP_COMPONENTS;
    SHOP_COMPONENTS = (D.items || []).filter(function (it) { return it.kind === 'component'; });
    return SHOP_COMPONENTS;
  }

  // 重掷咒具商店（每回合 + 手动刷新）
  Game.prototype.rollItemShop = function () {
    var pool = components().slice();
    var out = [];
    while (out.length < 3 && pool.length) {
      var i = Math.floor(Math.random() * pool.length);
      out.push(pool[i].id);
      pool.splice(i, 1);
    }
    this.itemShop = out;
  };

  // 我方可用的组件（背包 + 已装备）——用于判断能否合成
  Game.prototype._ownedComponents = function () {
    var have = {};
    var bag = this.itemsBag || [];
    for (var i = 0; i < bag.length; i++) have[bag[i]] = true;
    for (var r = 0; r < this.roster.length; r++) {
      var its = this.roster[r].items || [];
      for (var k = 0; k < its.length; k++) have[its[k]] = true;
    }
    return have;
  };

  // 这个组件是否「买了就能合成成品」
  Game.prototype.itemMergeHint = function (itemId) {
    var have = this._ownedComponents();
    for (var i = 0; i < D.items.length; i++) {
      var c = D.items[i];
      if (c.kind !== 'complete') continue;
      var rec = c.recipe || [];
      if (rec.length !== 2 || rec.indexOf(itemId) < 0) continue;
      var other = rec[0] === itemId ? rec[1] : rec[0];
      if (have[other]) return c;      // 返回能合成的成品
    }
    return null;
  };

  // 买咒具
  Game.prototype.buyItemFromShop = function (index) {
    if (this.phase !== 'planning') return { ok: false, reason: 'phase' };
    var id = this.itemShop[index];
    if (!id) return { ok: false, reason: 'empty' };
    if (this.gold < this.itemPrice) {
      this.addLog('金币不足（需 ' + this.itemPrice + ' 金）。', 'warn');
      return { ok: false, reason: 'gold' };
    }
    this.gold -= this.itemPrice;
    this.addItemToBag(id);
    this.itemShop[index] = '';
    var it = null;
    for (var i = 0; i < D.items.length; i++) if (D.items[i].id === id) it = D.items[i];
    if (it) this.addLog('购入咒具「' + it.name + '」。', 'item');
    this.bus.emit('change', 'gold');
    this.bus.emit('change', 'items');
    this.bus.emit('change', 'shop');
    return { ok: true, item: it };
  };

  Game.prototype.selectItem = function (itemId) {
    this.pendingItem = itemId;
    this.bus.emit('change', 'items');
    return itemId;
  };

  Game.prototype.equipItem = function (uid, itemId) {
    if (this.phase !== 'planning') return { ok: false };
    var inst = this.unitById(uid);
    if (!inst) return { ok: false };
    if (inst.items.length >= 3) {
      this.addLog('该棋子已经带满 3 件咒具，先卸一件。', 'warn');
      return { ok: false, reason: 'full' };
    }
    // 组件合成成装：目标身上已有另一半时直接合成
    for (var i = 0; i < D.items.length; i++) {
      var comp = D.items[i];
      if (comp.kind !== 'complete') continue;
      var rec = comp.recipe || [];
      if (rec.length !== 2 || rec.indexOf(itemId) < 0) continue;
      var otherId = rec[0] === itemId ? rec[1] : rec[0];
      if (inst.items.indexOf(otherId) >= 0) {
        inst.items.splice(inst.items.indexOf(otherId), 1);
        inst.items.push(comp.id);
        this._bagRemove(itemId);
        this.pendingItem = '';
        this.addLog('咒具合成！「' + comp.name + '」成型（消耗 2 件组件）。', 'item');
        this.bus.emit('change', 'items');
        this.bus.emit('change', 'roster');
        this.bus.emit('crafted', { uid: uid, item: comp });
        return { ok: true, crafted: comp };
      }
    }
    inst.items.push(itemId);
    this._bagRemove(itemId);
    this.pendingItem = '';
    this.addLog(D.unitById[inst.id].name + ' 装备了「' + D.itemById[itemId].name + '」。', 'item');
    this.bus.emit('change', 'items');
    this.bus.emit('change', 'roster');
    return { ok: true, equipped: itemId };
  };

  Game.prototype._bagRemove = function (itemId) {
    var i = this.itemsBag.indexOf(itemId);
    if (i >= 0) this.itemsBag.splice(i, 1);
  };

  Game.prototype.unequip = function (uid, itemId) {
    if (this.phase !== 'planning') return { ok: false };
    var inst = this.unitById(uid);
    if (!inst) return { ok: false };
    var idx = inst.items.indexOf(itemId);
    if (idx < 0) return { ok: false };
    inst.items.splice(idx, 1);
    this.itemsBag.push(itemId);
    this.addLog('从 ' + D.unitById[inst.id].name + ' 卸下「' + D.itemById[itemId].name + '」，已退回背包。', 'item');
    this.bus.emit('change', 'items');
    this.bus.emit('change', 'roster');
    return { ok: true };
  };

  // 右键：卸下最后一件
  Game.prototype.unequipLast = function (uid) {
    var inst = this.unitById(uid);
    if (!inst || !inst.items.length) return { ok: false, reason: 'empty' };
    return this.unequip(uid, inst.items[inst.items.length - 1]);
  };

  Game.prototype.addItemToBag = function (itemId) {
    this.itemsBag.push(itemId);
    this.bus.emit('change', 'items');
  };

  /* ======================================================== 羁绊 ======== */
  Game.prototype.traitSummary = function () {
    var ids = [];
    var board = this.boardUnits();
    for (var i = 0; i < board.length; i++) ids.push(board[i].id);
    var counts = D.countTraits(ids);
    var st = D.traitStatus(counts);
    var list = [];
    for (var tid in st) {
      if (!st.hasOwnProperty(tid)) continue;
      var row = st[tid];
      var topNeed = row.tiers.length ? row.tiers[row.tiers.length - 1].count : 1;
      row.id = tid;
      row.topNeed = topNeed;
      row.progress = Math.min(row.count, topNeed) / Math.max(1, topNeed);
      list.push(row);
    }
    list.sort(function (a, b) {
      if (b.level !== a.level) return b.level - a.level;
      return b.count - a.count;
    });
    return list;
  };

  // 场上已激活的异格联动（同本体的两个异格同时在场上）
  Game.prototype.activeLinks = function () {
    var ids = {};
    var board = this.boardUnits();
    for (var i = 0; i < board.length; i++) ids[board[i].id] = true;
    var out = [];
    var defs = D.links || [];
    for (var d = 0; d < defs.length; d++) {
      var def = defs[d];
      var all = true;
      for (var m = 0; m < def.members.length; m++) {
        if (!ids[def.members[m]]) { all = false; break; }
      }
      if (all) out.push(def);
    }
    return out;
  };

  // 某个棋子是否属于已激活的联动
  Game.prototype.isLinkedUnit = function (unitId) {
    var ls = this.activeLinks();
    for (var i = 0; i < ls.length; i++) {
      if (ls[i].members.indexOf(unitId) >= 0) return ls[i];
    }
    return null;
  };

  Game.prototype.traitCountOnBoard = function (traitId) {
    var board = this.boardUnits();
    var n = 0;
    for (var i = 0; i < board.length; i++) {
      if ((D.unitById[board[i].id].traits || []).indexOf(traitId) >= 0) n += 1;
    }
    return n;
  };

  /* ======================================================== 回合 ======== */
  Game.prototype.startRound = function () {
    this.rollItemShop();
    this.round += 1;
    this.phase = 'planning';
    this.battle = null;
    this.battleEndTimer = 0;
    this.pendingItem = '';
    this.lastResult = null;

    // 每回合白给 2 点经验
    this.exp += 2;
    this._checkLevel();

    if (!this.shopLocked) this.rollShop();
    this.shopLocked = false;

    if (this.round <= PVE_ROUNDS) {
      this.battleKind = 'pve';
      var w = D.pve[this.round - 1];
      this.addLog('—— 第 ' + this.round + ' 回合：PvE · ' + (w ? w.name : '咒灵') + ' ——', 'round');
    } else {
      this.battleKind = 'ai';
      // 把玩家当前阵容交给 AI 侦察（用于属性克制 / 伤害构成 / 站位应对）
    var scoutUnits = null;
    try { scoutUnits = this._buildMyUnits().units; } catch (e) { scoutUnits = null; }
    this.ai.beginRound(this.aiLastResult, scoutUnits);
      this.addLog('—— 第 ' + this.round + ' 回合：对手【' + this.ai.plan.name + '】· 金币 ' +
        this.ai.gold + ' · 等级 ' + this.ai.level + ' ——', 'round');
      var lines = this.ai.drainLog();
      for (var i = 0; i < lines.length; i++) this.addLog(lines[i], 'ai');
    }

    this.selectedUid = -1;
    this.bus.emit('change', 'all');
    this.bus.emit('round:start', this.round);
    return this.round;
  };

  /* 对手情报：备战阶段就能看到这回合要打谁 */
  Game.prototype.opponentPreview = function () {
    if (this.round <= PVE_ROUNDS) {
      var w = D.pve[this.round - 1];
      if (!w) return null;
      var list = [];
      var slot = 0;
      for (var g = 0; g < w.enemies.length; g++) {
        var grp = w.enemies[g];
        for (var i = 0; i < (grp.count || 1); i++) {
          var pos = { x: 5 + (slot % 2), y: Math.min(GRID_H - 1, Math.floor(slot / 2)) };
          slot += 1;
          list.push({
            id: 'pve', name: grp.name, star: 1, pos: pos, element: '咒灵',
            hp: grp.hp, ad: grp.ad, range: grp.range, icon: null
          });
        }
      }
      return { kind: 'pve', name: w.name, units: list };
    }
    if (!this.ai) return null;
    var bu = this.ai.boardUnits();
    var scale = this.ai.powerScale(this.round);
    // 卡组模式：商店池只有 36 张，玩家成型更快 → 敌方相应加强，保证难度不塌
    if (this.deckUnits && this.deckUnits.length) scale *= 1.24;
    var out = [];
    for (var k = 0; k < bu.length; k++) {
      var d = D.unitById[bu[k].id];
      out.push({
        id: bu[k].id, name: d.name, star: bu[k].star, pos: bu[k].pos,
        element: d.element, icon: d.icon, hp: Math.round(d.hp * scale), ad: Math.round(d.ad * scale),
        range: d.range
      });
    }
    return { kind: 'ai', name: this.ai.plan.name, units: out, scale: scale };
  };

  Game.prototype._buildMyUnits = function () {
    var my = [], ids = [];
    for (var i = 0; i < this.roster.length; i++) {
      var inst = this.roster[i];
      if (inst.pos.x < 0) continue;
      var d = D.unitById[inst.id];
      my.push({
        id: inst.id, uid: inst.uid, name: d.name, element: d.element,
        hp: d.hp, ad: d.ad, spell: d.spell, as: d.as, range: d.range,
        mana: d.mana, start_mana: d.start_mana,
        traits: d.traits, skill: d.skill, passive: d.passive, items: inst.items.slice(),
        // 关键：ult / ultCost / mods 必须一起带过去，否则必杀与所有 mods 机制全部失效
        ult: d.ult, ultCost: d.ultCost, mods: d.mods,
        star: inst.star, pos: { x: inst.pos.x, y: inst.pos.y }
      });
      ids.push(inst.id);
    }
    return { units: my, ids: ids };
  };

  Game.prototype._buildEnemyUnits = function () {
    var enemy = [], ids = [];
    if (this.battleKind === 'pve') {
      var w = D.pve[this.round - 1];
      var slot = 0;
      for (var g = 0; g < w.enemies.length; g++) {
        var grp = w.enemies[g];
        for (var i = 0; i < (grp.count || 1); i++) {
          var pos = { x: 5 + (slot % 2), y: Math.min(GRID_H - 1, Math.floor(slot / 2)) };
          slot += 1;
          enemy.push({
            id: 'pve_' + grp.id, name: grp.name, element: '咒灵',
            hp: grp.hp, ad: grp.ad, spell: 40, as: 0.8, range: grp.range || 1,
            mana: 100, start_mana: 0, traits: [],
            skill: { name: '咒力冲击', type: 'strike', power: 1.4, desc: '' },
            passive: {}, items: [], star: 1, pos: pos
          });
        }
      }
      return { units: enemy, ids: ids };
    }
    var scale = this.ai.powerScale(this.round);
    var bu = this.ai.boardUnits();
    for (var k = 0; k < bu.length; k++) {
      var d = D.unitById[bu[k].id];
      enemy.push({
        id: bu[k].id, name: d.name, element: d.element,
        hp: d.hp * scale, ad: d.ad * scale, spell: d.spell * scale,
        as: d.as, range: d.range, mana: d.mana, start_mana: d.start_mana,
        traits: d.traits, skill: d.skill, passive: d.passive,
        ult: d.ult, ultCost: d.ultCost, mods: d.mods,
        items: bu[k].items || [], star: bu[k].star, pos: bu[k].pos
      });
      ids.push(bu[k].id);
    }
    return { units: enemy, ids: ids };
  };

  Game.prototype.beginBattle = function () {
    if (this.phase !== 'planning') return { ok: false };
    if (this.boardCount() === 0) {
      this.addLog('至少要放一名棋子上场才能开战。', 'warn');
      return { ok: false, reason: 'empty' };
    }
    var mine = this._buildMyUnits();
    var foes = this._buildEnemyUnits();
    if (!foes.units.length) {
      this.addLog('对手还没有准备好，本回合轮空直接获胜。', 'system');
      this.endRound(true, 0);
      return { ok: true, walkover: true };
    }
    var pTiers = D.traitTiersFor(mine.ids);
    var eTiers = D.traitTiersFor(foes.ids);
    this.battle = new JJK.BattleSim();
    this.battle.setup(mine.units, foes.units, pTiers, eTiers);
    this.battleMeta = {
      myCount: mine.units.length,
      foeCount: foes.units.length,
      myTraits: pTiers,
      foeTraits: eTiers,
      kind: this.battleKind,
      enemyName: this.battleKind === 'pve' ? (D.pve[this.round - 1] || {}).name : this.ai.plan.name
    };
    this.phase = 'battle';
    this.battleElapsed = 0;
    this.addLog('战斗开始：我方 ' + mine.units.length + ' 人 vs 敌方 ' + foes.units.length + ' 人。', 'battle');
    this.bus.emit('change', 'phase');
    this.bus.emit('battle:start', this.battleMeta);
    return { ok: true };
  };

  Game.prototype.setSpeed = function (speed) {
    this.battleSpeed = speed;
    this.bus.emit('change', 'speed');
  };

  // 由渲染层每帧调用
  Game.prototype.tickBattle = function (dt) {
    if (this.phase !== 'battle' || !this.battle) return;
    var step = dt * this.battleSpeed;
    this.battleElapsed += step;
    // 固定步长 1/60，避免不同刷新率下结果漂移
    var steps = Math.min(8, Math.ceil(step / (1 / 60)));
    var sub = step / steps;
    for (var i = 0; i < steps; i++) this.battle.update(sub);
    var evs = this.battle.drainEvents();
    if (evs.length) {
      for (var k = 0; k < evs.length; k++) {
        if (evs[k].t === 'death') this.stats.kills += 1;
        if (evs[k].t === 'cast' || evs[k].t === 'domain' || evs[k].t === 'overtime') {
          this.addLog(this._describeEvent(evs[k]), 'battle');
        }
      }
      this.bus.emit('battle:events', evs);
    }
    if (this.battle.over) {
      this.battleEndTimer += dt;
      if (this.battleEndTimer > 0.85) this._finishBattle();
    }
  };

  Game.prototype._describeEvent = function (e) {
    var side = e.team === 0 ? '我方' : '敌方';
    if (e.t === 'cast') return '  ' + side + ' 施放「' + e.name + '」';
    if (e.t === 'skillDomain') return '  ★ ' + side + ' 展开领域！';
    if (e.t === 'domain') return '  ★ 领域展开：' + (e.team === 0 ? '我方' : '敌方') + '全属性 +22%，体术/术式必中。';
    if (e.t === 'overtime') return '  ⏱ 进入加时：双方开始受到咒力反噬，战斗将强制结束。';
    return '';
  };

  Game.prototype._finishBattle = function () {
    if (!this.battle) return;
    var sim = this.battle;
    var won = sim.winner === 0;
    var surv = sim.survivors(won ? 0 : 1);
    var dmg = 2 + Math.round(surv * 1.3) + Math.floor(this.round / 4);   // 放缓：整局拉长到 22~30 回合
    // 简单难度：败北伤害 -45%。死亡集中在 17~21 回合，前期补偿无效，必须动后期
    if (this.difficulty === 0) dmg = Math.max(1, Math.round(dmg * 0.80));
    var foeLeft = [], myLeft = [];
    for (var i = 0; i < sim.units.length; i++) {
      var u = sim.units[i];
      if (!u.alive) continue;
      var nm = u.def.name || '咒灵';
      if (u.team === 0) myLeft.push(nm); else foeLeft.push(nm);
    }
    if (won) {
      this.winStreak += 1; this.loseStreak = 0; this.aiLastResult = 1;
      this.stats.wins += 1;
      // 这是一场「谁先死」的竞速：简单难度让 AI 掉血更快，玩家才可能赢下比赛
      if (this.battleKind === 'ai') {
        this.ai.takeDamage(this.difficulty === 0 ? Math.round(dmg * 2.30) : dmg);
      }
    } else {
      this.loseStreak += 1; this.winStreak = 0; this.aiLastResult = -1;
      this.stats.losses += 1;
      this.hp = Math.max(0, this.hp - dmg);
      this.bus.emit('hp:lost', dmg);
    }
    this.lastResult = {
      stats: (sim && sim.stats) ? sim.stats() : [],
      won: won, dmg: dmg, myLeft: myLeft, foeLeft: foeLeft,
      survivors: surv, kind: this.battleKind,
      duration: sim.time, enemyName: this.battleMeta ? this.battleMeta.enemyName : ''
    };
    this.phase = 'result';
    this.bus.emit('battle:end', this.lastResult);
    this._settleRound(won, dmg);
  };

  Game.prototype._settleRound = function (won, dmg) {
    var interest = Math.min(5, Math.floor(this.gold / 10));
    var s = Math.max(this.winStreak, this.loseStreak);
    var bonus = Game.STREAK_BONUS(s);
    // PvP 回合获胜额外 +1 金 —— 「能吃连胜就别吃连败」的经济差异来源
    var winBonus = (this.battleKind === 'ai' && won) ? 1 : 0;
    var pveBonus = this.battleKind === 'pve' ? 4 : 0;
    var income = 6 + interest + bonus + winBonus + pveBonus;
    this.gold += income;

    var rewards = [];
    if (this.battleKind === 'pve' && won && this.round <= PVE_ROUNDS) {
      for (var i = 0; i < 2; i++) {
        var id = COMPONENTS[Math.floor(Math.random() * COMPONENTS.length)];
        this.itemsBag.push(id);
        rewards.push(D.itemById[id].name);
      }
      this.gold += 2;
      this.addLog('PvE 掉落：咒具组件「' + rewards.join('」+「') + '」，额外 +2 金。', 'reward');
    }

    this.lastResult.income = {
      base: 5, interest: interest, streak: bonus, win: winBonus,
      pve: pveBonus, total: income + (rewards.length ? 2 : 0)
    };
    this.lastResult.rewards = rewards;

    this.addLog((won ? '✔ 本回合胜利' : '✘ 本回合失败') + '：' + (won ? '造成 ' + dmg + ' 点伤害' : '损失 ' + dmg + ' 点生命') +
      ' · 收入 ' + income + ' 金（基础6 + 利息' + interest + (bonus ? ' + 连势' + bonus : '') + (winBonus ? ' + 胜利1' : '') + (pveBonus ? ' + PvE3' : '') + '）',
      won ? 'win' : 'lose');

    this.bus.emit('change', 'gold');
    this.bus.emit('change', 'items');
    this.bus.emit('change', 'phase');

    if (this.hp <= 0) { this.gameOver(false); return; }
    if (this.ai && this.battleKind === 'ai' && this.ai.hp <= 0) { this.gameOver(true); return; }
    this.bus.emit('round:result', this.lastResult);
  };

  Game.prototype.continueAfterResult = function () {
    if (this.phase !== 'result') return false;
    this.startRound();
    return true;
  };

  Game.prototype.gameOver = function (win) {
    this.phase = 'gameover';
    var comp = [];
    var board = this.boardUnits();
    for (var i = 0; i < board.length; i++) comp.push(D.unitById[board[i].id].name);
    this.bus.emit('change', 'phase');
    this.bus.emit('game:over', {
      win: win,
      rank: win ? 1 : 2,
      round: this.round,
      level: this.level,
      gold: this.gold,
      hp: this.hp,
      comp: comp,
      stats: this.stats,
      difficulty: this.difficulty
    });
  };

  /* ======================================================== 存档 ======== */
  Game.prototype.save = function () {
    var data = {
      v: 1,
      difficulty: this.difficulty, gold: this.gold, level: this.level, exp: this.exp,
      hp: this.hp, round: this.round, winStreak: this.winStreak, loseStreak: this.loseStreak,
      shop: this.shop, shopLocked: this.shopLocked, pool: this.pool,
      roster: this.roster.map(function (r) {
        return { uid: r.uid, id: r.id, star: r.star, pos: { x: r.pos.x, y: r.pos.y }, bench: r.bench, items: r.items.slice() };
      }),
      nextUid: this.nextUid, itemsBag: this.itemsBag, battleSpeed: this.battleSpeed,
      log: this.log.slice(-40), stats: this.stats, aiLastResult: this.aiLastResult,
      ai: this.ai ? {
        level: this.ai.level, exp: this.ai.exp, gold: this.ai.gold, hp: this.ai.hp,
        streak: this.ai.streak, rounds: this.ai.rounds, phase: this.ai.phase,
        owned: this.ai.owned, stars: this.ai.stars, items: this.ai.items,
        planId: this.ai.plan.id
      } : null
    };
    try {
      global.localStorage.setItem('jjk_save_v1', JSON.stringify(data));
      return true;
    } catch (e) { console.warn('[save]', e); return false; }
  };

  Game.prototype.load = function () {
    try {
      var raw = global.localStorage.getItem('jjk_save_v1');
      if (!raw) return false;
      var d = JSON.parse(raw);
      if (!d || d.v !== 1) return false;
      this.reset(d.difficulty);
      this.gold = d.gold; this.level = d.level; this.exp = d.exp; this.hp = d.hp;
      this.round = d.round; this.winStreak = d.winStreak; this.loseStreak = d.loseStreak;
      this.shop = d.shop || []; this.shopLocked = !!d.shopLocked; this.pool = d.pool || this.pool;
      this.roster = (d.roster || []).map(function (r) {
        return { uid: r.uid, id: r.id, star: r.star, pos: { x: r.pos.x, y: r.pos.y }, bench: r.bench, items: r.items || [] };
      });
      this.nextUid = d.nextUid || (this.roster.length + 1);
      this.itemsBag = d.itemsBag || [];
      this.battleSpeed = d.battleSpeed || 1;
      this.log = d.log || [];
      this.stats = d.stats || this.stats;
      this.aiLastResult = d.aiLastResult || 0;
      if (d.ai) {
        var p = null;
        for (var i = 0; i < D.plans.length; i++) if (D.plans[i].id === d.ai.planId) p = D.plans[i];
        if (p) {
          this.ai.plan = p;
          this.ai.build = p.phase_build.slice().sort(function (a, b) {
            return (D.unitById[a] ? D.unitById[a].cost : 1) - (D.unitById[b] ? D.unitById[b].cost : 1);
          });
        }
        this.ai.level = d.ai.level; this.ai.exp = d.ai.exp; this.ai.gold = d.ai.gold;
        this.ai.hp = d.ai.hp; this.ai.streak = d.ai.streak; this.ai.rounds = d.ai.rounds;
        this.ai.phase = d.ai.phase; this.ai.owned = d.ai.owned || {};
        this.ai.stars = d.ai.stars || {}; this.ai.items = d.ai.items || [];
      }
      this.phase = 'planning';
      this.bus.emit('change', 'all');
      this.addLog('已读取存档：第 ' + this.round + ' 回合。', 'system');
      return true;
    } catch (e) {
      console.warn('[load]', e);
      return false;
    }
  };

  Game.prototype.hasSave = function () {
    try { return !!global.localStorage.getItem('jjk_save_v1'); } catch (e) { return false; }
  };

  Game.prototype.clearSave = function () {
    try { global.localStorage.removeItem('jjk_save_v1'); } catch (e) { /* ignore */ }
  };

  JJK.Game = Game;
  JJK.CONST = {
    SHOP_SIZE: SHOP_SIZE, BENCH_SIZE: BENCH_SIZE, MAX_LEVEL: MAX_LEVEL,
    EXP_TABLE: EXP_TABLE, ODDS: ODDS, POOL_SIZE: POOL_SIZE, SELL_MULT: SELL_MULT,
    GRID_W: GRID_W, GRID_H: GRID_H, PVE_ROUNDS: PVE_ROUNDS
  };

})(window);
