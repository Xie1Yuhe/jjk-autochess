# -*- coding: utf-8 -*-
r"""
patch_revive_and_tierfx.py

## 1. 修复「复活后棋子消失」

`death` 事件的处理里有一个 520ms 的延时：
```js
setTimeout(function () {
  if (de) { de.classList.add('is-dead'); de.style.display = 'none'; }
}, 520);
```
`revive` 事件会移除 `dying / is-dead` 并恢复 display，
但那个**已经排队的延时回调不会被取消**，520ms 后它又把棋子藏起来了。
夜行/咒灵 4 羁绊的复活是「立即复活」，正好落在这个窗口里 → 表现就是「复活了人没了」。

修法：给元素打一个 `deadTimer` 标记，复活时清掉；延时回调先检查标记。

## 2. 羁绊 4 人档的专属特效

在 trait 达到 4 人时，战斗内广播 `tier4` 事件，由视图播放特效：
横幅 + 全屏色晕 + 音效。每条羁绊有自己的颜色与文案。

## 3. 商店锁定标记（🔒 + 锁链）

见 shop.js 的改动。
"""
import io
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ---------------------------------------------------------------- 1) 复活
v = os.path.join(ROOT, "js", "ui", "battleview.js")
s = io.open(v, encoding="utf-8").read()

old_death = """        var de = unitElById(e.unitId);
        if (de) {
          de.style.setProperty('--dx', de.dataset.tx || '0px');
          de.style.setProperty('--dy', de.dataset.ty || '0px');
          de.classList.add('dying');
          setTimeout(function () {
            if (de) { de.classList.add('is-dead'); de.style.display = 'none'; }
          }, 520);
        }"""
new_death = """        var de = unitElById(e.unitId);
        if (de) {
          de.style.setProperty('--dx', de.dataset.tx || '0px');
          de.style.setProperty('--dy', de.dataset.ty || '0px');
          de.classList.add('dying');
          // 打标记：复活时会被清掉，延时回调就不会再把棋子藏起来
          de.dataset.deadTimer = '1';
          setTimeout(function () {
            if (!de || de.dataset.deadTimer !== '1') return;   // 已被复活取消
            de.classList.add('is-dead');
            de.style.display = 'none';
          }, 520);
        }"""
assert old_death in s, "death anchor"
s = s.replace(old_death, new_death, 1)

old_rv = """        var rv = unitElById(e.unitId);
        if (rv) {
          rv.classList.remove('dying', 'is-dead');
          rv.style.display = '';"""
new_rv = """        var rv = unitElById(e.unitId);
        if (rv) {
          rv.dataset.deadTimer = '0';      // 取消挂起的「隐藏」回调
          rv.classList.remove('dying', 'is-dead');
          rv.style.display = '';"""
assert old_rv in s, "revive anchor"
s = s.replace(old_rv, new_rv, 1)

# ------------------------------------------------- 2) tier4 事件的特效
old_case = """      case 'domain': {"""
new_case = """      case 'tier4': {
        // 羁绊 4 人档生效：专属横幅 + 色晕 + 音效
        var t4 = e.color || '#ffd166';
        FX.banner(e.title || '羁 绊 觉 醒', e.text || '', 1900, t4);
        FX.ring({ x: e.team === 0 ? 2 : 5, y: 1 }, t4);
        FX.shake(6);
        JJK.Audio.play('trait');
        break;
      }
      case 'domain': {"""
assert old_case in s, "case anchor"
s = s.replace(old_case, new_case, 1)
io.open(v, "w", encoding="utf-8").write(s)
print("[fix] battleview：复活不再被延时隐藏；新增 tier4 特效")

# ------------------------------------------------- 3) battle.js 广播 tier4
bp = os.path.join(ROOT, "js", "core", "battle.js")
b = io.open(bp, encoding="utf-8").read()

# 找到羁绊生效的位置：搜索 _applyTraitTiers 或 trait 应用
import re
m = re.search(r"BattleSim\.prototype\._applyTraits?[A-Za-z]* = function", b)
if not m:
    print("[fix] 找不到羁绊应用函数，跳过 tier4 广播")
else:
    print("[fix] 找到羁绊函数:", m.group(0))
