# -*- coding: utf-8 -*-
r"""
rebuild_screen.py —— 一次性重写游戏主界面为严格三带结构

从原始 index.html 中按「配平标签」精确抽取各功能块，再按新顺序重新拼接，
避免上一次「字符串插入位置错乱」导致的嵌套损坏。

新结构：
```
<section class="screen screen-game">
  <div class="screen-shake">
    <header id="hud">…</header>
    <div class="top-strip" id="top-strip">
       <div class="intel" id="intel">…</div>
       <div class="panel traits-panel">…</div>
       <div class="panel items-panel">…</div>
       <div class="shop-controls" id="shop-controls">…</div>
       <div class="start-dock" id="start-dock">…</div>
    </div>
    <div class="stage" id="stage">
      <div class="col-left">…board-shell / bench-row…</div>
    </div>
  </div>
  <div class="shop-dock" id="shop-dock">drawer-head + shop-rail</div>
  <div class="log-dock" …>…</div>
</section>
```
"""
import io
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
p = os.path.join(ROOT, "index.html")
s = io.open(p, encoding="utf-8").read()


def find_block(text, start_marker, tag="div"):
    """从 start_marker 所在的开始标签起，按同名标签配平找到整块"""
    i = text.index(start_marker)
    start = text.rindex("<" + tag, 0, i)
    depth = 0
    k = start
    open_pat = "<" + tag
    close_pat = "</" + tag + ">"
    while k < len(text):
        if text.startswith(open_pat, k):
            depth += 1
            k = text.index(">", k) + 1
            continue
        if text.startswith(close_pat, k):
            depth -= 1
            k += len(close_pat)
            if depth == 0:
                return text[start:k]
            continue
        k += 1
    raise RuntimeError("unbalanced: " + start_marker)


hud = find_block(s, 'id="hud"', "header")
intel = find_block(s, 'id="intel"')
traits = find_block(s, 'traits-panel')
items = find_block(s, 'items-panel')
controls = find_block(s, 'id="shop-controls"')
startdock = find_block(s, 'class="start-dock"')
colleft = find_block(s, 'class="col-left"')
logdock = find_block(s, 'id="log-dock"')

for name, blk in [("hud", hud), ("intel", intel), ("traits", traits), ("items", items),
                  ("controls", controls), ("start", startdock), ("colleft", colleft),
                  ("log", logdock)]:
    print("  %-9s %5d 字  %s" % (name, len(blk), blk[:44].replace("\n", " ")))

new_section = '''<section class="screen screen-game" id="screen-game">
    <div class="screen-shake" id="shake-wrap">
      %s

      <!-- 上层：对手情报 / 羁绊 / 咒具 / 商店操作 / 开战 -->
      <div class="top-strip" id="top-strip">
        %s
        %s
        %s
        %s
        %s
      </div>

      <!-- 中层：棋盘 + 备战席（任何时候完整可见，不被任何元素覆盖） -->
      <div class="stage" id="stage">
        %s
      </div>
    </div>

    <!-- 下层：商店抽屉（只改变自身高度，绝不覆盖备战席） -->
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
    </div>

    %s
  </section>''' % (hud, intel, traits, items, controls, startdock, colleft, logdock)

i = s.index('<section class="screen screen-game"')
j = s.index('</section>', s.index('id="log-dock"')) + len('</section>')
s = s[:i] + new_section + s[j:]

io.open(p, "w", encoding="utf-8").write(s)
print("[rebuild] 主界面已重写")
