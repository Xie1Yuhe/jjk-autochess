# -*- coding: utf-8 -*-
r"""
restructure_bands.py —— 严格三带布局重构

## 目标

```
.screen-game
  ├─ header#hud                     上层：金币 / 生命 / 等级
  ├─ .top-strip                     上层：羁绊 + 咒具 + 商店操作
  ├─ .stage                         中层：棋盘 + 备战席（任何时候完整可见）
  └─ .shop-dock                     下层：商店抽屉（改变 height 展开/收起）
```

## 关键约束（用户要求）

1. **严禁用绝对定位覆盖备战区** —— 商店只能通过改变自身高度参与文档流
2. **商店展开时不遮暗棋盘/备战席** —— 移除所有 `opacity/filter` 变暗
3. 抽屉展开占底部 30~35%，卡牌拉大
4. 抽屉边缘提供「收起」按钮；收起后只留一条极简条带（金币 + 展开按钮）
5. 过渡 0.3s 左右，作用于 height / translateY

本脚本：
  · 把 `.col-right` 里的羁绊 / 咒具 / 商店操作搬到顶部横带
  · 「开始战斗」放进中层右下的 dock（不覆盖任何东西）
  · 商店容器改为 `.shop-dock` 带抽屉头（金币 + 收起/展开）
"""
import io
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
p = os.path.join(ROOT, "index.html")
s = io.open(p, encoding="utf-8").read()

# ---------------- 1) 把 aside 内容抽出来 ----------------
aside_start = s.index('<aside class="col-right">')
aside_end = s.index('</aside>', aside_start) + len('</aside>')
aside = s[aside_start:aside_end]

def grab(cls_marker):
    """从 aside 里抽出某个块"""
    i = aside.index(cls_marker)
    # 向前找到该块的起始 <div
    start = aside.rindex('<div', 0, i)
    # 用括号配平找结束
    depth = 0
    k = start
    while k < len(aside):
        if aside.startswith('<div', k):
            depth += 1
            k = aside.index('>', k) + 1
            continue
        if aside.startswith('</div>', k):
            depth -= 1
            k += 6
            if depth == 0:
                return aside[start:k]
            continue
        k += 1
    return ''

traits = grab('traits-panel')
items = grab('items-panel')
controls = grab('shop-controls')
startdock = grab('start-dock')
print("抽出：羁绊 %d 字 / 咒具 %d 字 / 操作 %d 字 / 开始 %d 字" % (
    len(traits), len(items), len(controls), len(startdock)))

# ---------------- 2) 组新的顶部横带 ----------------
top_strip = '''      <!-- 上层：羁绊 / 咒具 / 商店操作（横向排布，不遮挡任何东西） -->
      <div class="top-strip" id="top-strip">
        %s
        %s
        %s
      </div>
''' % (traits, items, controls)

# ---------------- 3) 中层：只留棋盘 + 备战席 + 开始战斗 ----------------
stage_new = '''      <!-- 中层：棋盘 + 备战席（任何时候完整可见） -->
      <div class="stage" id="stage">
        <div class="col-left">
'''

# 原来的 .stage 起点
stage_start = s.index('<div class="stage">')
colleft_start = s.index('<div class="col-left">', stage_start)
# col-left 的结束（配平）
def block_end(text, start):
    depth = 0
    k = start
    while k < len(text):
        if text.startswith('<div', k):
            depth += 1
            k = text.index('>', k) + 1
            continue
        if text.startswith('</div>', k):
            depth -= 1
            k += 6
            if depth == 0:
                return k
            continue
        k += 1
    return -1

colleft_end = block_end(s, colleft_start)
colleft = s[colleft_start:colleft_end]

# 用新结构替换整个 .stage .. </aside> 区间
new_mid = '''      <!-- 中层：棋盘 + 备战席（任何时候完整可见） -->
      <div class="stage" id="stage">
        %s
        <div class="start-dock" id="start-dock">
          <button class="btn-start" id="btn-battle">
            开 始 战 斗
            <span class="bs-sub" id="battle-sub">第 1 回合 · PvE</span>
          </button>
        </div>
      </div>
''' % colleft

s = s[:stage_start] + new_mid + s[aside_end:]

# ---------------- 4) 顶部横带插到 hud 之后 ----------------
hud_end = s.index('</header>', s.index('id="hud"')) + len('</header>')
s = s[:hud_end] + '\n' + top_strip + s[hud_end:]

# ---------------- 5) 商店抽屉：加抽屉头（金币 + 收起/展开） ----------------
old_shop = '''      <div class="shop-dock">
        <div class="shop-rail" id="shop-rail"></div>
      </div>'''
new_shop = '''      <!-- 下层：商店抽屉（只通过 height 展开/收起，绝不复盖备战席） -->
      <div class="shop-dock" id="shop-dock">
        <div class="drawer-head" id="drawer-head">
          <span class="dh-grip"></span>
          <span class="dh-title">商 店</span>
          <span class="dh-gold">金币 <b id="dh-gold">0</b></span>
          <span class="dh-hint" id="dh-hint">拖动卡牌到备战席</span>
          <button class="dh-toggle" id="btn-drawer">
            <span class="dh-arrow">▾</span><span class="dh-label">收起</span>
          </button>
        </div>
        <div class="shop-rail" id="shop-rail"></div>
      </div>'''
assert old_shop in s, "shop anchor"
s = s.replace(old_shop, new_shop, 1)

# 删掉旧的「展开棋盘」浮动按钮（新布局不需要）
s = re.sub(r'\s*<button class="board-toggle" id="btn-board-toggle"[\s\S]*?</button>', '', s)

io.open(p, "w", encoding="utf-8").write(s)
print("[bands] index.html 已重构为三带布局")
