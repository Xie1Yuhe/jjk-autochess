# -*- coding: utf-8 -*-
r"""
patch_ai_variety.py —— 让 AI 每局阵容都不一样

## 现状问题

1. AI 只有 3 套写死的蓝图，每局随机挑一套 → 打几把就腻
2. 更严重的是：`boardUnits()` 只遍历 `this.build`（固定蓝图），
   而「重搜」阶段随机买到的棋子**根本不会上场**，等于白花金币
3. 摆位完全固定，没有变化

## 改法

1. 新增 `_makeDeck()`：AI 每局自带一副 **36 张卡组**
   - 45% 概率直接用三套预设之一
   - 55% 概率现生成：按 8/8/8/8/4 配额、同角色 ≤2，
     并**按蓝图主题羁绊加权**，保证阵容仍成体系
2. 购买/重搜都只在**自己的卡组**里抽，不会出现卡组外的棋子
3. `boardUnits()` 改为遍历「已拥有的全部棋子」，修掉买了不上场的 bug
4. 摆位加轻微抖动，每局前后排的排布略有不同
"""
import io
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
p = os.path.join(ROOT, "js", "core", "ai.js")
s = io.open(p, encoding="utf-8").read()

# ---------------- 1) 构造函数里生成卡组 ----------------
old_ctor = """    this.build = this.plan.phase_build.slice().sort(function (a, b) {
      return (D.unitById[a] ? D.unitById[a].cost : 1) - (D.unitById[b] ? D.unitById[b].cost : 1);
    });
  }"""
new_ctor = """    this.build = this.plan.phase_build.slice().sort(function (a, b) {
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
  AI.prototype.inDeck = function (uid) { return !!this.deckSet[uid]; };"""
assert old_ctor in s, "ctor anchor"
s = s.replace(old_ctor, new_ctor, 1)

# ---------------- 2) 购买阶段：必须属于本局卡组 ----------------
old_buy = """      var d = D.unitById[uid];
      if (!d) continue;
      if ((this.owned[uid] || 0) > 0) continue;"""
new_buy = """      var d = D.unitById[uid];
      if (!d) continue;
      if (!this.inDeck(uid)) continue;          // 卡组外的棋子不买
      if ((this.owned[uid] || 0) > 0) continue;"""
assert old_buy in s, "buy anchor"
s = s.replace(old_buy, new_buy, 1)

# ---------------- 3) 重搜：从本局卡组抽，而不是固定蓝图 ----------------
old_roll = """      this.gold -= 1;
      var pool = this.build.filter(function (x) { return D.unitById[x] && D.unitById[x].cost <= 4; });
      if (!pool.length) continue;
      var pickId = pool[Math.floor(Math.random() * pool.length)];"""
new_roll = """      this.gold -= 1;
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
        for (var wj = 0; wj < w; wj++) weighted.push(wid);
      }
      if (!weighted.length) continue;
      var pickId = weighted[Math.floor(Math.random() * weighted.length)];"""
assert old_roll in s, "roll anchor"
s = s.replace(old_roll, new_roll, 1)

# ---------------- 4) 上阵：遍历已拥有的（修掉买了不上场） ----------------
old_board = """    var list = [];
    for (var i = 0; i < this.build.length; i++) {
      var uid = this.build[i];
      if ((this.owned[uid] || 0) > 0) list.push({ id: uid, star: this.stars[uid] || 1 });
    }"""
new_board = """    var list = [];
    // 遍历「所有已拥有」而不是固定蓝图——否则重搜买到的棋子永远不上场
    for (var uid in this.owned) {
      if (!this.owned.hasOwnProperty(uid)) continue;
      if ((this.owned[uid] || 0) <= 0) continue;
      if (!D.unitById[uid]) continue;
      list.push({ id: uid, star: this.stars[uid] || 1 });
    }"""
assert old_board in s, "board anchor"
s = s.replace(old_board, new_board, 1)

# ---------------- 5) 摆位抖动 ----------------
old_pos = """      var slot = melee ? meleeSlot : rangedSlot;
      for (var tries = 0; tries < 8 && !pos; tries++) {
        if (melee) {
          var mx = 4 + (slot % 2), my = Math.floor(slot / 2) % 4;"""
new_pos = """      var slot = melee ? meleeSlot : rangedSlot;
      // 每局给一个固定的小偏移，让摆位有变化但不至于乱
      if (jit === undefined) jit = Math.floor(Math.random() * 2);
      for (var tries = 0; tries < 8 && !pos; tries++) {
        if (melee) {
          var mx = 4 + ((slot + jit) % 2), my = Math.floor(slot / 2) % 4;"""
assert old_pos in s, "pos anchor"
s = s.replace(old_pos, new_pos, 1)

old_decl = """    var taken = {};
    var meleeSlot = 0, rangedSlot = 0;"""
new_decl = """    var taken = {};
    var jit;
    var meleeSlot = 0, rangedSlot = 0;"""
assert old_decl in s, "decl anchor"
s = s.replace(old_decl, new_decl, 1)

io.open(p, "w", encoding="utf-8").write(s)
print("[ai] 卡组化 AI 已写入")
print("   _makeDeck:", "AI.prototype._makeDeck" in s)
print("   购买限卡组:", "if (!this.inDeck(uid)) continue;" in s)
print("   上阵遍历 owned:", "for (var uid in this.owned)" in s)
print("   摆位抖动:", "var jit;" in s)
