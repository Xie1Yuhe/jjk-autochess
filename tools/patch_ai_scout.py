# -*- coding: utf-8 -*-
r"""
patch_ai_scout.py —— 让 AI 侦察玩家阵容并做出应对

## 三个应对维度

1. **属性克制**：玩家主力属性 → AI 优先买能克制它的属性
   克制链：行克幻 · 幻克夜 · 夜克影 · 影克行
   （玩家多「幻」，AI 就多买「行」）
2. **伤害构成**：玩家偏术式 → AI 优先买带 `mres` 的单位；偏体术 → 优先 `armor`
3. **站位**：把近战/嘲讽单位摆到更靠近玩家主力（最高费单位）的那一列

## 数据来源

`Game.endRound` 里把玩家阵容传给 `ai.beginRound(result, myUnits)`。
AI 在 `scout()` 里算出 `this.read`，之后购买/摆位都用它。
"""
import io
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ---------------- 1) game.js：把玩家阵容传给 AI ----------------
gp = os.path.join(ROOT, "js", "core", "game.js")
gs = io.open(gp, encoding="utf-8").read()

old_call = "    this.ai.beginRound(this.aiLastResult);"
new_call = """    // 把玩家当前阵容交给 AI 侦察（用于属性克制 / 伤害构成 / 站位应对）
    var scoutUnits = null;
    try { scoutUnits = this._buildMyUnits().units; } catch (e) { scoutUnits = null; }
    this.ai.beginRound(this.aiLastResult, scoutUnits);"""
assert old_call in gs, "beginRound call anchor"
gs = gs.replace(old_call, new_call, 1)
io.open(gp, "w", encoding="utf-8").write(gs)
print("[scout] game.js 已把玩家阵容传给 AI")

# ---------------- 2) ai.js：侦察 + 应对 ----------------
ap = os.path.join(ROOT, "js", "core", "ai.js")
s = io.open(ap, encoding="utf-8").read()

old_sig = "AI.prototype.beginRound = function (playerResult) {\n    this.rounds += 1;"
new_sig = """AI.prototype.beginRound = function (playerResult, playerUnits) {
    this.rounds += 1;
    if (playerUnits && playerUnits.length) this.scout(playerUnits);"""
assert old_sig in s, "beginRound sig anchor"
s = s.replace(old_sig, new_sig, 1)

# 侦察函数 + 克制表
anchor = "  AI.prototype._checkLevel = function () {"
scout = """  /* ---------------------------------------------------- 侦察 ----------- */
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

""" + anchor
assert anchor in s, "scout insert anchor"
s = s.replace(anchor, scout, 1)

# 购买/重搜权重里加入「反制属性」与「抗性」
old_w = """        var n = this.owned[wid] || 0;
        var w = 1;
        if (n > 0) w += 3;                       // 已拥有：优先补齐
        if (n === 1 || n === 2) w += 3;          // 差一张就升星
        if (n >= 9) w = 0;                       // 已满星"""
new_w = """        var n = this.owned[wid] || 0;
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
        }"""
assert old_w in s, "weight anchor"
s = s.replace(old_w, new_w, 1)

# 摆位：近战更靠近玩家主力所在的行
old_pos = """      // 每局给一个固定的小偏移，让摆位有变化但不至于乱
      if (jit === undefined) jit = Math.floor(Math.random() * 2);"""
new_pos = """      // 每局给一个固定的小偏移，让摆位有变化但不至于乱
      if (jit === undefined) jit = Math.floor(Math.random() * 2);
      // 侦察到玩家主力后，近战优先贴着它那一行站
      var read = this.read;
      if (read && read.carry && melee && !meleeAligned) {
        var ty = Math.max(0, Math.min(3, read.carry.y));
        if (!taken[(4 + (jit % 2)) + ',' + ty]) {
          pos = { x: 4 + (jit % 2), y: ty };
          meleeAligned = (read.carry.y === ty);
        }
      }"""
assert old_pos in s, "pos anchor"
s = s.replace(old_pos, new_pos, 1)

old_decl = """    var taken = {};
    var jit;"""
new_decl = """    var taken = {};
    var jit;
    var meleeAligned = false;"""
assert old_decl in s, "decl anchor"
s = s.replace(old_decl, new_decl, 1)

io.open(ap, "w", encoding="utf-8").write(s)
print("[scout] ai.js 已加入侦察与应对")
print("   scout():", "AI.prototype.scout" in s)
print("   购买权重含克制:", "rd.elemHeavy && rd.counterElem" in s)
print("   站位贴主力:", "meleeAligned" in s)
