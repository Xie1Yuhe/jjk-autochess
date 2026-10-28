# -*- coding: utf-8 -*-
r"""
patch_stats.py —— 给 BattleSim 加「逐单位战后统计」

记录三项：
  rec.dealt  造成的伤害
  rec.taken  承受的伤害
  rec.heal   治疗量（含自身回复 / 队友治疗 / 吸血）

设计参考：《云顶之弈》战斗后的伤害/承伤/治疗面板、《英雄联盟》赛后数据面板——
都是「按单位一行、按数值降序、带占比条」。
"""
import io
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
p = os.path.join(ROOT, "js", "core", "battle.js")
s = io.open(p, encoding="utf-8").read()

# 1) 单位对象初始化 rec
old = "    this.stateUntil = 0;   // 状态切换（蒸升 / 全开速 / 猩猩模式…）到期时间"
new = ("    this.rec = { dealt: 0, taken: 0, heal: 0 };   // 战后统计\n"
       "    this.stateUntil = 0;   // 状态切换（蒸升 / 全开速 / 猩猩模式…）到期时间")
if "this.rec = {" not in s:
    assert old in s, "rec init anchor"
    s = s.replace(old, new, 1)

# 2) _rawDamage：实际承伤 + 给来源记造成伤害
old2 = """  BattleSim.prototype._rawDamage = function (u, dmg) {
    if (!u.alive) return;
    dmg *= (1 + (u.mods.dmg_taken || 0));   // 易伤：目标受到伤害「增加」
    if (u.shield > 0) {
      var absorbed = Math.min(u.shield, dmg);
      u.shield -= absorbed;
      dmg -= absorbed;
    }
    u.hp -= dmg;
    if (u.hp <= 0) this._kill(u);
  };"""
new2 = """  BattleSim.prototype._rawDamage = function (u, dmg, src) {
    if (!u.alive) return;
    dmg *= (1 + (u.mods.dmg_taken || 0));   // 易伤：目标受到伤害「增加」
    if (u.shield > 0) {
      var absorbed = Math.min(u.shield, dmg);
      u.shield -= absorbed;
      dmg -= absorbed;
      if (u.rec) u.rec.taken += absorbed;   // 護盾吸收也算承伤
    }
    var real = Math.min(dmg, Math.max(0, u.hp));
    if (u.rec) u.rec.taken += real;
    if (src && src.rec) src.rec.dealt += real;
    u.hp -= dmg;
    if (u.hp <= 0) this._kill(u);
  };"""
assert old2 in s, "rawDamage anchor"
s = s.replace(old2, new2, 1)

# 3) _deal 调用 _rawDamage 时把 src 传进去
s = s.replace("this._rawDamage(dst, dmg);", "this._rawDamage(dst, dmg, src);")

# 4) 治疗记账：三种来源
# 4a) 技能治疗
old4 = "        ally.hp = Math.min(ally.maxHp, ally.hp + amt);"
new4 = ("        ally.hp = Math.min(ally.maxHp, ally.hp + amt);\n"
        "        if (u.rec) u.rec.heal += amt;\n"
        "        if (ally.rec) ally.rec.heal = ally.rec.heal;   // 目标不计，只记施法者")
if old4 in s:
    s = s.replace(old4, new4, 1)

# 4b) _deal 内的即时回血 _hl
old5 = "        dst.hp = Math.min(dst.maxHp, dst.hp + _hl);"
if old5 in s:
    s = s.replace(old5, old5 + "\n        if (dst.rec) dst.rec.heal += _hl;", 1)

# 4c) 吸血
old6 = "        src.hp = Math.min(src.maxHp, src.hp + dmg * src.mods.lifesteal);"
if old6 in s:
    s = s.replace(old6, old6 + "\n        if (src.rec) src.rec.heal += dmg * src.mods.lifesteal;", 1)

# 5) 新增 stats() 汇总
anchor = "  BattleSim.prototype._kill = function (u) {"
add = """  /* ---------------------------------------------------- 战后统计 ------ */
  // 返回 [{id, name, team, cost, star, dealt, taken, heal, alive}]
  BattleSim.prototype.stats = function () {
    var out = [];
    for (var i = 0; i < this.units.length; i++) {
      var u = this.units[i];
      var r = u.rec || { dealt: 0, taken: 0, heal: 0 };
      out.push({
        id: u.id, name: (u.def && u.def.name) || '咒灵', team: u.team,
        cost: (u.def && u.def.cost) || 0, star: u.star || 1,
        dealt: Math.round(r.dealt), taken: Math.round(r.taken),
        heal: Math.round(r.heal), alive: !!u.alive
      });
    }
    return out;
  };

""" + anchor
if "BattleSim.prototype.stats" not in s:
    s = s.replace(anchor, add, 1)

io.open(p, "w", encoding="utf-8").write(s)
print("[stats] battle.js 已加逐单位统计")
print("   rec 初始化:", "this.rec = {" in s)
print("   _rawDamage 带 src:", "this._rawDamage(dst, dmg, src)" in s)
print("   stats():", "BattleSim.prototype.stats" in s)
