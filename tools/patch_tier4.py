# -*- coding: utf-8 -*-
r"""battle.js：开战时广播「羁绊 4 人档」事件"""
import io
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
p = os.path.join(ROOT, "js", "core", "battle.js")
s = io.open(p, encoding="utf-8").read()

old = """    this._applyLinks();
    this.time = 0;
    this.over = false;
    this.winner = -1;
    return this;
  };"""
new = """    this._applyLinks();
    this.time = 0;
    this.over = false;
    this.winner = -1;
    this._announceTier4();
    return this;
  };

  /* 羁绊最高档（4 人档）生效时广播一次，供 UI 播放专属特效 */
  var TIER4_STYLE = {
    '夜':  { color: '#4fc06a', title: '夜 行 · 月 下 领 域', text: '夜行单位首次阵亡时以 35% 生命复活' },
    '影':  { color: '#2f5f9e', title: '影 袭 · 影 分 身',     text: '阵亡后留下 50% 属性的分身继续战斗' },
    '幻':  { color: '#e0483c', title: '幻 术 · 无 限 幻 境',   text: '全场敌人攻速 -25%，每秒流失 6 咒力' },
    '行':  { color: '#f0a020', title: '行 咒 · 行 动 自 如',   text: '施法后立刻追加一次普攻' },
    '体术': { color: '#ff8f3c', title: '体 术 · 无 下 限',    text: '黑闪必定连击两次' },
    '术式': { color: '#8f7cff', title: '术 式 · 解 放',       text: '每场战斗首次施法只需一半咒力' },
    '咒灵': { color: '#9b5cff', title: '咒 灵 · 咒 胎',       text: '咒灵首次阵亡时以 40% 生命复活' },
    '特级': { color: '#ffd166', title: '特 级 · 领 域 覆 盖',  text: '开战 8 秒后自动展开领域' },
    '东京校': { color: '#5bb8ff', title: '东 京 校 · 全 校 集 结', text: '全体友军全属性 +12%' },
    '京都校': { color: '#ff6b8a', title: '京 都 校 · 全 校 集 结', text: '京都校单位获得群体反击' }
  };

  BattleSim.prototype._announceTier4 = function () {
    var self = this;
    for (var t = 0; t < 2; t++) {
      var tiers = this.traitTiers[t] || {};
      for (var k in tiers) {
        if (!tiers.hasOwnProperty(k)) continue;
        var lv = tiers[k];
        // 四属性 / 咒灵 / 体术 / 术式 / 东京校 / 京都校 的最高档都是 3（对应 4 人）
        if (lv < 3) continue;
        var meta = TIER4_STYLE[k];
        if (!meta) continue;
        self._emit({
          t: 'tier4', team: t, trait: k,
          title: meta.title, text: meta.text, color: meta.color
        });
      }
    }
  };"""
assert old in s, "setup anchor"
s = s.replace(old, new, 1)
io.open(p, "w", encoding="utf-8").write(s)
print("[tier4] 已加入广播")
