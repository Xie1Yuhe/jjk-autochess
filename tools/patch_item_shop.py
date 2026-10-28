# -*- coding: utf-8 -*-
r"""
patch_item_shop.py —— 商店分区：2/3 角色卡 + 1/3 咒具

## 引擎侧

1. `Game.itemShop`：3 个咒具槽，每回合与刷新时重掷
2. `buyItemFromShop(idx)`：3 金买一个组件，进背包
3. `itemMergeHint(itemId)`：判断这个组件能否与**已有组件**（背包 or 已装备）合成成品

## UI 侧

`js/ui/shop.js` 渲染两栏：
  · `.shop-rail`  角色卡（占 2/3）
  · `.item-rail`  咒具（占 1/3）
能融合的咒具加 `.can-craft` 高亮 + 「可融合」角标。
"""
import io
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ============================ 1) 引擎 ============================
gp = os.path.join(ROOT, "js", "core", "game.js")
s = io.open(gp, encoding="utf-8").read()

# 1.1 初始化
old = "    this.gold = 6 + (this.difficulty === 0 ? 3 : 0);"
new = """    this.gold = 6 + (this.difficulty === 0 ? 3 : 0);
    this.itemShop = [];            // 商店里的咒具（3 格）
    this.itemPrice = 3;            // 单件咒具售价"""
if "this.itemShop = []" not in s:
    assert old in s
    s = s.replace(old, new, 1)

# 1.2 掷咒具 + 购买 + 融合判断（插在 selectItem 之前）
anchor = "  Game.prototype.selectItem = function (itemId) {"
block = '''  /* ---------------------------------------------------- 咒具商店 ------ */
  var COMPONENTS = null;
  function components() {
    if (COMPONENTS) return COMPONENTS;
    COMPONENTS = (D.items || []).filter(function (it) { return it.kind === 'component'; });
    return COMPONENTS;
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
    var bag = this.bag || [];
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

''' + anchor
if "Game.prototype.buyItemFromShop" not in s:
    assert anchor in s, "selectItem anchor"
    s = s.replace(anchor, block, 1)

io.open(gp, "w", encoding="utf-8").write(s)
print("[itemshop] game.js 引擎已加咒具商店")

# 1.3 回合开始 / 刷新时重掷咒具
s = io.open(gp, encoding="utf-8").read()
if "this.rollItemShop()" not in s:
    # 在 refreshShop 里加
    m = re.search(r"(Game\.prototype\.refreshShop = function \(\) \{)", s)
    if m:
        s = s[:m.end()] + "\n    this.rollItemShop();" + s[m.end():]
    # 在 startRound 里加
    m2 = re.search(r"(Game\.prototype\.startRound = function \(\) \{)", s)
    if m2:
        s = s[:m2.end()] + "\n    this.rollItemShop();" + s[m2.end():]
    io.open(gp, "w", encoding="utf-8").write(s)
    print("[itemshop] refreshShop / startRound 已接入重掷")
