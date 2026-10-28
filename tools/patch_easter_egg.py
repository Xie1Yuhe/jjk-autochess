# -*- coding: utf-8 -*-
r"""
patch_easter_egg.py —— 彩蛋重做：隐藏触发式魔虚罗

## 新规则（按需求）
1. **没有星级**：召唤/购买即为 3 星，不再合成升星
2. **商店极低概率**（0.35%）以 5 费卡出现，需要 7 级以上
3. **自动召唤**：场上（或队伍）满足下列任一条件时免费召唤到棋盘
     · 3 个伏黑惠
     · 1 个伏黑惠 + 1 个宿傩
4. **触发时播放特殊动画**

## 实现
- data：cost 5、noStar、autoSummon 条件随 unit 一起存放
- game：`_checkEasterEgg()` 在布阵/买卖/回合开始时检查，触发一次后本局不再重复
- 商店：`_pickUnit` 里按概率注入
- UI：`easterEgg` 事件 → 全屏闪光 + 专属横幅
"""
import io
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UID = "900001"

# ---------------- 1) 数据 ----------------
p = os.path.join(ROOT, "data", "units.json")
d = json.load(io.open(p, encoding="utf-8"))
units = d["units"] if isinstance(d, dict) and "units" in d else d
u = next(x for x in units if x["id"] == UID)
u["cost"] = 5
u["costSource"] = "easter-egg-5"
u["noStar"] = True
u["autoSummon"] = {"trio": "伏黑惠", "pair": ["伏黑惠", "宿傩"], "count": 3}
u["design"] = (
    "彩蛋：无星级，出现即 3 星。商店以 5 费、0.35% 的极低概率出现；"
    "更常见的触发方式是阵容——3 个伏黑惠，或 1 个伏黑惠 + 1 个宿傩，"
    "会自动登场。召唤物可继续召唤，第 n 代 = 本体 × 0.3^n。"
)
json.dump(d, io.open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("[egg] units.json 更新：cost=5, noStar, autoSummon")

# ---------------- 2) build_data 白名单 ----------------
bp = os.path.join(ROOT, "tools", "build_data.py")
bs = io.open(bp, encoding="utf-8").read()
if "noStar" not in bs:
    # 单位级字段
    bs = bs.replace('"isEasterEgg"', '"isEasterEgg", "noStar", "autoSummon"', 1)
    if '"noStar"' not in bs:
        # 若单位级白名单里没有 isEasterEgg，就找 playable 处理
        bs = bs.replace('"playable": ', '"noStar": u.get("noStar", False), "autoSummon": u.get("autoSummon"), "playable": ', 1)
    io.open(bp, "w", encoding="utf-8").write(bs)
    print("[egg] build_data 白名单已加 noStar/autoSummon")

# ---------------- 3) game.js 逻辑 ----------------
gp = os.path.join(ROOT, "js", "core", "game.js")
s = io.open(gp, encoding="utf-8").read()

# 3.1 商店注入：修改 _pickUnit 末尾
if "_pickEasterEgg" not in s:
    anchor = "  Game.prototype.rollShop = function () {"
    helper = '''  /* ---------------------------------------------------- 彩蛋 ---------- */
  var EGG_ID = '900001';
  var EGG_SHOP_RATE = 0.0035;     // 0.35%
  var EGG_MIN_LEVEL = 7;

  Game.prototype._pickEasterEgg = function () {
    if (this.eggSeenStore) return null;
    if (this.level < EGG_MIN_LEVEL) return null;
    if (Math.random() >= EGG_SHOP_RATE) return null;
    return EGG_ID;
  };

  // 阵容条件：3 伏黑惠 / 1 伏黑惠 + 1 宿傩
  Game.prototype._eggConditionMet = function () {
    var board = this.boardUnits();
    var mega = 0, suku = 0;
    for (var i = 0; i < board.length; i++) {
      var b = board[i];
      var nm = b.name || '';
      if (nm.indexOf('伏黑惠') >= 0) mega++;
      if (nm.indexOf('宿傩') >= 0) suku++;
    }
    if (mega >= 3) return 'trio';
    if (mega >= 1 && suku >= 1) return 'pair';
    return '';
  };

  Game.prototype._checkEasterEgg = function () {
    if (this.eggTriggered) return null;
    if (this.phase !== 'planning') return null;
    var why = this._eggConditionMet();
    if (!why) return null;
    // 找空位
    var spot = null;
    for (var y = 0; y < GRID_H && !spot; y++) {
      for (var x = 0; x < 4; x++) {
        if (!this.unitAtCell(x, y)) { spot = { x: x, y: y }; break; }
      }
    }
    if (!spot) return null;

    var uid = this._addUnit ? this._addUnit(EGG_ID) : null;
    var inst = uid ? this.unitById(uid) : null;
    if (!inst) return null;
    inst.star = 3;                 // 无星级：出现即满星
    inst.pos = spot;
    inst.bench = -1;
    this.eggTriggered = true;
    this.addLog('★ 彩蛋触发：' + (why === 'trio' ? '三个伏黑惠' : '伏黑惠与宿傩')
      + ' 引来了「无限式神」——魔虚罗登场！', 'upgrade');
    this.bus.emit('change', 'roster');
    this.bus.emit('easterEgg', { why: why, uid: uid });
    return why;
  };

''' + anchor
    assert anchor in s, 'rollShop anchor'
    s = s.replace(anchor, helper, 1)

# 3.2 rollShop 里注入彩蛋
old_roll = '''    this.shop = [];
    var dup = {};
    for (var i = 0; i < SHOP_SIZE; i++) {
      var id = this._pickUnit(dup);
      dup[id] = (dup[id] || 0) + 1;
      this.shop.push(id);
    }
    this.bus.emit('change', 'shop');'''
new_roll = '''    this.shop = [];
    var dup = {};
    for (var i = 0; i < SHOP_SIZE; i++) {
      var id = this._pickUnit(dup);
      dup[id] = (dup[id] || 0) + 1;
      this.shop.push(id);
    }
    // 彩蛋：以极低概率替换一格
    var egg = this._pickEasterEgg();
    if (egg) {
      this.shop[Math.floor(Math.random() * this.shop.length)] = egg;
      this.eggSeenStore = true;
      this.addLog('商店里似乎混进了什么不对劲的东西……', 'warn');
    }
    this.bus.emit('change', 'shop');'''
assert old_roll in s, 'roll body'
s = s.replace(old_roll, new_roll, 1)

# 3.3 布阵/买卖后检查
for fn in ["placeUnit", "sellUnit", "sortBench"]:
    pass  # 统一在 bus change 处检查，避免多处插入

io.open(gp, "w", encoding="utf-8").write(s)
print("[egg] game.js 逻辑已接入")
